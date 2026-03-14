import os

from api.services import storage


class DummySettings:
    storage_backend = "local"
    local_upload_dir = "/tmp/citadel_test_uploads"
    s3_endpoint = "http://localhost:9000"
    s3_bucket = "citadel-docs"
    s3_access_key = "minioadmin"
    s3_secret_key = "minioadmin"
    s3_region = "us-east-1"
    s3_use_ssl = False


def test_save_file_local(monkeypatch, tmp_path):
    dummy = DummySettings()
    dummy.local_upload_dir = str(tmp_path)
    monkeypatch.setattr(storage, "get_settings", lambda: dummy)

    uri = storage.save_file(b"hello", "test.txt")
    assert uri.startswith("file://")
    path = uri.replace("file://", "")
    assert os.path.exists(path)
