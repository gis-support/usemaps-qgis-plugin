import os
from typing import Optional

import json
from qgis.PyQt import QtWidgets, uic
from qgis.PyQt.QtCore import pyqtSignal, QEvent, Qt, QSortFilterProxyModel
from qgis.PyQt.QtGui import QIcon, QDropEvent, QDragEnterEvent, QStandardItemModel, QStandardItem
from qgis.core import (QgsProject, Qgis, QgsMapLayer, QgsVectorLayer,
                       QgsGeometry, QgsWkbTypes, QgsPalLayerSettings,
                       QgsRuleBasedRenderer, QgsSingleSymbolRenderer, QgsSymbol,
                       QgsVectorLayerSimpleLabeling, QgsRuleBasedLabeling)

from qgis.utils import iface
from .layers.mvt_layer import MVTLayer, FALLBACK_COLOR
from .layers.layers_registry import layers_registry
from ..tools.logger import Logger
from .gui.login_settings import LoginSettingsDialog
from .gui.import_layer import ImportLayerDialog
from ..tools.connection import CONNECTION
from ..tools.project_variables import get_layer_mappings
from .gui.adaptive_palette import apply_adaptive_palette
from ..tools.identify_tool import UsemapsIdentifyTool
from ..tools.gs_select_area import GsSelectArea


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
        self.identify_tool = UsemapsIdentifyTool(self.mapCanvas, self)
        self.select_area_widget = None

        for btn, path in ((b, p) for b, p in (
            (self.connectButton, ":/plugins/usemaps-plugin/widget_disconnect.svg"),
            (self.authSettingsButton, ":/plugins/usemaps-plugin/widget_settings.svg"),
            (self.refreshButton, ":/plugins/usemaps-plugin/refresh.svg"),
            (self.addLayerButton, ":/plugins/usemaps-plugin/export.svg"),
            (self.btnIdentify, ":/plugins/usemaps-plugin/info.svg")
        )):
            btn.setProperty("icon_path", path)
            btn.setIcon(QIcon(btn.property("icon_path")))

        self.btnIdentify.setToolTip(self.tr("Narzędzie identyfikacji. Włącz, a następnie kliknij obiekt na mapie, aby sprawdzić jego atrybuty."))
        self.btnIdentify.clicked.connect(self.toggle_identify)
        iface.layerTreeView().currentLayerChanged.connect(self.validate_active_layer)
        self.validate_active_layer(iface.activeLayer())

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
        layers_registry.on_schema.connect(self.databox_check_module)

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
        self._DATABOX_TAB_INDEX = 4
        self.project_settings = None
        self.project_datasource_name = None
        self.project_id_field = None
        self.project_name_field = None

        self.offers_projects_setup_tableview()
        self.databox_setup_tableview()

        self.addLayerButton.clicked.connect(self.importLayerDialog.show)
        self.addLayerButton.setEnabled(False)

        self.mapCanvas.installEventFilter(self)
        self.mapCanvas.mapToolSet.connect(self._on_map_tool_set)

        apply_adaptive_palette(self)

        iface.addDockWidget(Qt.DockWidgetArea.RightDockWidgetArea, self)
        self.hide()

    def _on_map_tool_set(self, tool):
        try:
            self.btnIdentify.setChecked(tool == self.identify_tool)
        except RuntimeError:
            pass

    def closeEvent(self, event):
        self.mapCanvas.removeEventFilter(self)
        try:
            self.mapCanvas.mapToolSet.disconnect(self._on_map_tool_set)
        except (TypeError, RuntimeError):
            pass
        self.identify_tool.clear_highlight()
        if self.select_area_widget:
            self.select_area_widget.closeWidget()
        self.closingPlugin.emit()
        if event:
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
        self.identify_tool.clear_highlight()

        self.btnIdentify.setChecked(False)
        self.btnIdentify.setEnabled(False)
        self.mapCanvas.unsetMapTool(self.identify_tool)

        self.attributeTabWidget.clear()

        if self.proxy_model.sourceModel():
            self.proxy_model.sourceModel().clear()
        else:
            self.layerTreeView.setModel(None)

        self.addLayerButton.setEnabled(False)
        self.offers_projects_reset()
        self.databox_reset()

    def add_layers_to_treeview(self, groups: list):
        """
        Dodaje warstwy/grupy do drzewka warstw.
        Wywoływane po zalogowaniu.
        """
        modules_layer_custom_id = -99

        tree_model = QStandardItemModel()
        self.proxy_model.setSourceModel(tree_model)
        root_item = tree_model.invisibleRootItem()

        self.addLayerButton.setEnabled(CONNECTION.current_user.get('is_admin', False) if CONNECTION.current_user else False)
        self.addLayerButton.setToolTip(
            "" if self.addLayerButton.isEnabled() else self.tr("Tylko administrator może dodać nową warstwę do organizacji")
        )

        def add_layers(layers: list, group_item: QStandardItem):
            if not layers:
                return

            for layer in layers:
                layer_class = layers_registry.layers.get(layer.get("id"))

                if layer_class:
                    if hasattr(layer_class, 'datasource') and layer_class.datasource_name == 'foreign_vehicles':
                        continue

                    layer_item = QStandardItem(layer_class.name)
                    layer_item.setData(layer_class, Qt.ItemDataRole.UserRole + 1)
                    group_item.appendRow(layer_item)

        def add_groups(groups: list):
            for group in groups:
                if not isinstance(group, dict) or not group.get('layers'):
                    continue

                if group['id'] == modules_layer_custom_id:
                    continue

                if group['schema_scope'] == 'core':
                    group_item = QStandardItem(group['name'])
                    group_item.setData([group['name'], group['id']], Qt.ItemDataRole.UserRole + 2)
                    add_layers(group.get('layers'), group_item)
                    root_item.appendRow(group_item)

        add_groups(groups)
        self.layerTreeView.setModel(self.proxy_model)
        self.layerTreeView.setHeaderHidden(True)
        self.layerTreeView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.message(self.tr('Pobrano schemat warstw'), duration=3)

        self.refresh_layers()
        self.validate_active_layer(iface.activeLayer())

    def add_layer_to_map(self, index):
        """
        Dodaje wybraną warstwę/grupę do projektu.
        """
        item = self.proxy_model.sourceModel().itemFromIndex(self.proxy_model.mapToSource(index))
        group_data = item.data(Qt.ItemDataRole.UserRole + 2)

        if group_data:
            layers_registry.loadGroup(group_data)
        else:
            layer_class = item.data(Qt.ItemDataRole.UserRole + 1)
            if layer_class:
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

        # TODO: w przyszłości po dostoswaniu api przejść na samo /api/v2/projects?with_default=true (SRVS-2989)
        def fetch_all_projects():
            default_res = CONNECTION.get('/api/v2/projects-default', sync=True) or {}
            if 'data' in default_res:
                yield default_res['data']

            projects_res = CONNECTION.get('/api/v2/projects', sync=True) or {}
            if 'data' in projects_res:
                yield from projects_res['data']

        self.load_projects_to_tableview(list(fetch_all_projects()))

        mappings = get_layer_mappings()
        for layer in QgsProject.instance().mapLayers().values():
            if layers_registry.isSystemLayer(layer):
                layer_id = mappings.get(layer.id())
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

        if self.tabWidget.isTabVisible(self._DATABOX_TAB_INDEX):
            self.databox_fetch_layers()

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

        # Jeśli ID to ID aktualnego uzytkownika, bierzemy nazwę z current_data. W innym przypadku pytamy API
        users = {
            uid: (current_data.get('name', '') if uid == current_data.get('id') else (CONNECTION.get(f'/api/users/{uid}', sync=True) or {}).get('data', {}).get('name', ''))
            for uid in {p.get('owner') for p in projects_data if p.get('owner')}
        }

        for p in projects_data:
            role, owner = p.get('role'), p.get('owner')

            # Logika ikon
            if role == 'default':
                icon_file, label = 'domyslna.svg', 'Domyślna'
            elif role == 'predefined':
                icon_file, label = 'predefiniowana.svg', 'Predefiniowana'
            elif owner is not None and current_data.get('id') is not None and str(owner) == str(current_data.get('id')):
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

        # TODO: w przyszłości przejść tylko na CONNECTION.get(f"/api/v2/projects/{project_info['id']}", sync=True) (SRVS-2989)
        if project_info.get('role') == 'default':
            res = CONNECTION.get("/api/v2/projects-default", sync=True)
        else:
            res = CONNECTION.get(f"/api/v2/projects/{project_info['id']}", sync=True)

        if not res or not res.get('data', {}).get('layers'):
            self.message(self.tr("Mapa nie zawiera żadnych warstw lub wystąpił błąd."), level=Qgis.Warning)
            return

        # Tworzenie głównej grupy projektu w QGIS
        root_group = QgsProject.instance().layerTreeRoot().addGroup(project_info['name'])

        def process_items(items, parent_group):
            """Funkcja tworząca podgrupy i ładująca warstwy."""
            if not isinstance(items, list):
                return

            for item in items:
                children = item.get('layers') or item.get('children')

                if children is not None:
                    sub_group = parent_group.addGroup(item.get('name', 'Grupa'))
                    process_items(children, sub_group)
                    sub_group.setItemVisibilityChecked(
                        item.get('visible', True) and any(child.isVisible() for child in sub_group.children())
                    )
                else:
                    if not item.get('id') or item.get('layer_type') == 'mvt':
                        continue

                    l_class = (layers_registry.layers.get(item.get('id')) or
                               layers_registry.layers.get(str(item.get('id'))) or
                               layers_registry.layers.get(int(item.get('id')) if str(item.get('id')).isdigit() else None))

                    if l_class:
                        node = l_class.loadLayer(group=parent_group, overridden_style_web=item.get('style'))
                        if node:
                            node.setItemVisibilityChecked(item.get('visible', True))
                    else:
                        self.log(f"Nie znaleziono definicji warstwy o ID: {item.get('id')}")

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
        if (response or {}).get('data', False):
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

            ds_data = (CONNECTION.get(f'/api/v2/datasources/{self.project_datasource_name}', sync=True) or {}).get('data', {})
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

            self.offers_projects_source_model.appendRow([
                id_item,
                QStandardItem(str(p.get(self.project_name_field, '') or "")),
                QStandardItem(str(p.get(self.project_settings.get('status_attribute', 'status'), '') or self.tr("Brak danych"))),
                QStandardItem(manager_name)
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

    # Data.Box

    def databox_setup_tableview(self) -> None:
        self.databox_source_model = QStandardItemModel(0, 1, self)
        self.databox_proxy_model = QSortFilterProxyModel(self)
        self.databox_proxy_model.setSourceModel(self.databox_source_model)
        self.databox_proxy_model.setFilterCaseSensitivity(Qt.CaseSensitivity.CaseInsensitive)
        self.databox_proxy_model.setFilterKeyColumn(0)

        self.databoxTableView.setModel(self.databox_proxy_model)
        self.databoxTableView.setSortingEnabled(True)
        self.databoxTableView.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)
        self.databoxTableView.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.databoxTableView.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.databoxTableView.horizontalHeader().setVisible(False)
        self.databoxTableView.horizontalHeader().setStretchLastSection(True)

        self.databoxTableView.viewport().installEventFilter(self)
        self.databoxBrowser.textChanged.connect(self.databox_proxy_model.setFilterFixedString)

        self.tabWidget.setTabVisible(self._DATABOX_TAB_INDEX, False)

        self.btnLoadDataboxMvt.clicked.connect(self.databox_load_selected_mvt)

        # Inicjalizacja narzędzia do wskazywania obszaru
        self.select_area_widget = GsSelectArea(self)
        self.layoutSelectArea.addWidget(self.select_area_widget)
        self.btnDownloadData.clicked.connect(self.databox_download_data)

        self.download_geometry_geojson = None
        self.select_area_widget.geometryCreated.connect(self.on_download_geometry_created)

    def on_download_geometry_created(self, geom: QgsGeometry):
        if geom and not geom.isNull():
            self.download_geometry_geojson = json.loads(geom.asJson())
            self.download_geometry_geojson["crs"] = {
                "type": "name",
                "properties": {
                    "name": QgsProject.instance().crs().authid()
                }
            }
        else:
            self.download_geometry_geojson = None

    def databox_check_module(self) -> None:
        if not CONNECTION.is_connected:
            return
        CONNECTION.get(
            '/api/license_manager/modules/DATABOX_DATA_MODULE',
            callback=self.databox_on_module_check
        )

    def databox_on_module_check(self, response: dict) -> None:
        is_enabled = (response or {}).get('data', {}).get('enabled', False)
        self.tabWidget.setTabVisible(self._DATABOX_TAB_INDEX, is_enabled)
        if is_enabled:
            self.databox_fetch_layers()

    def databox_fetch_layers(self) -> None:
        if not CONNECTION.is_connected:
            return
        CONNECTION.get(
            '/api/databox/layers/metadata?tag=qgis',
            callback=self.databox_on_layers_fetched
        )

    def databox_on_layers_fetched(self, response: dict) -> None:
        if not response or 'data' not in response:
            self.log("Błąd pobierania metadanych Data.Box")
            return

        self.databox_source_model.removeRows(0, self.databox_source_model.rowCount())
        for layer_data in response['data']:
            item = QStandardItem(layer_data.get('title') or layer_data.get('name'))
            item.setData(layer_data, Qt.ItemDataRole.UserRole + 1)
            self.databox_source_model.appendRow([item])

    def _get_selected_layer_data(self) -> Optional[dict]:
        index = self.databoxTableView.currentIndex()
        if not index.isValid():
            return
        return self.databox_source_model.itemFromIndex(self.databox_proxy_model.mapToSource(index)).data(Qt.ItemDataRole.UserRole + 1)

    def databox_load_selected_mvt(self) -> None:
        layer_data = self._get_selected_layer_data()
        if not layer_data:
            return
        mvt = MVTLayer(layer_data, parent=self)
        mvt.loadLayer()
        self.mapCanvas.setMapTool(None)

    def databox_download_data(self) -> None:
        layer_data = self._get_selected_layer_data()
        if not layer_data:
            self.message(
                self.tr("Wybierz warstwę z tabeli do pobrania."),
                level=Qgis.MessageLevel.Warning,
                duration=3
            )
            return

        if not self.download_geometry_geojson:
            self.message(
                self.tr("Nie wskazano obszaru na mapie."),
                level=Qgis.MessageLevel.Warning,
                duration=3
            )
            return

        self.mapCanvas.setMapTool(None)

        payload = {
            "data": {
                "geojson": self.download_geometry_geojson,
                "databox_layers": [layer_data.get('name')]
            }
        }

        self.message(self.tr("Rozpoczynam pobieranie obszaru..."), duration=3)
        self.btnDownloadData.setEnabled(False)
        self.current_download_layer_data = layer_data
        CONNECTION.post(
            '/api/databox/download_data_v2?background=false',
            payload=payload,
            callback=self.databox_on_data_downloaded
        )

    def databox_on_data_downloaded(self, response: dict) -> None:
        self.btnDownloadData.setEnabled(True)
        if not response or 'data' not in response:
            self.message(
                self.tr("Błąd podczas pobierania danych."),
                level=Qgis.MessageLevel.Critical,
                duration=3
            )
            return

        collections = {"pobrane_dane": response['data']} if isinstance(response['data'], dict) and response['data'].get("type") == "FeatureCollection" else response['data']

        for collection_name, collection in collections.items():
            if not collection.get("features"):
                self.message(
                    self.tr(f"Brak obiektów na wykszonym obszarze dla warstwy {collection_name}."),
                    level=Qgis.MessageLevel.Info,
                    duration=3
                )
                continue

            temp_layer = QgsVectorLayer(json.dumps(collection), "temp", "ogr")
            if not temp_layer.isValid():
                self.message(
                    self.tr(f"Nie udało się utworzyć warstwy z pobranych danych dla {collection_name}."),
                    level=Qgis.MessageLevel.Critical,
                    duration=3
                )
                continue

            memory_layer = QgsVectorLayer(f"{QgsWkbTypes.displayString(temp_layer.wkbType())}?crs={temp_layer.crs().authid()}", self.current_download_layer_data.get('title') or collection_name, "memory")
            provider = memory_layer.dataProvider()
            provider.addAttributes(temp_layer.fields())
            memory_layer.updateFields()
            provider.addFeatures(list(temp_layer.getFeatures()))
            memory_layer.updateExtents()

            self._apply_vector_symbology(memory_layer, self.current_download_layer_data)
            QgsProject.instance().addMapLayer(memory_layer)
            self.message(self.tr(f"Pomyślnie wczytano obiekty dla {collection_name}."), duration=3)

    def _apply_vector_symbology(self, vlayer: QgsMapLayer, layer_data: dict) -> None:
        style_data = layer_data.get('style', {})
        if not style_data:
            return

        uniques = style_data.get('uniques', {})

        if uniques and uniques.get('values'):
            renderer = QgsRuleBasedRenderer(QgsSymbol.defaultSymbol(vlayer.geometryType()))
            root_rule = renderer.rootRule()
            while root_rule.children():
                root_rule.removeChild(root_rule.children()[0])

            labeling_root = QgsRuleBasedLabeling.Rule(QgsPalLayerSettings())
            while labeling_root.children():
                labeling_root.removeChild(labeling_root.children()[0])
            has_labels = False

            for key, value in uniques['values'].items():
                if MVTLayer.is_null_key(key):
                    continue
                filter_expr = f'"{uniques.get("property", "")}" = \'{key}\''

                rule = QgsRuleBasedRenderer.Rule(MVTLayer.create_symbol(value))
                rule.setFilterExpression(filter_expr)
                rule.setLabel(str(key))
                root_rule.appendChild(rule)

                if value.get('labels'):
                    has_labels = True
                    ls = MVTLayer.create_labeling_style(value['labels'])
                    settings = ls.labelSettings()
                    l_rule = QgsRuleBasedLabeling.Rule(settings)
                    l_rule.setFilterExpression(filter_expr)
                    if settings.scaleVisibility:
                        l_rule.setMinimumScale(settings.minimumScale)
                        l_rule.setMaximumScale(settings.maximumScale)
                    labeling_root.appendChild(l_rule)

            else_rule = QgsRuleBasedRenderer.Rule(MVTLayer.create_symbol({
                'fill-color': FALLBACK_COLOR,
                'fill-outline-color': '#000000',
                'fill-opacity': 0.7
            }))
            else_rule.setIsElse(True)
            else_rule.setLabel("Pozostałe")
            root_rule.appendChild(else_rule)

            vlayer.setRenderer(renderer)
            if has_labels:
                vlayer.setLabeling(QgsRuleBasedLabeling(labeling_root))
                vlayer.setLabelsEnabled(True)

        else:
            vlayer.setRenderer(QgsSingleSymbolRenderer(MVTLayer.create_symbol(style_data)))

            if style_data.get('labels'):
                ls = MVTLayer.create_labeling_style(style_data['labels'])
                vlayer.setLabeling(QgsVectorLayerSimpleLabeling(ls.labelSettings()))
                vlayer.setLabelsEnabled(True)

    def databox_reset(self) -> None:
        self.databox_source_model.removeRows(0, self.databox_source_model.rowCount())
        self.tabWidget.setTabVisible(self._DATABOX_TAB_INDEX, False)

    # Identyfikacja

    def toggle_identify(self, checked: bool) -> None:
        """Przełącza narzędzie mapy na podstawie stanu przycisku."""
        if checked:
            self.mapCanvas.setMapTool(self.identify_tool)
            self.tabWidget.setCurrentIndex(self.tabWidget.indexOf(self.identifyTab))
        else:
            self.mapCanvas.unsetMapTool(self.identify_tool)

    def validate_active_layer(self, layer: Optional[QgsMapLayer]) -> None:
        """Włącza lub wyłącza przycisk identyfikacji w zależności od stanu logowania i warstwy."""

        # Przycisk jest aktywny tylko gdy: zalogowano i warstwa jest usemaps
        self.btnIdentify.setEnabled(bool(CONNECTION.is_connected and layer and layers_registry.isSystemLayer(layer)))

        # Wyłączenie narzędzia na mapie, jeśli przycisk został wyłączony
        if not self.btnIdentify.isEnabled() and self.btnIdentify.isChecked():
            self.btnIdentify.setChecked(False)
            self.mapCanvas.unsetMapTool(self.identify_tool)