def classFactory(iface):
    """Load GISBoxPlugin class from file gisbox_plugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .gisbox_plugin import GISBoxPlugin
    return GISBoxPlugin(iface)
