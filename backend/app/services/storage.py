import re
import uuid
from pathlib import Path
from typing import Protocol

from app.core.config import settings


class StorageService(Protocol):
    def upload(self, filename: str, content: bytes) -> str: ...
    def download(self, storage_key: str) -> bytes: ...
    def delete(self, storage_key: str) -> None: ...


class LocalStorageService:
    def __init__(self, root: Path | None = None) -> None:
        configured = root or settings.storage_path
        if not configured.is_absolute():
            configured = Path(__file__).resolve().parents[3] / configured
        self.root = configured.resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def _path(self, storage_key: str) -> Path:
        candidate = (self.root / storage_key).resolve()
        if candidate.parent != self.root:
            raise ValueError("Invalid storage key")
        return candidate

    def upload(self, filename: str, content: bytes) -> str:
        extension = Path(filename).suffix.lower()
        if extension not in {".pdf", ".png", ".jpg", ".jpeg"}:
            raise ValueError("Unsupported document extension")
        key = f"{uuid.uuid4().hex}{extension}"
        self._path(key).write_bytes(content)
        return key

    def download(self, storage_key: str) -> bytes:
        return self._path(storage_key).read_bytes()

    def delete(self, storage_key: str) -> None:
        self._path(storage_key).unlink(missing_ok=True)


class S3StorageService:
    def __init__(self) -> None:
        if (
            not settings.s3_bucket
            or not settings.s3_access_key_id
            or not settings.s3_secret_access_key
        ):
            raise RuntimeError("S3 object storage is not configured")
        import boto3

        self.bucket = settings.s3_bucket
        self.client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=settings.s3_endpoint_url,
            aws_access_key_id=settings.s3_access_key_id,
            aws_secret_access_key=settings.s3_secret_access_key.get_secret_value(),
        )

    @staticmethod
    def _key(filename: str) -> str:
        extension = Path(filename).suffix.lower()
        if extension not in {".pdf", ".png", ".jpg", ".jpeg"}:
            raise ValueError("Unsupported document extension")
        return f"{uuid.uuid4().hex}{extension}"

    @staticmethod
    def _validated_key(storage_key: str) -> str:
        if not re.fullmatch(r"[a-f0-9]{32}\.(pdf|png|jpg|jpeg)", storage_key):
            raise ValueError("Invalid storage key")
        return storage_key

    def upload(self, filename: str, content: bytes) -> str:
        key = self._key(filename)
        self.client.put_object(Bucket=self.bucket, Key=key, Body=content)
        return key

    def download(self, storage_key: str) -> bytes:
        response = self.client.get_object(Bucket=self.bucket, Key=self._validated_key(storage_key))
        return response["Body"].read()

    def delete(self, storage_key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=self._validated_key(storage_key))


def get_storage_service() -> StorageService:
    if settings.storage_backend == "s3":
        return S3StorageService()
    return LocalStorageService()
