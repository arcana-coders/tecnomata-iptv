import pytest
from tecnomata_iptv.accounts import AccountStore, StorageError
from tecnomata_iptv.xtream import Account


class Backend:
    def __init__(self):
        self.values = {}
        self.fail = False

    def get_password(self, service, identity):
        if self.fail:
            raise RuntimeError("private password in backend error")
        return self.values.get((service, identity))

    def set_password(self, service, identity, value):
        if self.fail:
            raise RuntimeError("private password in backend error")
        self.values[service, identity] = value

    def delete_password(self, service, identity):
        if self.fail:
            raise RuntimeError("private password in backend error")
        self.values.pop((service, identity), None)


def test_account_roundtrip_and_forget():
    backend = Backend()
    store = AccountStore(backend)
    account = Account("https://example.invalid", "u", "p")
    assert store.load() is None
    store.save(account)
    assert store.load() == account
    assert list(backend.values) == [("tecnomata-iptv", "default-account")]
    store.forget()
    assert store.load() is None


@pytest.mark.parametrize("method", ["load", "save", "forget"])
def test_keyring_errors_do_not_expose_backend_secrets(method):
    backend = Backend()
    backend.fail = True
    store = AccountStore(backend)
    with pytest.raises(StorageError) as error:
        getattr(store, method)(*([Account("https://example.invalid", "u", "p")] if method == "save" else []))
    assert "private" not in str(error.value)
    assert "password" not in str(error.value)


def test_corrupt_keyring_entry_is_not_restored():
    backend = Backend()
    backend.values["tecnomata-iptv", "default-account"] = '{"password": "private"}'
    with pytest.raises(StorageError):
        AccountStore(backend).load()
