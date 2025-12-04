from PyQt5.QtWidgets import QAction
from qgis.PyQt.QtGui import QIcon
from qgis.core import QgsProject, QgsMapLayer

from ..tools.gisbox_connection import GISBOX_CONNECTION
from .layers.layers_registry import layers_registry
from .gisbox_dockwidget import GISBoxDockWidget

class GISBox():

    def __init__(self, parent):
        super().__init__()
        self.parent = parent
        self.parent.toolbar.addSeparator()
        self.dockwidget = GISBoxDockWidget()

        self.dockwidgetAction = self.parent.add_dockwidget_action(
            dockwidget = self.dockwidget,
            icon_path=":/plugins/gisbox-plugin/disconnected.png",
            text = 'Usemaps',
            add_to_topmenu=True
            )

        layers_registry.on_schema.connect(self.readProject)
        QgsProject.instance().readProject.connect(self.readProject)
        QgsProject.instance().readProject.connect(self.toggle_gisbox_layers_readonly_mode)
        self.dockwidget.connectButton.clicked.connect(self.onConnection)

    def onConnection(self, connect: bool):
        """ Połączenie/rozłączenie z serwerem """

        connected = connect and GISBOX_CONNECTION.connect()
        self.dockwidget.authSettingsButton.setEnabled(not connected)
        if connected:
            # Połączono z serwerem
            self.dockwidgetAction.setIcon(QIcon(":/plugins/gisbox-plugin/connected.png"))
            self.dockwidget.connectButton.setIcon(QIcon(":/plugins/gisbox-plugin/widget_disconnect.svg"))
            self.dockwidget.connectButton.setText('Wyloguj')
            self.dockwidget.refreshButton.setEnabled(True)

        else:
            # Rozłączono z serwerem lub błąd połączenia

            GISBOX_CONNECTION.disconnect()

            self.dockwidgetAction.setIcon(QIcon(":/plugins/gisbox-plugin/disconnected.png"))
            self.dockwidget.connectButton.setIcon(QIcon(":/plugins/gisbox-plugin/widget_connect.svg"))
            self.dockwidget.connectButton.setText('Zaloguj')
            self.dockwidget.refreshButton.setEnabled(False)
            self.dockwidget.connectButton.setChecked(False)
            self.dockwidget.clear_treeview()
        
        self.toggle_gisbox_layers_readonly_mode()


    def toggle_gisbox_layers_readonly_mode(self):
        """
        Przełącza tryb `read_only` warstw Usemaps.
        Wykorzystywane przy łączeniu/rozłączaniu z Usemaps.
        """
        is_connected = GISBOX_CONNECTION.is_connected
        for layer in QgsProject.instance().mapLayers().values():
            if layers_registry.isGisboxLayer(layer) and layer.type() == QgsMapLayer.VectorLayer:

                if is_connected:
                    # Odczytywanie uprawnień użytkownika do edycji warstwy
                    layer_id = layer.customProperty('gisbox/layer_id')
                    layer_permission = GISBOX_CONNECTION.current_user['permissions']['layers'].get(int(layer_id))

                    if layer_permission['main_value'] == 2:
                        layer.setReadOnly(False)
                    
                    else:
                        layer.setReadOnly(True)

                else:
                    if layer.isEditable():
                        layer.rollBack()
                    layer.setReadOnly(True)

    def readProject(self):
        if not GISBOX_CONNECTION.is_connected:
            return
        for layer in QgsProject.instance().mapLayers().values():
            if layers_registry.isGisboxLayer(layer):
                layer_class = layers_registry.layers[int(
                    layer.customProperty('gisbox/layer_id'))]
                layer_class.setLayer(layer, from_project=True)

