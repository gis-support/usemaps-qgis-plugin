import os

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import pyqtSignal, QEvent
from PyQt5.QtGui import QIcon, QDropEvent, QDragEnterEvent

from PyQt5.Qt import QStandardItemModel, QStandardItem, QSortFilterProxyModel
from qgis.utils import iface
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject

from .layers.layers_registry import layers_registry
from ..tools.logger import Logger
from .gui.login_settings import LoginSettingsDialog
from .gui.import_layer import ImportLayerDialog
from ..tools.connection import CONNECTION
from ..tools.project_variables import get_layer_mappings
from .gui.adaptive_palette import apply_adaptive_palette


FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'main_dockwidget.ui'))


class MainDockWidget(QtWidgets.QDockWidget, FORM_CLASS, Logger):

    closingPlugin = pyqtSignal()

    def __init__(self, parent=None):
        super(MainDockWidget, self).__init__(parent)
        self.setupUi(self)
        self.loginSettingsDialog = LoginSettingsDialog(self)
        self.importLayerDialog = ImportLayerDialog()

        self.connectButton.setIcon(QIcon(":/plugins/usemaps-plugin/widget_connect.svg"))
        self.connectButton.setCheckable(True)

        self.authSettingsButton.setIcon(QIcon(":/plugins/usemaps-plugin/widget_settings.svg"))
        self.authSettingsButton.clicked.connect(self.show_login_settings)

        self.layerBrowser.textChanged.connect(self.filter_tree_view)

        self.layerTreeView.setDragEnabled(True)
        self.layerTreeView.setAcceptDrops(False)
        self.layerTreeView.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.layerTreeView.viewport().installEventFilter(self)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.proxy_model.setRecursiveFilteringEnabled(True)

        layers_registry.on_schema.connect(self.add_layers_to_treeview)

        self.refreshButton.setIcon(QIcon(":/plugins/usemaps-plugin/refresh.svg"))
        self.refreshButton.clicked.connect(self.refresh_layers)
        self.refreshButton.setEnabled(False)

        self.addLayerButton.setIcon(QIcon(":/plugins/usemaps-plugin/export.svg"))
        self.addLayerButton.clicked.connect(self.importLayerDialog.show)
        self.addLayerButton.setEnabled(False)

        self.mapCanvas = iface.mapCanvas()
        self.mapCanvas.setAcceptDrops(True)
        self.mapCanvas.installEventFilter(self)

        apply_adaptive_palette(self)

        iface.addDockWidget(Qt.RightDockWidgetArea, self)
        self.hide()

    def closeEvent(self, event):
        self.closingPlugin.emit()
        event.accept()




    def filter_tree_view(self, text):
        """
        Filtruje drzewko warstw po nazwach warstw.
        Wywoływane po wpisywaniu tekstu w label layerBrowser.
        """
        self.proxy_model.setFilterFixedString(text)

        if text:
            self.layerTreeView.expandAll()
        else:
            self.layerTreeView.collapseAll()


    def show_login_settings(self):
        """
        Wyświetla okno ustawień połączenia z serwerem.
        """
        self.loginSettingsDialog.show()


    def clear_treeview(self):
        """
        Usuwa wzystkie warstwy z drzewa warstw.
        Wywoływane po wylogowaniu.
        """

        if self.proxy_model.sourceModel():
            self.proxy_model.sourceModel().clear()

        else:
            self.layerTreeView.setModel(None)

        self.addLayerButton.setEnabled(False)

    def add_layers_to_treeview(self, groups: list):
        """
        Dodaje warstwy/grupy do drzewka warstw.
        Wywoływane po zalogowaniu.
        """
        modules_layer_custom_id = -99

        tree_model = QStandardItemModel()
        self.proxy_model.setSourceModel(tree_model)
        root_item = tree_model.invisibleRootItem()

        is_admin = CONNECTION.current_user.get('is_admin', False) if CONNECTION.current_user else False
        self.addLayerButton.setEnabled(is_admin)

        self.addLayerButton.setToolTip(
            "" if is_admin else self.tr("Tylko administrator może dodać nową warstwę do organizacji")
        )

        def add_layers(layers: list, group_item: QStandardItem):

            if not layers:
                return

            for layer in layers:
                layer_id = layer.get("id")

                layer_class = layers_registry.layers.get(layer_id)

                if layer_class:
                    if hasattr(layer_class, 'datasource'):
                        if layer_class.datasource_name == 'foreign_vehicles':
                            continue

                    layer_item = QStandardItem(layer_class.name)
                    layer_item.setData(layer_class, Qt.UserRole + 1)
                    group_item.appendRow(layer_item)

        def add_groups(groups: list):

            for group in groups:
                if not isinstance(group, dict):
                    continue

                group_layers = group.get('layers')

                if not group_layers:
                    continue

                if group['id'] == modules_layer_custom_id:
                    continue

                scope = group['schema_scope']

                if scope == 'core':
                    group_item = QStandardItem(group['name'])
                    group_item.setData([group['name'], group['id']], Qt.UserRole + 2)
                    add_layers(group_layers, group_item)
                    root_item.appendRow(group_item)


        add_groups(groups)
        self.layerTreeView.setModel(self.proxy_model)
        self.layerTreeView.setHeaderHidden(True)
        self.layerTreeView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)
        self.message(self.tr('Pobrano schemat warstw'))


    def add_layer_to_map(self, index):
        """
        Dodaje wybraną warstwę/grupę do projektu.
        """
        source_index = self.proxy_model.mapToSource(index)
        source_model = self.proxy_model.sourceModel()
        item = source_model.itemFromIndex(source_index)

        if group_data := item.data(Qt.UserRole + 2):
            layers_registry.loadGroup(group_data)

        elif layer_class := item.data(Qt.UserRole + 1):
            layer_class.loadLayer()


    def eventFilter(self, obj, event):
        """
        Event obsługujący dwa wydarzenia:
        1. dodawanie warstw/grup po przeciągnięciu na panel mapowy.
        2. dodawanie warstw/grup po dwukrotnym kliknięciu lewym przyciskiem myszy na drzewku warstw.
        """
        if obj == self.mapCanvas:
            if event.type() == QDragEnterEvent.DragEnter:
                return self.handle_map_canvas_drag_enter(event)

            if event.type() == QDropEvent.Drop:
                return self.handle_map_canvas_drop(event)


        if obj == self.layerTreeView.viewport() and event.type() == QEvent.MouseButtonDblClick:
            if event.button() == Qt.LeftButton:
                index = self.layerTreeView.indexAt(event.pos())
                if index.isValid():
                    self.add_layer_to_map(index)
                    return True

        return super().eventFilter(obj, event)


    def handle_map_canvas_drag_enter(self, event):
        """
        Sprawdza, czy przeciągany obiekt posiada dane tego samego typu, co obiekty z drzewa warstw.
        """
        if event.mimeData().hasFormat("application/x-qabstractitemmodeldatalist"):
            event.acceptProposedAction()
            return True

        return False


    def handle_map_canvas_drop(self, event):
        """
        Wywołuje dodanie upuszczonej warstwy/grupy do projektu.
        """
        selected_indexes = self.layerTreeView.selectedIndexes()

        if not selected_indexes:
            return False

        self.add_layer_to_map(selected_indexes[0])

        event.acceptProposedAction()
        return True


    def refresh_layers(self):
        """
        Odświeżanie warstw Usemaps, które obecnie znajdują się w projekcie.
        """
        if not CONNECTION.is_connected:
            return
        layers_registry.loadData(True)
        mappings = get_layer_mappings()
        for layer in QgsProject.instance().mapLayers().values():
            if layers_registry.isSystemLayer(layer):
                layer_qgis_id = layer.id()
                layer_id = mappings.get(layer_qgis_id)
                layer_class = layers_registry.layers.get(int(layer_id))
                if not layer_class:
                    return
                layer_class.on_reload.emit(True)
