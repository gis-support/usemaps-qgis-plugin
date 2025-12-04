def classFactory(iface):
    """Load plugin class from file plugin.

    :param iface: A QGIS interface instance.
    :type iface: QgsInterface
    """
    #
    from .plugin import UsemapsPlugin
    return UsemapsPlugin(iface)
