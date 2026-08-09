import os

from app.config import settings
from app.storage.base import AudioStorage


class LocalFilesystemStorage(AudioStorage):
    """Stands in for object storage (S3, etc.) for local dev/take-home purposes.

    A real deployment would swap this for an S3-backed implementation without
    touching any caller — they only ever see storage_key strings, never paths.
    """

    def __init__(self, base_dir: str | None = None):
        self.base_dir = base_dir or settings.storage_dir
        os.makedirs(self.base_dir, exist_ok=True)

    def save(self, job_id: str, filename: str, content: bytes) -> str:
        job_dir = os.path.join(self.base_dir, job_id)
        os.makedirs(job_dir, exist_ok=True)
        ext = os.path.splitext(filename)[1] or ".bin"
        storage_key = os.path.join(job_id, f"original{ext}")
        with open(os.path.join(self.base_dir, storage_key), "wb") as f:
            f.write(content)
        return storage_key

    def get_path(self, storage_key: str) -> str:
        return os.path.join(self.base_dir, storage_key)

    def delete(self, storage_key: str) -> None:
        path = self.get_path(storage_key)
        if os.path.exists(path):
            os.remove(path)
        job_dir = os.path.dirname(path)
        if os.path.isdir(job_dir) and not os.listdir(job_dir):
            os.rmdir(job_dir)


_storage_instance: AudioStorage | None = None


def get_storage() -> AudioStorage:
    global _storage_instance
    if _storage_instance is None:
        _storage_instance = LocalFilesystemStorage()
    return _storage_instance
