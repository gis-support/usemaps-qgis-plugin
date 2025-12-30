from traceback import print_exc
from owslib.wmts import WebMapTileService
from qgis.core import QgsNetworkAccessManager
from owslib.wms import WebMapService
from owslib.wfs import WebFeatureService
from qgis.PyQt.QtNetwork import QNetworkRequest, QNetworkReply
from qgis.PyQt.QtCore import QUrl, QCoreApplication
from typing import Union

try:
  import defusedxml.ElementTree as et
  from defusedxml.common import EntitiesForbidden
except (ModuleNotFoundError, ImportError):
  from ..lib.defusedxml import ElementTree as et
  from ..lib.defusedxml.common import EntitiesForbidden

class CapabilitiesConnectionException(Exception):
    def __init__(self, code: int, *args, **kwargs):
            self.code = code
            super().__init__(*args, **kwargs)

def get_capabilities(url: str, type: str) -> Union[WebMapService, WebFeatureService]:
    manager = QgsNetworkAccessManager()
    
    request_url = f'{url}?service={type}&request=GetCapabilities'
    request = QNetworkRequest(QUrl(request_url))
    reply = manager.blockingGet(request)
    
    if reply.error() != QNetworkReply.NetworkError.NoError or not reply.content():
        raise CapabilitiesConnectionException(code=reply.error())

    content = reply.content()
    data = content.data()
    try:
        xml = et.fromstring(data)
    except EntitiesForbidden as e:
        print_exc()
        raise CapabilitiesConnectionException(code=409, message=QCoreApplication.translate("Capabilities", "Dokument XML pobrany z adresu {} zawiera potencjalnie niebezpieczne fragmenty i został zablokowany").format(url)) from e # Tekst do tłumaczenia
    version =  xml.attrib.get("version")
    
    if type == "WMS":
        return WebMapService(url="", version=version, xml=data)
    elif type == "WFS":
        return WebFeatureService(url="", version=version, xml=data)
    elif type == "WMTS":
        return WebMapTileService(url="", version=version, xml=data)
