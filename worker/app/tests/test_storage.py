import os

from app.services import storage


def test_resolve_local_path(tmp_path):
    file_path = tmp_path / "file.txt"
    file_path.write_text("hello")
    uri = f"file://{file_path}"
    resolved = storage.resolve_to_local_path(uri)
    assert os.path.exists(resolved)
