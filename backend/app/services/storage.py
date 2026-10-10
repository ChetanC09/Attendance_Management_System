import re
import uuid
from pathlib import Path
from typing import Protocol

import boto3

from app.core.config import settings


class StorageService(Protocol):
    def upload(self, filename: str, content: bytes) -> str: ...
    def download(self, storage_key: str) -> bytes: ...
    def delete(self, storage_key: str) -> None: ...


class StorageUnavailable(RuntimeError):
    """Provider failure without exposing credentials or raw SDK error details."""


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
        self.bucket = settings.s3_bucket
        endpoint_url = settings.s3_endpoint_url
        if endpoint_url is not None:
            endpoint_url = endpoint_url.strip() or None
        self.client = boto3.client(
            "s3",
            region_name=settings.s3_region,
            endpoint_url=endpoint_url,
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
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=content)
        except Exception as error:
            raise StorageUnavailable("Object storage upload failed") from error
        return key

    def download(self, storage_key: str) -> bytes:
        key = self._validated_key(storage_key)
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=key)
            return response["Body"].read()
        except Exception as error:
            provider_code = getattr(error, "response", {}).get("Error", {}).get("Code")
            if provider_code in {"NoSuchKey", "NotFound", "404"}:
                raise FileNotFoundError("Document content is unavailable") from None
            raise StorageUnavailable("Object storage download failed") from error

    def delete(self, storage_key: str) -> None:
        key = self._validated_key(storage_key)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception as error:
            raise StorageUnavailable("Object storage deletion failed") from error


def get_storage_service() -> StorageService:
    if settings.storage_backend == "s3":
        return S3StorageService()
    return LocalStorageService()
