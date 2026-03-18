from typing import Optional, Any, Iterable

from qgis.gui import (
    QgsMapTool, QgsRubberBand, QgsMapCanvas, QgsMapMouseEvent,
    QgsCollapsibleGroupBox
)
from qgis.PyQt.QtWidgets import (
    QWidget, QFormLayout, QLabel, QLineEdit, QVBoxLayout, QScrollArea
)
from qgis.PyQt.QtCore import Qt, QDate, QDateTime
from qgis.PyQt.QtGui import QCursor, QColor
from qgis.core import (
    QgsRectangle, QgsFeatureRequest, QgsMapLayer,
    QgsCoordinateTransform, QgsProject, QgsGeometry, QgsPointXY,
    QgsWkbTypes, NULL, QgsAttributeEditorElement, QgsFeature
)

from . import USER_CACHE
from .connection import CONNECTION

class UsemapsIdentifyTool(QgsMapTool):
    def __init__(self, canvas: QgsMapCanvas, dock_widget: QWidget) -> None:
        super().__init__(canvas)
        self.canvas = canvas
        self.dock = dock_widget
        self.startPoint = None

        self.geometry = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.geometry.setColor(QColor('red'))
        self.geometry.setFillColor(QColor(255, 165, 0, 100))
        self.geometry.setWidth(3)

        # Prostokąt selekcji przy przeciąganiu
        self.selectionRect = QgsRubberBand(self.canvas, QgsWkbTypes.PolygonGeometry)
        self.selectionRect.setColor(QColor('orange'))
        self.selectionRect.setFillColor(QColor(255, 122, 52, 100))

        self.setCursor(QCursor(Qt.CursorShape.CrossCursor))

    def _resolve_user_name(self, user_id: Any) -> Any:
        """Pobiera nazwę z globalnego cache lub dociąga z API i zapisuje."""
        if user_id not in USER_CACHE:
            USER_CACHE[user_id] = (CONNECTION.get(f'/api/users/{user_id}', sync=True) or {}).get('data', {}).get('name', user_id)
        return USER_CACHE[user_id]

    def canvasPressEvent(self, e: QgsMapMouseEvent) -> None:
        """Rejestruje punkt początkowy kliknięcia LPM"""
        if (self.canvas.currentLayer() and
            self.canvas.currentLayer().type() == QgsMapLayer.VectorLayer and
            e.button() == Qt.MouseButton.LeftButton):
            self.startPoint = e.mapPoint()

    def canvasMoveEvent(self, e: QgsMapMouseEvent) -> None:
        """Rysuje prostokąt zaznaczenia podczas przeciągania myszą"""
        if (self.canvas.currentLayer() and
            self.canvas.currentLayer().type() == QgsMapLayer.VectorLayer and
            e.buttons() == Qt.MouseButton.LeftButton and self.startPoint):
            self.selectionRect.reset(QgsWkbTypes.PolygonGeometry)
            self.selectionRect.addPoint(self.startPoint)
            self.selectionRect.addPoint(QgsPointXY(self.startPoint.x(), e.mapPoint().y()))
            self.selectionRect.addPoint(e.mapPoint())
            self.selectionRect.addPoint(QgsPointXY(e.mapPoint().x(), self.startPoint.y()))

    def canvasReleaseEvent(self, e: QgsMapMouseEvent) -> None:
        """Identyfikuje obiekt na podstawie kliknięcia punktu lub zaznaczonego obszaru"""
        if not self.canvas.currentLayer() or self.canvas.currentLayer().type() != QgsMapLayer.VectorLayer:
            return

        if e.button() == Qt.MouseButton.LeftButton:
            if self.selectionRect.asGeometry().boundingBox().isEmpty():
                try:
                    self._process_feature(
                        self._find_best_feature(
                            self.canvas.currentLayer(),
                            QgsGeometry.fromPointXY(
                                QgsCoordinateTransform(
                                    self.canvas.mapSettings().destinationCrs(),
                                    self.canvas.currentLayer().crs(),
                                    QgsProject.instance()
                                ).transform(self.toMapCoordinates(e.pos()))
                            )
                        ),
                        self.canvas.currentLayer()
                    )
                except Exception:
                    pass
            else:
                self._process_feature(
                    next(
                        (f for f in self.canvas.currentLayer().getFeatures(
                            QgsFeatureRequest().setFilterRect(
                                QgsCoordinateTransform(
                                    self.canvas.mapSettings().destinationCrs(),
                                    self.canvas.currentLayer().crs(),
                                    QgsProject.instance()
                                ).transform(self.selectionRect.asGeometry().boundingBox())
                            )
                        )),
                        None
                    ),
                    self.canvas.currentLayer()
                )

        self.startPoint = None
        self.selectionRect.reset(QgsWkbTypes.PolygonGeometry)

    def _find_best_feature(self, layer: QgsMapLayer, click_geom: QgsGeometry) -> Optional[QgsFeature]:
        """Wybiera obiekt. Priorytetyzuje najmniejszą powierzchnię."""
        return min(
            (f for f in layer.getFeatures(
                QgsFeatureRequest().setFilterRect(
                    QgsRectangle(
                        click_geom.asPoint().x() - (self.canvas.mapUnitsPerPixel() * 8),
                        click_geom.asPoint().y() - (self.canvas.mapUnitsPerPixel() * 8),
                        click_geom.asPoint().x() + (self.canvas.mapUnitsPerPixel() * 8),
                        click_geom.asPoint().y() + (self.canvas.mapUnitsPerPixel() * 8)
                    )
                )
            ) if f.geometry() and f.geometry().intersects(click_geom)),
            key=lambda x: x.geometry().area(),
            default=None
        )

    def _extract_field_names(self, elements, valid_fields):
        """Generuje nazwy pól na podstawie elementów formularza warstwy"""
        for el in elements:
            if el.type() == QgsAttributeEditorElement.AeTypeField and el.name() in valid_fields:
                yield el.name()
            elif el.type() == QgsAttributeEditorElement.AeTypeContainer:
                yield from self._extract_field_names(el.children(), valid_fields)

    def _process_feature(self, feature: Optional[QgsFeature], layer: QgsMapLayer) -> None:
        """Generuje listę atrybutów ze zwijanymi grupami"""
        if not feature:
            self.clear_highlight()  # Czyści obrys obiektu
            self.dock.attributeTabWidget.clear()  # Czyści atrybuty w panelu bocznym
            return

        self.geometry.reset(layer.geometryType())
        self.geometry.addGeometry(feature.geometry(), layer)

        self.dock.attributeTabWidget.clear()

        self.dock.attributeTabWidget.addTab(
            self._setup_scroll_area(
                QScrollArea(),
                self._populate_groups_layout(QWidget(), feature, layer)
            ),
            self.tr("Atrybuty")
        )

        self.dock.tabWidget.setCurrentIndex(self.dock.tabWidget.indexOf(self.dock.identifyTab))

    def _setup_scroll_area(self, scroll: QScrollArea, content: QWidget) -> QScrollArea:
        """Konfiguruje obszar przewijania dla panelu atrybutów"""
        scroll.setWidgetResizable(True)
        scroll.setWidget(content)
        return scroll

    def _populate_groups_layout(self, container: QWidget, feature: QgsFeature, layer: QgsMapLayer) -> QWidget:
        """Wypełnia atrybutami, uwzględniając podział na zakładki z konfiguracji warstwy"""
        QVBoxLayout(container)

        if layer.editFormConfig().layout() == 1 and layer.editFormConfig().tabs():
            for tab in layer.editFormConfig().tabs():
                container.layout().addWidget(
                    self._create_group_box(
                        tab.name(),
                        self._create_attribute_page(feature, self._extract_field_names(tab.children(), layer.fields().names()))
                    )
                )
        else:
            container.layout().addWidget(
                self._create_attribute_page(feature, (f.name() for f in layer.fields()))
            )

        container.layout().addStretch()
        return container

    def _create_group_box(self, title: str, content: QWidget) -> QgsCollapsibleGroupBox:
        """Tworzy zakładkę grupy dla atrybutów"""
        return self._add_to_layout(QgsCollapsibleGroupBox(title), content)

    def _add_to_layout(self, parent: QWidget, child: QWidget) -> QWidget:
        QVBoxLayout(parent).addWidget(child)
        return parent

    def _create_attribute_page(self, feature: QgsFeature, field_names: Iterable[str]) -> QWidget:
        """Buduje formularz w oparciu nazwy pól"""
        page = QWidget()
        QFormLayout(page)

        for name, value in ((n, feature.attribute(n)) for n in field_names):
            page.layout().addRow(
                QLabel(f"<b>{name}:</b>"),
                self._create_readonly_field(
                    self._resolve_user_name(value)
                    if name in ('create_user', 'update_user') and value not in (None, NULL, '')
                    else value
                )
            )

        return page

    def _create_readonly_field(self, value: Any) -> QLineEdit:
        """Formatuje pola"""
        return self._apply_readonly_field_settings(
            QLineEdit(
                "NULL" if value == NULL or value is None
                else value.toString("yyyy-MM-dd HH:mm:ss") if isinstance(value, QDateTime)
                else value.toString("yyyy-MM-dd") if isinstance(value, QDate)
                else str(value)
            )
        )

    def _apply_readonly_field_settings(self, widget: QLineEdit) -> QLineEdit:
        """Dostosowuje wymiary i właściwości pola tekstowego"""
        widget.setReadOnly(True)
        widget.setCursorPosition(0)

        widget.setMinimumWidth(widget.fontMetrics().boundingRect(widget.text()).width() + 20)

        return widget

    def clear_highlight(self) -> None:
        """Usuwa obrysy i podświetlenia z mapy"""
        self.geometry.reset()
        self.selectionRect.reset(QgsWkbTypes.PolygonGeometry)

    def deactivate(self) -> None:
        """Dezaktywuje narzędzie i sprząta interfejs"""
        self.clear_highlight()
        super().deactivate()