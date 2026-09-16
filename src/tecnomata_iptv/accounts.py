"""Una cuenta propia en Secret Service de Linux. Nunca escribir secretos a disco."""
import json
from .xtream import Account


class StorageError(Exception):
    pass


class AccountStore:
    def __init__(self, backend=None, service="tecnomata-iptv"):
        self._backend = backend
        self.service = service
        self.identity = "default-account"

    @property
    def backend(self):
        if self._backend is None:
            from keyring.backends.SecretService import Keyring
            # Explicit secure Linux backend. No plaintext backend fallback.
            self._backend = Keyring()
        return self._backend

    def load(self):
        try:
            payload = self.backend.get_password(self.service, self.identity)
            if payload is None:
                return None
            data = json.loads(payload)
            if not isinstance(data, dict) or any(not isinstance(data.get(key), str)
                                                for key in ("server", "username", "password")):
                raise ValueError()
            return Account(data["server"], data["username"], data["password"])
        except Exception:
            raise StorageError("No se pudo leer la cuenta del almacén seguro de Linux. Puedes conectar manualmente.") from None

    def save(self, account):
        try:
            payload = json.dumps({"server": account.server, "username": account.username,
                                  "password": account.password})
            self.backend.set_password(self.service, self.identity, payload)
        except Exception:
            raise StorageError("La conexión funciona, pero no se pudo guardar la cuenta en el almacén seguro de Linux.") from None

    def forget(self):
        try:
            from keyring.errors import PasswordDeleteError
            try:
                self.backend.delete_password(self.service, self.identity)
            except PasswordDeleteError:
                pass  # Nothing saved already.
        except Exception:
            raise StorageError("No se pudo borrar la cuenta del almacén seguro de Linux.") from None
