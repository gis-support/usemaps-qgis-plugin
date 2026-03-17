from typing import Optional, Any, Iterable

from qgis.gui import QgsMapTool, QgsRubberBand, QgsMapCanvas, QgsMapMouseEvent
from qgis.PyQt.QtWidgets import QWidget, QFormLayout, QLabel, QLineEdit, QTabWidget, QVBoxLayout
from qgis.PyQt.QtCore import Qt, QDate, QDateTime
from qgis.PyQt.QtGui import QCursor, QColor
from qgis.core import (
    QgsRectangle, QgsFeatureRequest, QgsMapLayer,
    QgsCoordinateTransform, QgsProject, QgsGeometry, QgsPointXY,
    QgsWkbTypes, NULL, QgsAttributeEditorElement, QgsFeature
)

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

        self.setCursor(QCursor(Qt.CrossCursor))

    def canvasPressEvent(self, e: QgsMapMouseEvent) -> None:
        if (self.canvas.currentLayer() and
            self.canvas.currentLayer().type() == QgsMapLayer.VectorLayer and
            e.button() == Qt.LeftButton):
            self.startPoint = e.mapPoint()

    def canvasMoveEvent(self, e: QgsMapMouseEvent) -> None:
        if (self.canvas.currentLayer() and
            self.canvas.currentLayer().type() == QgsMapLayer.VectorLayer and
            e.buttons() == Qt.LeftButton and self.startPoint):
            self.selectionRect.reset(QgsWkbTypes.PolygonGeometry)
            self.selectionRect.addPoint(self.startPoint)
            self.selectionRect.addPoint(QgsPointXY(self.startPoint.x(), e.mapPoint().y()))
            self.selectionRect.addPoint(e.mapPoint())
            self.selectionRect.addPoint(QgsPointXY(e.mapPoint().x(), self.startPoint.y()))

    def canvasReleaseEvent(self, e: QgsMapMouseEvent) -> None:
        if not self.canvas.currentLayer() or self.canvas.currentLayer().type() != QgsMapLayer.VectorLayer:
            return

        if e.button() == Qt.LeftButton:
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
        for el in elements:
            if el.type() == QgsAttributeEditorElement.AeTypeField and el.name() in valid_fields:
                yield el.name()
            elif el.type() == QgsAttributeEditorElement.AeTypeContainer:
                yield from self._extract_field_names(el.children(), valid_fields)

    def _process_feature(self, feature: Optional[QgsFeature], layer: QgsMapLayer) -> None:
        """Generuje główną zakładkę i zagnieżdża w niej zakładki grup"""
        if not feature:
            return

        self.geometry.reset(layer.geometryType())
        self.geometry.addGeometry(feature.geometry(), layer)

        self.dock.attributeTabWidget.clear()

        inner_tabs = QTabWidget()

        if layer.editFormConfig().layout() == 1 and layer.editFormConfig().tabs():
            for tab in layer.editFormConfig().tabs():
                inner_tabs.addTab(
                    self._create_attribute_page(
                        feature,
                        self._extract_field_names(tab.children(), layer.fields().names())
                    ),
                    tab.name()
                )
        else:
            inner_tabs.addTab(
                self._create_attribute_page(feature, (f.name() for f in layer.fields())),
                self.tr("Atrybuty")
            )

        main_page = QWidget()
        QVBoxLayout(main_page).addWidget(inner_tabs)

        self.dock.attributeTabWidget.addTab(main_page, self.tr("Atrybuty"))

        self.dock.tabWidget.setCurrentIndex(self.dock.tabWidget.indexOf(self.dock.identifyTab))

    def _create_attribute_page(self, feature: QgsFeature, field_names: Iterable[str]) -> QWidget:
        """Buduje formularz w oparciu nazwy pól"""
        page = QWidget()
        QFormLayout(page)

        for name, value in ((n, feature.attribute(n)) for n in field_names):
            page.layout().addRow(
                QLabel(f"<b>{name}:</b>"),
                self._create_readonly_field(
                    (CONNECTION.get(f'/api/users/{value}', sync=True) or {}).get('data', {}).get('name', value)
                    if name in ('create_user', 'update_user') and value not in (None, NULL, '')
                    else value
                )
            )

        return page

    def _create_readonly_field(self, value: Any) -> QLineEdit:
        widget = QLineEdit(
            "NULL" if value == NULL or value is None
            else value.toString("yyyy-MM-dd HH:mm:ss") if isinstance(value, QDateTime)
            else value.toString("yyyy-MM-dd") if isinstance(value, QDate)
            else str(value)
        )
        widget.setReadOnly(True)
        widget.setCursorPosition(0)

        widget.setMinimumWidth(widget.fontMetrics().boundingRect(widget.text()).width() + 20)

        return widget

    def clear_highlight(self) -> None:
        self.geometry.reset()
        self.selectionRect.reset(QgsWkbTypes.PolygonGeometry)

    def deactivate(self) -> None:
        self.clear_highlight()
        super().deactivate()