from google.oauth2.credentials import Credentials

import gdrive_sync


class MemoryGoogleDriveTokenStorage:
    def __init__(self, token_json=None):
        self.token_json = token_json
        self.deleted = False

    def get_token_json(self):
        return self.token_json

    def save_token_json(self, token_json):
        self.token_json = token_json

    def delete_token(self):
        self.deleted = True
        self.token_json = None


def make_token_json(scopes=None):
    scopes = scopes or gdrive_sync.SCOPES
    creds = Credentials(
        token="token",
        refresh_token="refresh",
        token_uri="https://oauth2.googleapis.com/token",
        client_id="client-id",
        client_secret="client-secret",
        scopes=scopes,
    )
    return creds.to_json()


def test_google_drive_token_loads_from_keyring_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(gdrive_sync.engine, "get_app_data_dir", lambda: tmp_path)
    storage = MemoryGoogleDriveTokenStorage(make_token_json())
    manager = gdrive_sync.DriveSyncManager(token_storage=storage)

    creds = manager._load_credentials()

    assert creds is not None
    assert creds.has_scopes(gdrive_sync.SCOPES)


def test_google_drive_legacy_token_migrates_to_keyring_storage(tmp_path, monkeypatch):
    monkeypatch.setattr(gdrive_sync.engine, "get_app_data_dir", lambda: tmp_path)
    legacy_token = tmp_path / "gdrive_token.json"
    legacy_token.write_text(make_token_json(), encoding="utf-8")
    storage = MemoryGoogleDriveTokenStorage()
    manager = gdrive_sync.DriveSyncManager(token_storage=storage)

    creds = manager._load_credentials()

    assert creds is not None
    assert storage.token_json is not None
    assert not legacy_token.exists()


def test_google_drive_legacy_token_is_removed_when_keyring_token_exists(tmp_path, monkeypatch):
    monkeypatch.setattr(gdrive_sync.engine, "get_app_data_dir", lambda: tmp_path)
    legacy_token = tmp_path / "gdrive_token.json"
    legacy_token.write_text(make_token_json(), encoding="utf-8")
    storage = MemoryGoogleDriveTokenStorage(make_token_json())
    manager = gdrive_sync.DriveSyncManager(token_storage=storage)

    creds = manager._load_credentials()

    assert creds is not None
    assert not legacy_token.exists()
