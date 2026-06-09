import re
from typing import Optional, Any
from qgis.core import (
    QgsProject, QgsVectorTileLayer, QgsVectorTileBasicRenderer,
    QgsVectorTileBasicRendererStyle, QgsVectorTileBasicLabeling,
    QgsVectorTileBasicLabelingStyle,
    QgsWkbTypes, QgsFillSymbol, QgsUnitTypes,
    QgsPalLayerSettings, QgsTextFormat, Qgis
)
from qgis.PyQt.QtCore import QObject
from qgis.PyQt.QtGui import QColor

from ...tools.connection import CONNECTION
from ...tools.logger import Logger
from .datasources import RASTER_ZOOM_LEVEL

FALLBACK_COLOR = '#b92626'


class MVTLayer(QObject, Logger):
    def __init__(self, layer_data: dict, parent=None):
        super().__init__(parent)
        self.layer_data = layer_data

    @staticmethod
    def is_null_key(key: Any) -> bool:
        return str(key).lower() == 'null' or str(key) == ''

    @staticmethod
    def build_null_filter(prop: str) -> str:
        return f'"{prop}" IS NULL OR "{prop}" = \'\''

    @staticmethod
    def create_symbol(style_dict: dict) -> QgsFillSymbol:
        color = QColor(style_dict.get('fill-color', FALLBACK_COLOR))
        outline_color = QColor(style_dict.get('fill-outline-color', '#000000'))
        outline_color.setAlphaF(float(style_dict.get('fill-outline-opacity', 1.0)))

        symbol = QgsFillSymbol.createSimple({
            'color': color.name(),
            'outline_color': outline_color.name(),
            'outline_width': str(style_dict.get('line-width', 0.2) * 0.75),
            'outline_style': 'solid'
        })
        symbol.setOpacity(float(style_dict.get('fill-opacity', style_dict.get('opacity', 1.0))))
        sl = symbol.symbolLayer(0)
        sl.setStrokeWidthUnit(QgsUnitTypes.RenderPoints)
        sl.setStrokeColor(outline_color)
        return symbol

    @staticmethod
    def create_labeling_style(labels_cfg: dict) -> QgsVectorTileBasicLabelingStyle:
        label_style = QgsVectorTileBasicLabelingStyle()
        label_style.setGeometryType(QgsWkbTypes.PolygonGeometry)

        settings = QgsPalLayerSettings()
        text_format = QgsTextFormat()
        text_format.setSize(labels_cfg.get('font-size', 12) * 0.7)
        text_format.setSizeUnit(QgsUnitTypes.RenderPoints)
        text_format.setColor(QColor(labels_cfg.get('font-color', '#000000')))

        if labels_cfg.get('font-weight') == 'bold':
            font = text_format.font()
            font.setBold(True)
            text_format.setFont(font)

        if labels_cfg.get('stroke-visible', False):
            buffer_settings = text_format.buffer()
            buffer_settings.setEnabled(True)
            buffer_settings.setColor(QColor(labels_cfg.get('stroke-color', '#FFFFFF')))
            buffer_settings.setSize(labels_cfg.get('stroke-width', 1.0) * 0.5)
            buffer_settings.setSizeUnit(QgsUnitTypes.RenderPoints)
            text_format.setBuffer(buffer_settings)

        settings.setFormat(text_format)
        settings.xOffset = labels_cfg.get('offset-x', 0) * 0.6
        settings.yOffset = labels_cfg.get('offset-y', 0) * 0.6
        settings.placement = QgsPalLayerSettings.Free

        attr_adv = labels_cfg.get('attributes_advanced', {}).get('text', '')
        if attr_adv:
            match = re.search(r'\{([^}]+)\}', attr_adv.strip())
            settings.fieldName = match.group(1) if match else attr_adv
        else:
            fields_list = labels_cfg.get('attributes', [])
            if fields_list:
                settings.fieldName = fields_list[0]

        maxzoom = labels_cfg.get('maxzoom')

        mvt_minzoom = 13
        label_style.setMinZoomLevel(mvt_minzoom)
        scale_min = RASTER_ZOOM_LEVEL.get(mvt_minzoom, 0)
        if scale_min > 0:
            settings.scaleVisibility = True
            settings.minimumScale = scale_min

        if maxzoom is not None:
            label_style.setMaxZoomLevel(maxzoom)
            scale_max = RASTER_ZOOM_LEVEL.get(maxzoom, 0)
            if scale_max > 0:
                settings.scaleVisibility = True
                settings.maximumScale = scale_max

        label_style.setLabelSettings(settings)
        return label_style

    def _build_tile_style(self,
                          layer_name: str,
                          filter_expr: str,
                          style_dict: dict,
                          minzoom: Optional[int]) -> QgsVectorTileBasicRendererStyle:

        tile_style = QgsVectorTileBasicRendererStyle()
        tile_style.setLayerName(layer_name)
        tile_style.setGeometryType(QgsWkbTypes.PolygonGeometry)
        tile_style.setFilterExpression(filter_expr)
        tile_style.setSymbol(self.create_symbol(style_dict))
        if minzoom is not None:
            tile_style.setMinZoomLevel(minzoom)
        return tile_style

    def loadLayer(self) -> Optional[QgsVectorTileLayer]:
        layer_name = self.layer_data.get('name', 'kontury_klasyfikacyjne')
        title = self.layer_data.get('title') or layer_name

        host = CONNECTION._getHost().rstrip('/')
        token = CONNECTION.token
        mvt_url = f"{host}/api/databox/mvt/{layer_name}/{{z}}/{{x}}/{{y}}?token={token}"
        mvt_url = mvt_url.replace('=', '%3D').replace('&', '%26')

        style_data = self.layer_data.get('style', {})
        zmax = min(style_data.get('maxzoom', 14), 14)
        uri = f"type=xyz&url={mvt_url}&zmax={zmax}&zmin=0"

        layer = QgsVectorTileLayer(uri, title)
        if not layer.isValid():
            self.message(self.tr("Nie udało się wczytać warstwy MVT: {}.").format(title), level=Qgis.Warning)
            return

        minzoom = style_data.get('minzoom')
        maxzoom = style_data.get('maxzoom')
        mvt_minzoom = max(0, minzoom - 1) if minzoom is not None else None

        if any(z is not None for z in (minzoom, maxzoom)):
            layer.setScaleBasedVisibility(True)
            if mvt_minzoom is not None:
                layer.setMinimumScale(RASTER_ZOOM_LEVEL.get(mvt_minzoom, 0))
            if maxzoom is not None:
                layer.setMaximumScale(RASTER_ZOOM_LEVEL.get(maxzoom, 0))

        styles = []
        label_styles = []
        uniques = style_data.get('uniques', {})
        fallback_style = {
            'fill-color': FALLBACK_COLOR,
            'fill-outline-color': '#000000',
            'fill-opacity': 0.7
        }

        if uniques and uniques.get('values'):
            prop = uniques.get('property', '')
            non_null_keys = []

            for key, value in uniques['values'].items():
                is_null = self.is_null_key(key)
                if is_null:
                    continue
                non_null_keys.append(key)
                filter_expr = f'"{prop}" = \'{key}\''

                styles.append(self._build_tile_style(layer_name, filter_expr, value, mvt_minzoom))

                if value.get('labels'):
                    label = self.create_labeling_style(value['labels'])
                    label.setLayerName(layer_name)
                    label.setFilterExpression(filter_expr)
                    label_styles.append(label)

            if non_null_keys:
                escaped_keys = ", ".join([f"'{k}'" for k in non_null_keys])
                fallback_filter = f'NOT ("{prop}" IN ({escaped_keys})) OR "{prop}" IS NULL OR "{prop}" = \'\''
            else:
                fallback_filter = f'"{prop}" IS NULL OR "{prop}" = \'\''

            styles.append(self._build_tile_style(layer_name, fallback_filter, fallback_style, mvt_minzoom))
        else:
            styles.append(self._build_tile_style(layer_name, '', style_data, mvt_minzoom))

            if style_data.get('labels'):
                label = self.create_labeling_style(style_data['labels'])
                label.setLayerName(layer_name)
                label_styles.append(label)

        renderer = QgsVectorTileBasicRenderer()
        renderer.setStyles(styles)
        layer.setRenderer(renderer)

        if label_styles:
            labeling = QgsVectorTileBasicLabeling()
            labeling.setStyles(label_styles)
            layer.setLabeling(labeling)
            layer.setLabelsEnabled(True)

        QgsProject.instance().addMapLayer(layer)
        self.message(self.tr("Pomyślnie wczytano warstwę wektorową MVT: {}").format(title), duration=3)
        return layer
