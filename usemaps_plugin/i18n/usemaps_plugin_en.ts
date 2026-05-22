<?xml version="1.0" encoding="utf-8"?>
<!DOCTYPE TS>
<TS version="2.1" language="en_US" sourcelanguage="pl_PL">
<context>
    <name>BaseMapLayer</name>
    <message>
        <location filename="../service/layers/basemap_layer.py" line="131"/>
        <source>Błąd warstwy {}: błąd połączenia z serwerem.</source>
        <translation>Layer error {}: server connection error.</translation>
    </message>
    <message>
        <location filename="../service/layers/basemap_layer.py" line="134"/>
        <source>Błąd warstwy {}: błąd połączenia z serwerem (kod: {}). Upewnij się, że połączenie sieciowe i usługa działają poprawnie</source>
        <translation>Layer error {}: server connection error (code: {}). Make sure the network connection and service are working correctly</translation>
    </message>
    <message>
        <location filename="../service/layers/basemap_layer.py" line="137"/>
        <source>Błąd warstwy {}: nazwa {} nie występuje w Capabilities.</source>
        <translation>Layer error {}: name {} does not appear in Capabilities.</translation>
    </message>
</context>
<context>
    <name>Capabilities</name>
    <message>
        <location filename="../tools/capabilities.py" line="38"/>
        <source>Dokument XML pobrany z adresu {} zawiera potencjalnie niebezpieczne fragmenty i został zablokowany</source>
        <translation>The XML document downloaded from {} contains potentially dangerous content and has been blocked</translation>
    </message>
</context>
<context>
    <name>Connection</name>
    <message>
        <location filename="../tools/connection.py" line="42"/>
        <source>Błąd komunikacji z API: {}</source>
        <translation>API communication error: {}</translation>
    </message>
    <message>
        <location filename="../tools/connection.py" line="49"/>
        <source>Wystąpił nieoczekiwany błąd. Kod błędu: {}</source>
        <translation>An unexpected error occurred. Error code: {}</translation>
    </message>
    <message>
        <location filename="../tools/connection.py" line="68"/>
        <source>Błąd pobierania pliku. Kod: {}</source>
        <translation>Error downloading file. Code: {}</translation>
    </message>
    <message>
        <location filename="../tools/connection.py" line="108"/>
        <location filename="../tools/connection.py" line="256"/>
        <source>Błąd połączenia z serwerem. Sprawdź czy adres aplikacji jest prawidłowy lub skontaktuj się z administratorem</source>
        <translation>Server connection error. Check if the application address is correct or contact your administrator</translation>
    </message>
    <message>
        <location filename="../tools/connection.py" line="133"/>
        <source>Połączono</source>
        <translation>Connected</translation>
    </message>
    <message>
        <location filename="../tools/connection.py" line="167"/>
        <source>Rozłączono</source>
        <translation>Disconnected</translation>
    </message>
</context>
<context>
    <name>Dialog</name>
    <message>
        <location filename="../service/gui/login_settings.ui" line="14"/>
        <source>Ustawienia logowania</source>
        <translation>Login settings</translation>
    </message>
    <message>
        <location filename="../service/gui/login_settings.ui" line="54"/>
        <source>Hasło:</source>
        <translation>Password:</translation>
    </message>
    <message>
        <location filename="../service/gui/login_settings.ui" line="93"/>
        <source>Login:</source>
        <translation>Login:</translation>
    </message>
    <message>
        <location filename="../service/gui/login_settings.ui" line="100"/>
        <source>Adres:</source>
        <translation>Address:</translation>
    </message>
    <message>
        <location filename="../service/gui/two_fa.ui" line="14"/>
        <source>Dwuetapowa weryfikacja</source>
        <translation>Two-factor verification</translation>
    </message>
    <message>
        <location filename="../service/gui/two_fa.ui" line="23"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;Kod weryfikacyjny został wysłany na Twój adres e-mail. &lt;/p&gt;&lt;p&gt;W celu zalogowania się wpisz przesłany kod poniżej&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;A verification code has been sent to your email address.&lt;/p&gt;&lt;p&gt;Please enter the code below to log in.&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../service/gui/two_fa.ui" line="63"/>
        <source>Kod:</source>
        <translation>Code:</translation>
    </message>
    <message>
        <location filename="../service/gui/two_fa.ui" line="102"/>
        <source>Nie otrzymałeś maila?</source>
        <translation>Haven&apos;t received your email?</translation>
    </message>
    <message>
        <location filename="../service/gui/two_fa.ui" line="120"/>
        <source>Wyślij kod ponownie</source>
        <translation>Resend code</translation>
    </message>
    <message>
        <location filename="../service/gui/import_layer.ui" line="26"/>
        <source>Dodaj nową warstwę</source>
        <translation>Add new layer</translation>
    </message>
    <message>
        <location filename="../service/gui/import_layer.ui" line="34"/>
        <source>Wybierz warstwę:</source>
        <translation>Select layer:</translation>
    </message>
    <message>
        <location filename="../service/gui/import_layer.ui" line="73"/>
        <source>Dodaj</source>
        <translation>Add</translation>
    </message>
    <message>
        <location filename="../service/gui/import_layer.ui" line="92"/>
        <source>Anuluj</source>
        <translation>Cancel</translation>
    </message>
</context>
<context>
    <name>FeatureLayer</name>
    <message>
        <location filename="../service/layers/datasources.py" line="241"/>
        <source>Wczytywanie warstwy: {}...</source>
        <translation>Loading layer: {}...</translation>
    </message>
    <message>
        <source>Ładowanie obiektów</source>
        <translation type="vanished">Loading features</translation>
    </message>
    <message>
        <source>Pomyślnie wczytano dane warstwy: {}, czas: {}</source>
        <translation type="vanished">Layer data loaded successfully: {}, time: {}</translation>
    </message>
    <message>
        <location filename="../service/layers/datasources.py" line="188"/>
        <source>Wczytano warstwę: {}</source>
        <translation>Layer loaded: {}</translation>
    </message>
    <message>
        <location filename="../service/layers/datasources.py" line="626"/>
        <source>Pobrano dane warstwy: {}, czas: {:.5f}s</source>
        <translation>Layer data downloaded: {}, time: {:.5f}s</translation>
    </message>
    <message>
        <location filename="../service/layers/datasources.py" line="634"/>
        <source>Wczytywanie obiektów</source>
        <translation>Loading features</translation>
    </message>
    <message>
        <location filename="../service/layers/datasources.py" line="748"/>
        <source>Identyfikator</source>
        <translation>ID</translation>
    </message>
    <message>
        <location filename="../service/layers/datasources.py" line="985"/>
        <source>Pomyślnie zmodyfikowano dane warstwy: {}</source>
        <translation>Layer data modified successfully: {}</translation>
    </message>
    <message>
        <location filename="../service/layers/datasources.py" line="429"/>
        <location filename="../service/layers/datasources.py" line="484"/>
        <source>Pozostałe</source>
        <translation>Others</translation>
    </message>
</context>
<context>
    <name>ImportLayerDialog</name>
    <message>
        <location filename="../service/gui/import_layer.py" line="37"/>
        <source>Wysyłanie...</source>
        <translation>Uploading...</translation>
    </message>
    <message>
        <location filename="../service/gui/import_layer.py" line="68"/>
        <source>Sukces</source>
        <translation>Success</translation>
    </message>
    <message>
        <location filename="../service/gui/import_layer.py" line="68"/>
        <source>Warstwa została dodana do Usemaps.</source>
        <translation>The layer has been added to Usemaps.</translation>
    </message>
    <message>
        <location filename="../service/gui/import_layer.py" line="71"/>
        <source>Błąd</source>
        <translation>Error</translation>
    </message>
    <message>
        <location filename="../service/gui/import_layer.py" line="74"/>
        <source>Dodaj</source>
        <translation>Add</translation>
    </message>
</context>
<context>
    <name>LayersRegistry</name>
    <message>
        <location filename="../service/layers/layers_registry.py" line="29"/>
        <location filename="../service/layers/layers_registry.py" line="45"/>
        <source>Warstwy modułów dodatkowych</source>
        <translation>Layers of additional modules</translation>
    </message>
    <message>
        <location filename="../service/layers/layers_registry.py" line="49"/>
        <source>Pobieranie schematu warstw...</source>
        <translation>Downloading layers schema...</translation>
    </message>
</context>
<context>
    <name>MainDockWidget</name>
    <message>
        <location filename="../service/main_dockwidget.py" line="220"/>
        <source>Pobrano schemat warstw</source>
        <translation>Layers schema downloaded</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="345"/>
        <location filename="../service/main_dockwidget.py" line="580"/>
        <source>Nazwa</source>
        <translation>Name</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="581"/>
        <source>Status</source>
        <translation>Status</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="582"/>
        <source>Kierownik</source>
        <translation>Manager</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="669"/>
        <source>Projekt {} nie posiada powiązanych źródeł danych</source>
        <translation>Project {} has no associated data sources</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="673"/>
        <location filename="../service/main_dockwidget.py" line="688"/>
        <source>Projekt {} nie posiada warstw dostępnych dla Ciebie</source>
        <translation>Project {} has no layers available to you</translation>
    </message>
    <message>
        <source>Błąd ładowania warstwy {getattr(layer_class, &apos;name&apos;, &apos;?&apos;)}: {e}</source>
        <translation type="vanished">Error loading layer {getattr(layer_class, &apos;name&apos;, &apos;?&apos;)}: {e}</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="690"/>
        <source>Wczytano warstwy projektu: {}</source>
        <translation>Loaded layers for project: {}</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="558"/>
        <source>Brak skonfigurowanego źródła projektów.</source>
        <translation>No configured project data source.</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="604"/>
        <source>Brak danych</source>
        <translation>No data</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="346"/>
        <source>Właściciel</source>
        <translation>Owner</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="171"/>
        <source>Tylko administrator może dodać nową warstwę do organizacji</source>
        <translation>Only an administrator can add a new layer to the organization</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="347"/>
        <source>Data ostatniej edycji</source>
        <translation>Last edited</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="445"/>
        <source>Błąd pobierania danych mapy</source>
        <translation>Error fetching map data</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="452"/>
        <source>Mapa nie zawiera żadnych warstw.</source>
        <translation>The map contains no layers.</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="485"/>
        <source>Zaimportowano mapę: {}</source>
        <translation>Map imported: {}</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.py" line="49"/>
        <source>Narzędzie identyfikacji. Włącz, a następnie kliknij obiekt na mapie, aby sprawdzić jego atrybuty.</source>
        <translation>Identify tool. Enable it, then click a feature on the map to check its attributes.</translation>
    </message>
</context>
<context>
    <name>NetworkHandler</name>
    <message>
        <location filename="../tools/requests.py" line="34"/>
        <source>Przekroczono czas oczekiwania na odpowiedź serwera.</source>
        <translation>Server response timeout.</translation>
    </message>
</context>
<context>
    <name>ServiceProvider</name>
    <message>
        <location filename="../service/main.py" line="44"/>
        <source>Wyloguj</source>
        <translation>Logout</translation>
    </message>
    <message>
        <location filename="../service/main.py" line="58"/>
        <source>Zaloguj</source>
        <translation>Login</translation>
    </message>
</context>
<context>
    <name>TwoFADialog</name>
    <message>
        <location filename="../service/gui/two_fa.py" line="72"/>
        <source>Weryfikacja dwuetapowa</source>
        <translation>Two-factor verification</translation>
    </message>
    <message>
        <location filename="../service/gui/two_fa.py" line="73"/>
        <source>Wysłano kod weryfikacyjny ponownie.</source>
        <translation>Verification code resent.</translation>
    </message>
</context>
<context>
    <name>UsemapsDockWidget</name>
    <message>
        <location filename="../service/main_dockwidget.ui" line="14"/>
        <source>Usemaps - platforma do współpracy na mapach</source>
        <translation>Usemaps - platform for collaboration on maps</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="21"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-size:10pt;&quot;&gt;Narzędzie pozwalające na wczytanie danych z Usemaps do QGIS i ich edycję wraz ze współpracownikami.&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-size:10pt;&quot;&gt;A tool for loading data from Usemaps into QGIS and editing it collaboratively with your team.&lt;/span&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="31"/>
        <source>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-size:10pt;&quot;&gt;Dowiedz się więcej o &lt;/span&gt;&lt;a href=&quot;https://usemaps.com/&quot;&gt;&lt;span style=&quot; font-size:10pt; text-decoration: underline; color:#0000ff;&quot;&gt;Usemaps&lt;/span&gt;&lt;/a&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</source>
        <translation>&lt;html&gt;&lt;head/&gt;&lt;body&gt;&lt;p&gt;&lt;span style=&quot; font-size:10pt;&quot;&gt;Learn more about &lt;/span&gt;&lt;a href=&quot;https://usemaps.com/en/&quot;&gt;&lt;span style=&quot; font-size:10pt; text-decoration: underline; color:#0000ff;&quot;&gt;Usemaps&lt;/span&gt;&lt;/a&gt;&lt;/p&gt;&lt;/body&gt;&lt;/html&gt;</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="53"/>
        <source>Zaloguj</source>
        <translation>Login</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="60"/>
        <source>Ustawienia logowania</source>
        <translation>Login settings</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="100"/>
        <source>Dane</source>
        <translation>Data</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="106"/>
        <source>Szukaj/filtruj warstwy</source>
        <translation>Search/filter layers</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="187"/>
        <source>Identyfikacja</source>
        <translation>Identify</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="232"/>
        <source>Odśwież</source>
        <translation>Refresh</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="160"/>
        <source>Szukaj/filtruj projekty</source>
        <translation>Search/filter projects</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="154"/>
        <source>Projekty</source>
        <translation>Projects</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="121"/>
        <source>Mapy</source>
        <translation>Maps</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="127"/>
        <source>Szukaj/filtruj mapy</source>
        <translation>Search/filter maps</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="87"/>
        <source>Identyfikacja Usemaps</source>
        <translation>Usemaps Identify</translation>
    </message>
    <message>
        <location filename="../service/main_dockwidget.ui" line="225"/>
        <source>Prześlij do Usemaps</source>
        <translation>Upload to Usemaps</translation>
    </message>
</context>
<context>
    <name>UsemapsIdentifyTool</name>
    <message>
        <location filename="../tools/identify_tool.py" line="90"/>
        <source>Atrybuty</source>
        <translation>Attributes</translation>
    </message>
    <message>
        <source>Tylko administrator może dodać nową warstwę do organizacji</source>
        <translation type="vanished">Only an administrator can add a new layer to the organization</translation>
    </message>
</context>
<context>
    <name>UsemapsPlugin</name>
    <message>
        <source>&amp;Wtyczka Usemaps</source>
        <translation>&amp;Usemaps Plugin</translation>
    </message>
</context>
</TS>
