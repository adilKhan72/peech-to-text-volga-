from abc import ABC, abstractmethod


class AudioStorage(ABC):
    """Audio lives here, referenced by storage_key everywhere else in the app.

    Local filesystem today, S3 (or similar) later — swapping the implementation is a
    one-file change (see local_fs.py) because nothing else talks to the filesystem
    directly.
    """

    @abstractmethod
    def save(self, job_id: str, filename: str, content: bytes) -> str:
        """Persist audio bytes, return a storage_key that get_path can resolve later."""

    @abstractmethod
    def get_path(self, storage_key: str) -> str:
        """Resolve a storage_key back to a local path the pipeline can read from."""

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Remove stored audio — e.g. after a successful transcription, per retention policy."""
