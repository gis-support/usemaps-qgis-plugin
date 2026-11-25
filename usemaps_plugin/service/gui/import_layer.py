import os

from qgis.PyQt import uic
from qgis.PyQt.QtWidgets import QDialog, QMessageBox
from qgis.PyQt.QtCore import Qt, QCoreApplication
from qgis.PyQt.QtNetwork import QHttpMultiPart, QHttpPart, QNetworkRequest, QNetworkReply
from qgis.utils import iface
from qgis.core import QgsMapLayerProxyModel, QgsJsonExporter, QgsProject

from ...tools.connection import CONNECTION
from .adaptive_palette import apply_adaptive_palette

FORM_CLASS, _ = uic.loadUiType(os.path.join(
    os.path.dirname(__file__), 'import_layer.ui'))

class ImportLayerDialog(QDialog, FORM_CLASS):
    """ Dialog wgrywania warstw do organizacji """
    def __init__(self):
        super(ImportLayerDialog, self).__init__(parent=iface.mainWindow())
        self.setupUi(self)
        self.setWindowFlags(self.windowFlags() | Qt.WindowType.WindowStaysOnTopHint)
        self.layer_combobox.setFilters(QgsMapLayerProxyModel.Filter.VectorLayer)

        self.cancel_button.clicked.connect(self.hide)
        self.add_button.clicked.connect(self.upload_to_usemaps)

        QgsProject.instance().layersAdded.connect(self.hide_layers_outside_legend)
        QgsProject.instance().layerTreeRoot().addedChildren.connect(self.hide_layers_outside_legend)

        apply_adaptive_palette(self)

    def showEvent(self, event):
        self.hide_layers_outside_legend()
        super().showEvent(event)

    def hide_layers_outside_legend(self, *args):
        """ Ukrycie warstw spoza legendy """
        root = QgsProject.instance().layerTreeRoot()
        self.layer_combobox.setExceptedLayerList([
            layer for layer in QgsProject.instance().mapLayers().values()
            if not root.findLayer(layer.id())
        ])

    def upload_to_usemaps(self):
        """ Przesyła warstwę do Usemaps jako GeoJSON. """
        layer = self.layer_combobox.currentLayer()

        if not (layer and any(True for _ in layer.getFeatures())):
            return

        self.add_button.setEnabled(False)
        self.add_button.setText(self.tr("Wysyłanie..."))

        multi_part = QHttpMultiPart(QHttpMultiPart.ContentType.FormDataType)

        geojson_part = QHttpPart()
        geojson_part.setHeader(QNetworkRequest.KnownHeaders.ContentDispositionHeader,
                               'form-data; name="geojson"; filename="layer.geojson"')
        geojson_part.setBody(QgsJsonExporter(layer).exportFeatures(layer.getFeatures()).encode('utf-8'))
        multi_part.append(geojson_part)

        for name, value in {
            "verbose_name": layer.name(),
            "target_srid": str(layer.crs().postgisSrid() if layer.crs().postgisSrid() > 0 else 4326),
            "create_layer": "true",
            "permissions": "[]" # Brak dostępu
        }.items():
            part = QHttpPart()
            part.setHeader(QNetworkRequest.KnownHeaders.ContentDispositionHeader, f'form-data; name="{name}"')
            part.setBody(value.encode('utf-8'))
            multi_part.append(part)

        request = CONNECTION._createRequest("/api/v2/datasources-upload/geojson", with_token=True)
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, None)

        reply = CONNECTION.MANAGER.post(request, multi_part)
        multi_part.setParent(reply)

        while not reply.isFinished():
            QCoreApplication.processEvents()

        if reply.error() == QNetworkReply.NetworkError.NoError:
            QMessageBox.information(self, self.tr("Sukces"), self.tr("Warstwa została dodana do Usemaps."))
            self.hide()
        else:
            QMessageBox.critical(self, self.tr("Błąd"), f"{self.tr('Nie udało się przesłać warstwy do Usemaps')}")

        self.add_button.setEnabled(True)
        self.add_button.setText(self.tr("Dodaj"))