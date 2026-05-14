# coding: utf-8
import urllib

from qgis.PyQt.QtCore import QObject, QUrl, pyqtSignal, QSettings, QCoreApplication
from qgis.PyQt.QtNetwork import QNetworkRequest
from qgis.core import QgsNetworkAccessManager, Qgis
import json

from .logger import Logger
from ..service.gui.two_fa import TwoFADialog


class Connection(QObject, Logger):
    on_connect = pyqtSignal(bool)
    on_disconnect = pyqtSignal()
    on_error = pyqtSignal(dict)

    MANAGER = QgsNetworkAccessManager()
    MANAGER.setTransferTimeout(600000)

    def __init__(self, parent=None):
        super(Connection, self).__init__(parent)
        self._active_replies = set()

        self.token = None
        self.is_connected = False
        self.twoFaDialog = None
        self.current_user = None

    def _getHost(self):
        settings = QSettings()
        settings.beginGroup('gisbox/gisbox_connection')
        host = settings.value('host', '').strip()
        
        if host and not host.startswith(('http://', 'https://')):
            return f"https://{host}"
            
        return host

    def authenticate(self) -> bool:
        """ Logowanie za pomocą REST API """
        settings = QSettings()
        settings.beginGroup('gisbox/gisbox_connection')

        is_external = all(
            (self.get('/api/license_manager/modules/EXTERNAL_LOGIN', sync=True, silent=True) or {}).get('data', {}).get(k)
            for k in ('configured', 'enabled')
        )

        credentials = {
            'username_or_email': settings.value('user'),
            'password': settings.value('pass')
        }

        if is_external:
            endpoint = '/api/external_login'
            payload = {'data': {'credentials': credentials}}
        else:
            endpoint = '/api/login'
            payload = {'data': credentials}

        request = self._createRequest(endpoint, with_token=False)
        reply = self.MANAGER.blockingPost(request, json.dumps(payload).encode('utf-8'))
        response_raw = bytearray(reply.content())
        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        
        if not response_raw:
            self.message(
                self.tr('Błąd połączenia z serwerem. Sprawdź czy adres aplikacji jest prawidłowy lub skontaktuj się z administratorem'),
                level=Qgis.MessageLevel.Critical, duration=5)
            return False
        response = json.loads(response_raw)
        if status_code != 200 and status_code != 201:
            error_message = response.get('error_message')
            self.message(f'{error_message}', level=Qgis.MessageLevel.Critical, duration=5)
            return False

        if status_code == 201:
            if self.twoFaDialog is None:
                self.twoFaDialog = TwoFADialog()

            if self.twoFaDialog.exec() == 0:
                return False

            return self.verify_code(self.twoFaDialog.verification_code)

        self.token = response['token']
        return True

    def connect(self) -> bool:
        if not self.authenticate():
            self.on_disconnect.emit()
            return False

        self.log(self.tr("Połączono"))
        self.on_connect.emit(True)
        self.is_connected = True
        self.get_current_user()
        return True

    def get_current_user(self):
        if self.current_user:
            return

        response_data = self.get('/api/users/current_user', sync=True)
        if not response_data or 'data' not in response_data:
            return

        data = response_data['data']
        permissions = data.get('permissions', {})
        layers_dict = {l["layer_id"]: l for l in permissions.get('layers', [])}
        modules_dict = {m["module_name"]: m for m in permissions.get('modules', [])}

        data['permissions']['layers'] = layers_dict
        data['permissions']['modules'] = modules_dict

        self.current_user = data


    def disconnect(self):

        if self.token:
            request = self._createRequest('/api/logout')
            self.MANAGER.blockingGet(request)
        self.log(self.tr("Rozłączono"))
        self.on_disconnect.emit()
        self.is_connected = False
        self.token = None
        self.current_user = None
        return True

    def _createRequest(self,
                       endpoint: str,
                       content_type: str = 'application/json',
                       with_token: bool = True) -> QNetworkRequest:
        request = QNetworkRequest(QUrl(urllib.parse.urljoin(self._getHost(), endpoint)))
        request.setHeader(QNetworkRequest.KnownHeaders.ContentTypeHeader, content_type)
        request.setRawHeader(b'X-User-Agent', b'qgis_gs')
        if with_token and self.token:
            request.setRawHeader(b'X-Access-Token', bytes(self.token.encode()))

        return request

    def _process_reply(self, reply, is_sync: bool, binary: bool, callback: any = None, silent: bool = False):
        if is_sync:
            content_bytes = bytearray(reply.content())
        else:
            content_bytes = bytearray(reply.readAll())

        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        
        if not is_sync:
            self._active_replies.discard(reply)
            reply.deleteLater()

        if status_code not in (200, 201, 204):
            try:
                response_data = json.loads(content_bytes)
                if status_code == 500:
                    error_message = QCoreApplication.translate("Connection", "Wystąpił nieoczekiwany błąd. Kod błędu: {}").format(response_data.get('error_code', 'Brak'))
                else:
                    error_message = response_data.get('error_message', 'Nieznany błąd')
            except Exception:
                error_message = QCoreApplication.translate("Connection", "Błąd HTTP: {}").format(status_code)

            if not silent:
                self.message(error_message, level=Qgis.MessageLevel.Critical, duration=5)
            
            if is_sync:
                return None
            return

        if binary:
            result = bytes(content_bytes)
        else:
            try:
                result = json.loads(content_bytes)
            except (json.JSONDecodeError, KeyError, ValueError) as e:
                self.log(QCoreApplication.translate("Connection", "Błąd komunikacji z API: {}").format(e))
                result = None

        if callback:
            callback(result)

        if is_sync:
            return result

    def _send_request(self, method: str, endpoint: str, data: bytes = b'', sync: bool = False, binary: bool = False, callback: any = None, silent: bool = False):
        request = self._createRequest(endpoint)
        is_get = method.upper() == 'GET'

        if sync:
            reply = self.MANAGER.blockingGet(request) if is_get else self.MANAGER.blockingPost(request, data)
            return self._process_reply(reply, is_sync=True, binary=binary, callback=callback, silent=silent)

        reply = self.MANAGER.get(request) if is_get else self.MANAGER.post(request, data)
        self._active_replies.add(reply)
        reply.finished.connect(lambda: self._process_reply(reply, is_sync=False, binary=binary, callback=callback, silent=silent))
        return reply

    def get(self, endpoint: str, sync: bool = False, callback: any = None, binary: bool = False, silent: bool = False):
        return self._send_request(method='GET', endpoint=endpoint, sync=sync, binary=binary, callback=callback, silent=silent)

    def post(self, endpoint: str, payload: dict, callback: any = None, sync: bool = False, binary: bool = False, silent: bool = False):
        data = json.dumps(payload).encode()
        return self._send_request(method='POST', endpoint=endpoint, data=data, sync=sync, binary=binary, callback=callback, silent=silent)

    def verify_code(self, code: int):
        settings = QSettings()
        settings.beginGroup('gisbox/gisbox_connection')
        payload = {
            'data': {
                'username_or_email': settings.value('user'),
                'password': settings.value('pass'),
                'verification_code': code
            }
        }
        request = self._createRequest('/api/login', with_token=False)
        reply = self.MANAGER.blockingPost(request, json.dumps(payload).encode('utf-8'))
        response_raw = bytearray(reply.content())
        status_code = reply.attribute(QNetworkRequest.Attribute.HttpStatusCodeAttribute)
        
        if not response_raw:
            self.message(
                self.tr('Błąd połączenia z serwerem. Sprawdź czy adres aplikacji jest prawidłowy lub skontaktuj się z administratorem'),
                level=Qgis.MessageLevel.Critical, duration=5)
            return False
        response = json.loads(response_raw)
        if status_code != 200:
            error_message = response.get('error_message')
            self.message(f'{error_message}', level=Qgis.MessageLevel.Critical, duration=5)
            return False
            
        self.token = response['token']
        return True


CONNECTION = Connection()