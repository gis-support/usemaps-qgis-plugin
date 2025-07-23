import os.path

from PyQt5.QtCore import (QCoreApplication, QUrl)
from PyQt5.QtGui import QDesktopServices, QIcon
from PyQt5.QtWidgets import QAction, QDockWidget

from .resources import resources
from .tools.gisbox_connection import GISBOX_CONNECTION
from .gisbox.main import GISBox

PLUGIN_NAME = "Wtyczka GIS.Box"

class GISBoxPlugin:


    def __init__(self, iface):

        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)

        self.actions = []
        self.modules = []
        self.menu = self.tr(u'&Wtyczka GIS.Box')
        self.toolbar = self.iface.addToolBar(PLUGIN_NAME)
        self.toolbar.addSeparator

    def tr(self, message):
        return QCoreApplication.translate('GISBoxPlugin', message)

    def add_action(
        self,
        icon_path,
        text,
        callback=None,
        enabled_flag=True,
        add_to_menu=True,
        add_to_topmenu=False,
        add_to_toolbar=True,
        status_tip=None,
        whats_this=None,
        parent=None,
        checkable = False,
        enabled=True):

        icon = QIcon(icon_path)
        action = QAction(icon, text, parent)
        action.triggered.connect(callback)
        action.setEnabled(enabled_flag)
        action.setCheckable(checkable)

        if status_tip is not None:
            action.setStatusTip(status_tip)

        if whats_this is not None:
            action.setWhatsThis(whats_this)

        if add_to_toolbar:
            self.toolbar.addAction(action)

        if add_to_menu:
            self.iface.addPluginToMenu(
                self.menu,
                action)
        
        if add_to_topmenu:
            self.topMenu.addAction(action)

        action.setEnabled(enabled)

        self.actions.append(action)

        return action

    def add_dockwidget_action(self, dockwidget: QDockWidget, icon_path: str, text: str, add_to_topmenu: bool = False):

        dockwidget_action = dockwidget.toggleViewAction()
        dockwidget_action.setIcon(QIcon(icon_path))
        dockwidget_action.setText(text)

        self.toolbar.addAction(dockwidget_action)

        if add_to_topmenu:
            self.topMenu.addAction(dockwidget_action)

        return dockwidget_action

    # def initModules(self, modules: list = ['uldk', 'gugik_nmt', 'wms', 'wmts', 'mapster', 'data_downloader']):
    #     """ Włączenie modułów """

    #     modules_path = Path( self.plugin_dir ).joinpath('modules')
    #     #Iteracja po modułach dodatkowych
    #     for module_name in modules:
    #         main_module = modules_path.joinpath(module_name).joinpath('main.py')
    #         #Załadowanie modułu
    #         spec = util.spec_from_file_location('main', main_module)
    #         module = util.module_from_spec(spec)
    #         spec.loader.exec_module(module)
    #         #Lista obiektów w module
    #         clsmembers = inspect.getmembers(module, inspect.isclass)
    #         for (_, c) in clsmembers:
    #             # Odrzucamy inne klasy niż dziedziczące po klasie bazowej
    #             if issubclass(c, BaseModule) and c is not BaseModule:
    #                 #Aktywacja i rejestracja modułu
    #                 self.modules.append( c(self) )

    def initGui(self):

        self.gisbox = GISBox(self)
        self.topMenu = self.iface.mainWindow().menuBar().addMenu(u'&GIS.Box')

        # self.initModules()

        self.topMenu.addSeparator()
        self.topMenu.setObjectName('gisSupportMenu')

        # self.initModules(["gisbox"])

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        GISBOX_CONNECTION.disconnect()
        for action in self.actions:
            self.iface.removePluginMenu(
                self.menu,
                action)
        #Wyłączenie modułów
        # for module in self.modules:
        #     module.unload()

        self.toolbar.clear()
        self.toolbar.deleteLater()
        self.topMenu.clear()
        self.topMenu.deleteLater()

    def open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))