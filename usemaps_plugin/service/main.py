from qgis.PyQt.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProject, QgsMapLayer, QgsVectorTileLayer, QgsDataSourceUri
from qgis.PyQt.QtCore import QCoreApplication
import urllib.parse

from ..tools.connection import CONNECTION
from .layers.layers_registry import layers_registry
from .layers.datasources import Datasource
from .main_dockwidget import MainDockWidget
from ..tools.project_variables import get_layer_mapping, migrate_layer_gisbox_id_variable, remove_layer_mapping
from .gui.adaptive_palette import apply_adaptive_palette

class ServiceProvider():

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.parent.toolbar.addSeparator()
        self.dockwidget = MainDockWidget()

        self.dockwidgetAction = self.parent.add_dockwidget_action(
            dockwidget = self.dockwidget,
            icon_path=":/plugins/usemaps-plugin/disconnected.png",
            text = 'Usemaps',
            add_to_topmenu=True
            )

        layers_registry.on_schema.connect(self.readProject)
        QgsProject.instance().readProject.connect(self.readProject)
        QgsProject.instance().readProject.connect(self.toggle_system_layers_readonly_mode)
        QgsProject.instance().layerRemoved.connect(remove_layer_mapping)
        self.dockwidget.connectButton.clicked.connect(self.onConnection)

    def onConnection(self, connect: bool):
        """ Połączenie/rozłączenie z serwerem """

        connected = connect and CONNECTION.connect()
        self.dockwidget.authSettingsButton.setEnabled(not connected)
        if connected:
            # Połączono z serwerem
            self.dockwidgetAction.setIcon(QIcon(":/plugins/usemaps-plugin/connected.png"))
            self.dockwidget.connectButton.setProperty("icon_path", ":/plugins/usemaps-plugin/widget_connect.svg")
            self.dockwidget.connectButton.setIcon(QIcon(self.dockwidget.connectButton.property("icon_path")))
            self.dockwidget.connectButton.setText(QCoreApplication.translate("ServiceProvider", "Wyloguj"))
            self.dockwidget.refreshButton.setEnabled(True)

            projects_res = CONNECTION.get('/api/v2/projects', sync=True)
            if isinstance(projects_res, dict) and 'data' in projects_res:
                self.dockwidget.load_projects_to_tableview(projects_res['data'])
        else:
            # Rozłączono z serwerem lub błąd połączenia

            CONNECTION.disconnect()

            self.dockwidgetAction.setIcon(QIcon(":/plugins/usemaps-plugin/disconnected.png"))
            self.dockwidget.connectButton.setProperty("icon_path", ":/plugins/usemaps-plugin/widget_disconnect.svg")
            self.dockwidget.connectButton.setIcon(QIcon(self.dockwidget.connectButton.property("icon_path")))
            self.dockwidget.connectButton.setText(QCoreApplication.translate("ServiceProvider", "Zaloguj"))
            self.dockwidget.refreshButton.setEnabled(False)
            self.dockwidget.connectButton.setChecked(False)
            self.dockwidget.offers_projects_reset()
            self.dockwidget.clear_treeview()
            self.dockwidget.projects_proxy_model.sourceModel().clear()

        apply_adaptive_palette(self.dockwidget)

        self.toggle_system_layers_readonly_mode()


    def toggle_system_layers_readonly_mode(self):
        """
        Przełącza tryb `read_only` warstw Usemaps.
        Wykorzystywane przy łączeniu/rozłączaniu z Usemaps.
        """
        is_connected = CONNECTION.is_connected
        for layer in QgsProject.instance().mapLayers().values():
            if layers_registry.isSystemLayer(layer) and layer.type() == QgsMapLayer.LayerType.VectorLayer:

                if is_connected:
                    # Odczytywanie uprawnień użytkownika do edycji warstwy
                    layer_qgis_id = layer.id()
                    layer_id = get_layer_mapping(layer_qgis_id)
                    layer_permission = CONNECTION.current_user['permissions']['layers'].get(layer_id)

                    if layer_permission['main_value'] == 2:
                        layer.setReadOnly(False)

                    else:
                        layer.setReadOnly(True)

                else:
                    if layer.isEditable():
                        layer.rollBack()
                    layer.setReadOnly(True)

    def readProject(self):
        if not CONNECTION.is_connected:
            return
        token = CONNECTION.token
        for layer in QgsProject.instance().mapLayers().values():
            if layers_registry.isSystemLayer(layer):
                migrate_layer_gisbox_id_variable(layer)
                if CONNECTION.is_connected:
                    layer_qgis_id = layer.id()
                    layer_id = get_layer_mapping(layer_qgis_id)
                    layer_class = layers_registry.layers[layer_id]
                    if not isinstance(layer_class, Datasource):
                        layer_class.setLayer(layer)
                    else:
                        layer_class.setLayer(layer, from_project=True)
            elif isinstance(layer, QgsVectorTileLayer) and '/api/databox/mvt/' in layer.source():
                if token:
                    source_parts = layer.source().split('&')
                    current_tokens = [p.split('=', 1)[1] for p in source_parts if p.startswith('http-header:X-Access-Token=')]
                    if not current_tokens or current_tokens[0] != token:
                        new_parts = [p for p in source_parts if not p.startswith('http-header:X-Access-Token=')]
                        new_parts.append(f'http-header:X-Access-Token={token}')
                        new_source = '&'.join(new_parts)
                        layer.setDataSource(new_source, layer.name(), "vectortile")
                        layer.reload()
                        layer.triggerRepaint()

        self.dockwidget.refresh_layers()
