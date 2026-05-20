SOURCES = plugin.py \
          service/main.py \
          service/main_dockwidget.py \
          service/gui/two_fa.py \
          service/gui/import_layer.py \
          service/layers/basemap_layer.py \
          service/layers/datasources.py \
          service/layers/layers_registry.py \
          tools/connection.py \
          tools/requests.py \
          tools/capabilities.py \
          tools/identify_tool.py

FORMS = service/main_dockwidget.ui \
        service/gui/login_settings.ui \
        service/gui/two_fa.ui \
        service/gui/import_layer.ui

TRANSLATIONS = i18n/usemaps_plugin_en.ts \
               i18n/usemaps_plugin_pl.ts
