import os.path

from qgis.PyQt.QtCore import QCoreApplication, QUrl, QSettings, QTranslator
from qgis.PyQt.QtGui import QDesktopServices, QIcon
from qgis.PyQt.QtWidgets import QAction, QDockWidget

from .resources import resources
from .tools.connection import CONNECTION
from .service.main import ServiceProvider

PLUGIN_NAME = "Wtyczka Usemaps"

class UsemapsPlugin:


    def __init__(self, iface):

        self.iface = iface
        self.plugin_dir = os.path.dirname(__file__)
        self.install_translation()
        self.actions = []
        self.modules = []
        self.menu = self.tr(u'&Wtyczka Usemaps')
        self.toolbar = self.iface.addToolBar(PLUGIN_NAME)
        self.toolbar.addSeparator

    def install_translation(self):
        locale = QSettings().value('locale/userLocale')[0:2]
        self.translator = QTranslator()
        i18n_path = os.path.join(self.plugin_dir, "i18n", f"usemaps_plugin_{locale}.qm")
        if not os.path.exists(i18n_path):
            i18n_path = os.path.join(self.plugin_dir, "i18n", "usemaps_plugin_en.qm")
        self.translator.load(i18n_path)
        QCoreApplication.installTranslator(self.translator)

    def tr(self, message):
        return QCoreApplication.translate('UsemapsPlugin', message)

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

    def initGui(self):

        self.topMenu = self.iface.mainWindow().menuBar().addMenu(u'&Usemaps')

        self.service = ServiceProvider(self)

        self.topMenu.addSeparator()
        self.topMenu.setObjectName('gisSupportMenu')

    def unload(self):
        """Removes the plugin menu item and icon from QGIS GUI."""
        CONNECTION.disconnect()
        for action in self.actions:
            self.iface.removePluginMenu(
                self.menu,
                action)

        self.toolbar.clear()
        self.toolbar.deleteLater()
        self.topMenu.clear()
        self.topMenu.deleteLater()

    def open_url(self, url):
        QDesktopServices.openUrl(QUrl(url))