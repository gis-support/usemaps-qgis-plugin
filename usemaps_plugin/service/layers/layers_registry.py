import time
from typing import List, Union

from qgis.PyQt.QtCore import pyqtSignal, QObject
from qgis.core import QgsProject
from qgis.utils import iface

from . import RELATION_VALUES_MAPPING_REGISTRY

from .basemap_layer import BaseMapLayer
from .datasources import FeatureLayer

from ...tools.logger import Logger
from ...tools.connection import CONNECTION
from ...tools.project_variables import get_layer_mapping

class LayersRegistry(QObject, Logger):
    """ Klasa służy do zarządzania warstwami systemowymi Usemaps """

    on_schema = pyqtSignal(list)
    on_layers = pyqtSignal(dict)
    data_loaded = pyqtSignal()
    on_groups = pyqtSignal(dict)

    def __init__(self):
        super().__init__()
        # Dane inicjalne
        self.groups = [{'id': -99, 'schema_scope': 'module',
                        'name': self.tr('Warstwy modułów dodatkowych'),
                        'subgroups': []}]
        self.layers = {}
        self.baselayers = {}

        # Sygnały
        # Po połączeniu pobieramy dane
        CONNECTION.on_connect.connect(self.loadData)
        self.on_layers.connect(self.onLayers)

    def loadData(self, connected: bool):
        """ Załadowanie wszystkich danych """
        if not connected:
            return
        # Wyczyszczenie wcześniejszych danych
        self.groups = [{'id': -99, 'schema_scope': 'module',
                        'name': self.tr('Warstwy modułów dodatkowych'),
                        'subgroups': []}]
        self.layers = {}
        self.baselayers = {}
        self.message(self.tr('Pobieranie schematu warstw...'), duration=10)
        CONNECTION.get(
            '/api/dataio/data_sources/relation_values_mapping/all', callback=self._set_relation_values_mapping)
        CONNECTION.get(
            f'/api/v2/layers-schema?full_data=true', callback=self.on_layers.emit)

    def onLayers(self, data: dict):
        """ Zapamiętanie pobranych warstw i pobranie warstw podkładowych """
        groups = data['data']
        self.groups.extend(groups)

        for group in groups:
            layers = group['layers']
            self.groups.extend(group)

            for layer in layers:
                if layer['layer_type'] == 'service_layer':
                    if not layer.get('service_layers_names'):
                        continue
                    current_layer = BaseMapLayer(layer)
                else:
                    current_layer = FeatureLayer(layer)
                self.layers[current_layer.id] = current_layer

        self.on_schema.emit(self.groups)

    def _set_relation_values_mapping(self, data: dict):
        RELATION_VALUES_MAPPING_REGISTRY.update(data['data'])

    def _put_layer_in_group(self, layer):
        layer_group_id = layer['group_id']
        if layer_group_id is None and layer['layer_scope'] == 'module':
            layer_group_id = -99

        group = self.getGroupById(layer_group_id)

        if group:
            if group.get('layers'):
                # Sprawdzamy czy warstwa nie jest już w grupie
                if layer['id'] in group['layers']:
                    return
                group['layers'].append(layer['id'])
            else:
                group['layers'] = [layer['id']]

    def getGroupById(self, group_id, groups=None):
        if groups is None:
            groups = self.groups
        for group in groups:
            if group['id'] == group_id:
                return group

    def isSystemLayer(self, layer=None):
        """ Sprawdza czy dana warstwa jest warstwą systemową """
        if layer is None:
            # Jeśli nie podano warstwy to sprawdzamy warstwę aktywną
            layer = iface.activeLayer()
        if layer is None:
            # Brak warstw
            return False

        try:
            if layer.customProperty('gisbox/is_gisbox_layer'):
                return bool(layer.customProperty('gisbox/is_gisbox_layer'))
            return get_layer_mapping(layer.id()) != -1
        except RuntimeError:
            return False

    def getLayerClass(self, layer=None):
        """ Zwraca klasę danej warstwy """
        if layer is None:
            # Jeśli nie podano warstwy to sprawdzamy warstwę aktywną
            layer = iface.activeLayer()
        if not self.isSystemLayer(layer):
            # To nie jest warstwa systemowa
            return
        layer_gisbox_id = get_layer_mapping(layer.id())
        return layers_registry.layers.get(layer_gisbox_id)

    def loadGroup(self, group_data: List[Union[str, int]]):

        group_name = group_data[0]
        group_id = group_data[1]
        group = self.getGroupById(group_id)

        root = QgsProject.instance().layerTreeRoot()
        qgis_group = root.addGroup(group_name)
        for layer in group['layers']:
            layer_id = layer.get("id")
            layer_class = self.layers.get(layer_id)
            if layer_class:
                layer_class.loadLayer(group=qgis_group)
        iface.mapCanvas().refresh()


# Stworzenie instancji klasy
layers_registry = LayersRegistry()
