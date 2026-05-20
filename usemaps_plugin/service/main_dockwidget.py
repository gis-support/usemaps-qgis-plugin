import os

from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal, QEvent, Qt, QSortFilterProxyModel
from qgis.PyQt.QtGui import QIcon, QDropEvent, QDragEnterEvent, QStandardItemModel, QStandardItem

from qgis.utils import iface
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
        self.mapCanvas = iface.mapCanvas()
        self.mapCanvas.setAcceptDrops(True)

        self.loginSettingsDialog = LoginSettingsDialog(self)
        self.importLayerDialog = ImportLayerDialog()

        for btn, path in ((b, p) for b, p in (
            (self.connectButton, ":/plugins/usemaps-plugin/widget_disconnect.svg"),
            (self.authSettingsButton, ":/plugins/usemaps-plugin/widget_settings.svg"),
            (self.refreshButton, ":/plugins/usemaps-plugin/refresh.svg"),
            (self.addLayerButton, ":/plugins/usemaps-plugin/export.svg")
        )):
            btn.setProperty("icon_path", path)
            btn.setIcon(QIcon(btn.property("icon_path")))

        self.connectButton.setCheckable(True)

        self.authSettingsButton.clicked.connect(self.show_login_settings)

        self.layerBrowser.textChanged.connect(self.filter_tree_view)

        self.layerTreeView.setDragEnabled(True)
        self.layerTreeView.setAcceptDrops(False)
        self.layerTreeView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.layerTreeView.viewport().installEventFilter(self)

        self.proxy_model = QSortFilterProxyModel()
        self.proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.proxy_model.setRecursiveFilteringEnabled(True)

        layers_registry.on_schema.connect(self.add_layers_to_treeview)
        layers_registry.on_schema.connect(self.offers_projects_check_module)

        self.mapBrowser.textChanged.connect(self.filter_projects_view)

        self.projects_proxy_model = QSortFilterProxyModel()
        self.projects_proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.projects_proxy_model.setRecursiveFilteringEnabled(True)
        self.projects_proxy_model.setFilterKeyColumn(-1)

        self.mapTableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.mapTableView.doubleClicked.connect(self.add_project_to_qgis)
        self._sort_state = {}

        self.refreshButton.clicked.connect(self.handle_refresh)
        self.refreshButton.setEnabled(False)
        self.tabWidget.setCurrentIndex(0)

        self._offers_projects_sort_state = {}
        self._PROJECTS_TAB_INDEX = 2
        self.project_settings = None
        self.project_datasource_name = None
        self.project_id_field = None
        self.project_name_field = None

        self.offers_projects_setup_tableview()

        self.addLayerButton.clicked.connect(self.importLayerDialog.show)
        self.addLayerButton.setEnabled(False)

        self.mapCanvas.installEventFilter(self)

        apply_adaptive_palette(self)

        iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self)
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
                    layer_item.setData(layer_class, Qt.ItemDataRole.UserRole + 1)
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
                    group_item.setData([group['name'], group['id']], Qt.ItemDataRole.UserRole + 2)
                    add_layers(group_layers, group_item)
                    root_item.appendRow(group_item)


        add_groups(groups)
        self.layerTreeView.setModel(self.proxy_model)
        self.layerTreeView.setHeaderHidden(True)
        self.layerTreeView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.message(self.tr('Pobrano schemat warstw'), duration=3)

        self.refresh_layers()


    def add_layer_to_map(self, index):
        """
        Dodaje wybraną warstwę/grupę do projektu.
        """
        source_index = self.proxy_model.mapToSource(index)
        source_model = self.proxy_model.sourceModel()
        item = source_model.itemFromIndex(source_index)

        if group_data := item.data(Qt.ItemDataRole.UserRole + 2):
            layers_registry.loadGroup(group_data)

        elif layer_class := item.data(Qt.ItemDataRole.UserRole + 1):
            layer_class.loadLayer()


    def eventFilter(self, obj, event):
        """
        Event obsługujący dwa wydarzenia:
        1. dodawanie warstw/grup po przeciągnięciu na panel mapowy.
        2. dodawanie warstw/grup po dwukrotnym kliknięciu lewym przyciskiem myszy na drzewku warstw.
        """
        if obj == self.mapCanvas:
            if event.type() == QDragEnterEvent.Type.DragEnter:
                return self.handle_map_canvas_drag_enter(event)

            if event.type() == QDropEvent.Type.Drop:
                return self.handle_map_canvas_drop(event)


        if obj == self.layerTreeView.viewport() and event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                index = self.layerTreeView.indexAt(event.pos())
                if index.isValid():
                    self.add_layer_to_map(index)
                    return True

        if obj == self.tableProjects.viewport() and event.type() == QEvent.Type.MouseButtonDblClick:
            if event.button() == Qt.MouseButton.LeftButton:
                index = self.tableProjects.indexAt(event.pos())
                if index.isValid():
                    self.offers_projects_load_layers(index)
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

        res = CONNECTION.get('/api/v2/projects', sync=True)
        if isinstance(res, dict) and 'data' in res:
            self.load_projects_to_tableview(res['data'])

        mappings = get_layer_mappings()
        for layer in QgsProject.instance().mapLayers().values():
            if layers_registry.isSystemLayer(layer):
                layer_qgis_id = layer.id()
                layer_id = mappings.get(layer_qgis_id)
                if layer_id is None:
                    continue
                layer_class = layers_registry.layers.get(int(layer_id))

                if hasattr(layer_class, 'on_reload'):
                    layer_class.on_reload.emit(True)
                else:
                    layer.triggerRepaint()

    def handle_refresh(self) -> None:
        """Odświeża warstwy dodane do QGIS oraz dane we wszystkich widocznych zakładkach."""
        if not CONNECTION.is_connected:
            return

        layers_registry.loadData(True)

        self.refresh_layers()

        if self.tabWidget.isTabVisible(self._PROJECTS_TAB_INDEX):
            self.offers_projects_fetch_config()

    # Mapy

    def filter_projects_view(self, text):
        self.projects_proxy_model.setFilterFixedString(text)

    def load_projects_to_tableview(self, projects_data: list):
        """Wypełnia zakładkę Mapy danymi z endpointu /projects."""
        model = QStandardItemModel(0, 4)
        model.setHorizontalHeaderLabels([
            '',
            self.tr('Nazwa'),
            self.tr('Właściciel'),
            self.tr('Data ostatniej edycji')
            ])
        self.projects_proxy_model.setSourceModel(model)

        # Pobranie danych aktualnego uzytkownika
        current_data = (CONNECTION.get('/api/users/current_user', sync=True) or {}).get('data', {})
        c_id = current_data.get('id')
        c_name = current_data.get('name', '')

        # Jeśli ID to ID aktualnego uzytkownika, bierzemy c_name. W innym przypadku pytamy API
        users = {
            uid: (c_name if uid == c_id else (CONNECTION.get(f'/api/users/{uid}', sync=True) or {}).get('data', {}).get('name', ''))
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
                QStandardItem(users.get(owner, '')),
                QStandardItem(p.get('last_saved_at', '').replace('T', ' ')[:16])
            ]

            row[0].setIcon(QIcon(f":/plugins/usemaps-plugin/{icon_file}"))

            for item in row:
                item.setData(p, Qt.ItemDataRole.UserRole + 1)

            model.appendRow(row)

        header = self.mapTableView.horizontalHeader()
        header.sectionClicked.connect(self._handle_header_click)
        self.mapTableView.setModel(self.projects_proxy_model)
        self.mapTableView.setSortingEnabled(True)
        header = self.mapTableView.horizontalHeader()

        # Ustawienie domyślnego sortowania po dacie malejąco
        header.setSortIndicator(3, Qt.SortOrder.DescendingOrder)
        self.projects_proxy_model.sort(3, Qt.SortOrder.DescendingOrder)

        # Reset stanów sortowania
        self._sort_state = {i: 0 for i in range(4)}

        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Fixed)
        self.mapTableView.setColumnWidth(0, 25)
        self.mapTableView.setColumnWidth(1, 220)
        self.mapTableView.setColumnWidth(2, 125)
        self.mapTableView.setColumnWidth(3, 60)

        self.mapTableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

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
            header.setSortIndicator(3, Qt.SortOrder.DescendingOrder)
            self.projects_proxy_model.sort(3, Qt.SortOrder.DescendingOrder)
            self._sort_state[3] = 2
        else:
            # Ustawienie wskazanego sortowania
            order = Qt.SortOrder.AscendingOrder if next_state == 1 else Qt.SortOrder.DescendingOrder
            header.setSortIndicator(logical_index, order)
            self.projects_proxy_model.sort(logical_index, order)

    def add_project_to_qgis(self, index):
        """Dodaje strukturę projektu do QGIS."""
        project_info = self.projects_proxy_model.mapToSource(index).data(Qt.ItemDataRole.UserRole + 1)
        if not project_info:
            return

        res = CONNECTION.get(f"/api/v2/projects/{project_info['id']}", sync=True)
        if not res or 'data' not in res:
            self.message(self.tr("Błąd pobierania danych mapy"), level=Qgis.Warning)
            return

        data = res['data']
        layers_list = data.get('layers', [])

        if not layers_list:
            self.message(self.tr("Mapa nie zawiera żadnych warstw."), level=Qgis.Info)
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
                    l_id = item.get('id')
                    if not l_id or item.get('layer_type') == 'mvt':
                        continue
                    l_class = (layers_registry.layers.get(l_id) or
                               layers_registry.layers.get(str(l_id)) or
                               layers_registry.layers.get(int(l_id) if str(l_id).isdigit() else None))
                    if l_class:
                        map_layer_style = item.get('style')
                        if (node := l_class.loadLayer(group=parent_group, overridden_style_web=map_layer_style)):
                            node.setItemVisibilityChecked(item.get('visible', True))
                    else:
                        self.log(f"Nie znaleziono definicji warstwy o ID: {l_id}")

        process_items(res['data'].get('layers', []), root_group)
        self.message(self.tr("Zaimportowano mapę: {}").format(project_info['name']), duration=3)

    # Projekty

    def offers_projects_setup_tableview(self) -> None:
        """Konfiguruje wygląd i zachowanie zakładki projektów."""
        self.offers_projects_source_model = QStandardItemModel(0, 4, self)
        self.offers_projects_proxy_model = QSortFilterProxyModel(self)
        self.offers_projects_proxy_model.setSourceModel(self.offers_projects_source_model)
        self.offers_projects_proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.offers_projects_proxy_model.setFilterKeyColumn(-1)

        self.tableProjects.setModel(self.offers_projects_proxy_model)
        self.tableProjects.setSortingEnabled(True)
        self.tableProjects.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.tableProjects.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.tableProjects.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.tableProjects.horizontalHeader().setStretchLastSection(True)
        header = self.tableProjects.horizontalHeader()
        header.setVisible(False)
        header.setStretchLastSection(True)
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)

        header.sectionClicked.connect(self.offers_projects_handle_header_click)
        self.tableProjects.viewport().installEventFilter(self)
        self.projectBrowser.textChanged.connect(self.offers_projects_proxy_model.setFilterFixedString)

        self.tabWidget.setTabVisible(self._PROJECTS_TAB_INDEX, False)

    def offers_projects_check_module(self) -> None:
        if not CONNECTION.is_connected:
            return
        CONNECTION.get(
            '/api/license_manager/modules/OZE_MODULE',
            callback=self.offers_projects_on_module_check
        )

    def offers_projects_on_module_check(self, response: dict) -> None:
        data = (response or {}).get('data', {})
        if data.get('enabled') and data.get('configured'):
            CONNECTION.get(
                '/api/settings/oze_module_enabled',
                callback=self.offers_projects_on_setting_check
            )
        else:
            self.tabWidget.setTabVisible(self._PROJECTS_TAB_INDEX, False)

    def offers_projects_on_setting_check(self, response: dict) -> None:
        enabled = (response or {}).get('data', False)
        if enabled:
            self.tabWidget.setTabVisible(self._PROJECTS_TAB_INDEX, True)
            self.offers_projects_fetch_config()
        else:
            self.tabWidget.setTabVisible(self._PROJECTS_TAB_INDEX, False)

    def offers_projects_fetch_config(self) -> None:
        """Pobiera konfigurację źródła projektów."""
        if not CONNECTION.is_connected:
            return
        CONNECTION.get(
            '/api/dataio/selected_datasources/oze_projects_datasource',
            callback=self.offers_projects_process_config
        )

    def offers_projects_process_config(self, response: dict) -> None:
        if response and 'data' in response:
            self.project_settings = response['data'].get('settings', {})
            self.project_datasource_name = response['data'].get('datasource')

            if not self.project_datasource_name:
                self.message(self.tr("Brak skonfigurowanego źródła projektów."), level=1)
                return

            ds_meta = CONNECTION.get(f'/api/v2/datasources/{self.project_datasource_name}', sync=True) or {}
            ds_data = ds_meta.get('data', {})
            self.project_id_field = ds_data.get('pk_attribute', 'id')
            self.project_name_field = ds_data.get('label_attribute') or self.project_settings.get('name_attribute', 'nazwa')

            CONNECTION.post(
                f'/api/v2/datasources-features/read/{self.project_datasource_name}',
                payload={"data": {}},
                callback=self.offers_projects_populate_table
            )

    def offers_projects_populate_table(self, response: dict) -> None:
        """Wypełnia tabelę projektów danymi i ustawia domyślne sortowanie po ID rosnąco."""
        self.offers_projects_source_model.removeRows(0, self.offers_projects_source_model.rowCount())
        if not (response and 'data' in response):
            return

        self.offers_projects_source_model.setHorizontalHeaderLabels([
                        "ID",
                        self.tr("Nazwa"),
                        self.tr("Status"),
                        self.tr("Kierownik")
                        ])
        header = self.tableProjects.horizontalHeader()
        header.setVisible(True)

        for feature in response['data'].get('features', []):
            p = feature.get('properties', {})
            m_id = p.get(self.project_settings.get('manager_attribute', 'kierownik'))

            id_item = QStandardItem()
            id_item.setData(int(feature.get(self.project_id_field, 0)), Qt.ItemDataRole.DisplayRole)

            if m_id:
                user_data = (CONNECTION.get(f'/api/users/{m_id}', sync=True) or {}).get('data', {})
                manager_name = user_data.get('name') or user_data.get('username') or str(m_id)
            else:
                manager_name = ""
            manager_item = QStandardItem(manager_name)

            self.offers_projects_source_model.appendRow([
                id_item,
                QStandardItem(str(p.get(self.project_name_field, '') or "")),
                QStandardItem(str(p.get(self.project_settings.get('status_attribute', 'status'), '') or self.tr("Brak danych"))),
                manager_item
            ])

        # Domyślne sortowanie po ID rosnąco
        header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
        self.offers_projects_proxy_model.sort(0, Qt.SortOrder.AscendingOrder)
        self._offers_projects_sort_state = {i: 0 for i in range(4)}
        self._offers_projects_sort_state[0] = 1

    def offers_projects_handle_header_click(self, logical_index: int)-> None:
        """Obsługuje kliknięcie nagłówka tabeli projektów (3 stany sortowania)"""
        header = self.tableProjects.horizontalHeader()

        # Kolumna ID tylko 2 stany (rosnąco <-> malejąco), bez resetu
        if logical_index == 0:
            next_state = 2 if self._offers_projects_sort_state.get(0, 0) == 1 else 1
        else:
            next_state = (self._offers_projects_sort_state.get(logical_index, 0) + 1) % 3

        # Reset stanów pozostałych kolumn
        self._offers_projects_sort_state = {i: 0 for i in range(4)}
        self._offers_projects_sort_state[logical_index] = next_state

        if next_state == 0:
            # Powrót do domyślnego sortowania po ID rosnąco
            header.setSortIndicator(0, Qt.SortOrder.AscendingOrder)
            self.offers_projects_proxy_model.sort(0, Qt.SortOrder.AscendingOrder)
            self._offers_projects_sort_state[0] = 1
        else:
            order = Qt.SortOrder.AscendingOrder if next_state == 1 else Qt.DescendingOrder
            header.setSortIndicator(logical_index, order)
            self.offers_projects_proxy_model.sort(logical_index, order)

    def offers_projects_load_layers(self, index) -> None:
        """Pobiera relacje warstw dla wybranego projektu"""
        if not (index.isValid() and self.project_datasource_name):
            return

        project_id = self.offers_projects_proxy_model.data(self.offers_projects_proxy_model.index(index.row(), 0))
        project_name = self.offers_projects_proxy_model.data(self.offers_projects_proxy_model.index(index.row(), 1))

        CONNECTION.post(
            f"/api/dataio/data_sources/feature_assignment/{self.project_datasource_name}/{project_id}",
            payload={"data": {}},
            callback=lambda res: self.offers_projects_apply_layers(res, project_name)
        )

    def offers_projects_apply_layers(self, response: dict, project_name: str) -> None:
        """Tworzy grupę i ładuje do niej warstwy powiązane z projektem."""
        if not (response and 'data' in response):
            return

        assigned_sources = {
            item.get('data_source_name') for item in response['data']
            if item.get('data_source_name') and item.get('data_source_name') != 'attachments_attachment'
        }

        candidate_layers = [
            layer_class
            for layer_class in layers_registry.layers.values()
            if getattr(layer_class, 'datasource_name', None) in assigned_sources
        ]

        if not assigned_sources:
            self.message(self.tr("Projekt {} nie posiada powiązanych źródeł danych").format(project_name), level=1, duration=3)
            return

        if not candidate_layers:
            self.message(self.tr("Projekt {} nie posiada warstw dostępnych dla Ciebie").format(project_name), level=1, duration=3)
            return

        project_group = QgsProject.instance().layerTreeRoot().addGroup(project_name)
        loaded = 0

        for layer_class in candidate_layers:
            try:
                layer_class.loadLayer(group=project_group)
                loaded += 1
            except Exception as e:
                self.log(f"Błąd ładowania warstwy {getattr(layer_class, 'name', '?')}: {e}")

        if loaded == 0:
            QgsProject.instance().layerTreeRoot().removeChildNode(project_group)
            self.message(self.tr("Projekt {} nie posiada warstw dostępnych dla Ciebie").format(project_name), level=1, duration=3)
        else:
            self.message(self.tr("Wczytano warstwy projektu: {}").format(project_name), duration=3)

    def offers_projects_reset(self) -> None:
        """Resetuje stan modułu projektów"""
        self.offers_projects_source_model.removeRows(0, self.offers_projects_source_model.rowCount())
        self.tableProjects.horizontalHeader().setVisible(False)
        self.tabWidget.setTabVisible(self._PROJECTS_TAB_INDEX, False)

        self.project_settings = None
        self.project_datasource_name = None
        self.project_id_field = None
        self.project_name_field = None
