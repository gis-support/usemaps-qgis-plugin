import os

from PyQt5 import QtWidgets, uic
from PyQt5.QtCore import pyqtSignal, QEvent
from PyQt5.QtGui import QIcon, QDropEvent, QDragEnterEvent

from PyQt5.Qt import QStandardItemModel, QStandardItem, QSortFilterProxyModel
from qgis.utils import iface
from qgis.PyQt.QtCore import Qt
from qgis.core import QgsProject, Qgis

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

        self.mapBrowser.textChanged.connect(self.filter_projects_view)

        self.projects_proxy_model = QSortFilterProxyModel()
        self.projects_proxy_model.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.projects_proxy_model.setRecursiveFilteringEnabled(True)
        self.projects_proxy_model.setFilterKeyColumn(-1)

        self.mapTableView.setSelectionMode(QtWidgets.QAbstractItemView.SingleSelection)
        self.mapTableView.doubleClicked.connect(self.add_project_to_qgis)
        self._sort_state = {}

        self.refreshButton.setIcon(QIcon(":/plugins/usemaps-plugin/refresh.svg"))
        self.refreshButton.setText("  " + self.refreshButton.text())
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
        self.message(self.tr('Pobrano schemat warstw'), duration=3)


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

        res = CONNECTION.get('/api/v2/projects', sync=True)
        if isinstance(res, dict) and 'data' in res:
            self.load_projects_to_tableview(res['data'])

        mappings = get_layer_mappings()
        for layer in QgsProject.instance().mapLayers().values():
            if layers_registry.isSystemLayer(layer):
                layer_qgis_id = layer.id()
                layer_id = mappings.get(layer_qgis_id)
                layer_class = layers_registry.layers.get(int(layer_id))
                if not layer_class:
                    return
                layer_class.on_reload.emit(True)

    def filter_projects_view(self, text):
        self.projects_proxy_model.setFilterFixedString(text)

    def load_projects_to_tableview(self, projects_data: list):
        """Wypełnia zakładkę Mapy danymi z endpointu /projects."""
        model = QStandardItemModel(0, 4)
        model.setHorizontalHeaderLabels(['', 'Nazwa', 'Właściciel', 'Data ostatniej edycji'])
        self.projects_proxy_model.setSourceModel(model)

        # Pobranie danych aktualnego uzytkownika
        current_data = (CONNECTION.get('/api/users/current_user', sync=True) or {}).get('data', {})
        c_id = current_data.get('id')
        c_name = current_data.get('name', 'Brak informacji')

        # Jeśli ID to ID aktualnego uzytkownika, bierzemy c_name. W innym przypadku pytamy API
        users = {
            uid: (c_name if uid == c_id else (CONNECTION.get(f'/api/users/{uid}', sync=True) or {}).get('data', {}).get('name', 'Brak informacji'))
            for uid in {p.get('owner') for p in projects_data if p.get('owner')}
        }

        for p in projects_data:
            role, owner = p.get('role'), p.get('owner')

            # Logika ikon
            if role == 'default':
                icon_file, label = 'domyslna.svg', 'Domyślna'
            elif role == 'predefined':
                icon_file, label = 'predefiniowana.svg', 'Predefiniowana'
            elif owner is not None and c_id is not None and str(owner) == str(c_id):
                icon_file, label = 'moja.svg', 'Moja'
            else:
                icon_file, label = 'udostepniona.svg', 'Udostępniona'

            row = [
                QStandardItem(label),
                QStandardItem(p.get('name', '')),
                QStandardItem(users.get(owner, 'Brak informacji')),
                QStandardItem(p.get('last_saved_at', '').replace('T', ' ')[:16])
            ]

            row[0].setIcon(QIcon(f":/plugins/usemaps-plugin/{icon_file}"))

            for item in row:
                item.setData(p, Qt.UserRole + 1)

            model.appendRow(row)

        header = self.mapTableView.horizontalHeader()
        header.sectionClicked.connect(self._handle_header_click)
        self.mapTableView.setModel(self.projects_proxy_model)
        self.mapTableView.setSortingEnabled(True)
        header = self.mapTableView.horizontalHeader()

        # Ustawienie domyślnego sortowania po dacie malejąco
        header.setSortIndicator(3, Qt.DescendingOrder)
        self.projects_proxy_model.sort(3, Qt.DescendingOrder)

        # Reset stanów sortowania
        self._sort_state = {i: 0 for i in range(4)}

        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Fixed)
        self.mapTableView.setColumnWidth(0, 25)
        self.mapTableView.setColumnWidth(1, 220)
        self.mapTableView.setColumnWidth(2, 125)
        self.mapTableView.setColumnWidth(3, 60)

        self.mapTableView.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

    def _handle_header_click(self, logical_index):
        header = self.mapTableView.horizontalHeader()

        if logical_index == 3:
            # Kolumna daty tylko 2 stany (malejąco <-> rosnąco)
            next_state = 2 if self._sort_state.get(3, 0) == 1 else 1
        else:
            # Pozostałe kolumny 3 stany (0 -> 1 -> 2 -> 0)
            next_state = (self._sort_state.get(logical_index, 0) + 1) % 3

        self._sort_state[logical_index] = next_state

        for col in list(self._sort_state.keys()):
            if col != logical_index:
                self._sort_state[col] = 0

        if next_state == 0:
            # Reset do stanu 0 powrót do sortowania po najnowszej dacie
            header.setSortIndicator(3, Qt.DescendingOrder)
            self.projects_proxy_model.sort(3, Qt.DescendingOrder)
            self._sort_state[3] = 2
        else:
            # Ustawienie wskazanego sortowania
            order = Qt.AscendingOrder if next_state == 1 else Qt.DescendingOrder
            header.setSortIndicator(logical_index, order)
            self.projects_proxy_model.sort(logical_index, order)

    def add_project_to_qgis(self, index):
        """Dodaje strukturę projektu do QGIS."""
        project_info = self.projects_proxy_model.mapToSource(index).data(Qt.UserRole + 1)
        if not project_info:
            return

        res = CONNECTION.get(f"/api/v2/projects/{project_info['id']}", sync=True)
        if not res or 'data' not in res:
            self.message(self.tr("Błąd pobierania danych projektu"), level=Qgis.Warning)
            return

        data = res['data']
        layers_list = data.get('layers', [])

        if not layers_list:
            self.message(self.tr("Projekt nie zawiera żadnych warstw."), level=Qgis.Info)
            return

        # Tworzenie głównej grupy projektu w QGIS
        root_group = QgsProject.instance().layerTreeRoot().addGroup(project_info['name'])

        def process_items(items, parent_group):
            """Funkcja tworząca podgrupy i ładująca warstwy."""
            if not isinstance(items, list):
                return

            for item in items:
                if (children := item.get('layers') or item.get('children')) is not None:
                    sub_group = parent_group.addGroup(item.get('name', 'Grupa'))
                    process_items(children, sub_group)
                    sub_group.setItemVisibilityChecked(
                        item.get('visible', True) and any(child.isVisible() for child in sub_group.children())
                    )
                else:
                    l_id = item.get('id') or item.get('layer_id')
                    if not l_id or item.get('layer_type') == 'mvt':
                        continue
                    l_class = (layers_registry.layers.get(l_id) or
                               layers_registry.layers.get(str(l_id)) or
                               layers_registry.layers.get(int(l_id) if str(l_id).isdigit() else None))
                    if l_class:
                        if (node := l_class.loadLayer(group=parent_group)):
                            node.setItemVisibilityChecked(item.get('visible', True))
                    else:
                        self.log(f"Nie znaleziono definicji warstwy o ID: {l_id}")

        process_items(res['data'].get('layers', []), root_group)
        self.message(self.tr(f"Zaimportowano projekt: {project_info['name']}"), duration=3)