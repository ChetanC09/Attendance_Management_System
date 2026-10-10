from io import BytesIO
from types import SimpleNamespace

import pytest
from pydantic import SecretStr

from app.services import storage as storage_module
from app.services.storage import S3StorageService, StorageUnavailable


class FakeStorageClient:
    def __init__(self) -> None:
        self.objects: dict[str, bytes] = {}
        self.failure: Exception | None = None

    def put_object(self, *, Bucket: str, Key: str, Body: bytes) -> None:
        if self.failure:
            raise self.failure
        self.objects[Key] = Body

    def get_object(self, *, Bucket: str, Key: str) -> dict:
        if self.failure:
            raise self.failure
        if Key not in self.objects:
            missing = RuntimeError("missing")
            missing.response = {"Error": {"Code": "NoSuchKey"}}
            raise missing
        return {"Body": BytesIO(self.objects[Key])}

    def delete_object(self, *, Bucket: str, Key: str) -> None:
        if self.failure:
            raise self.failure
        self.objects.pop(Key, None)


def make_storage() -> tuple[S3StorageService, FakeStorageClient]:
    storage = S3StorageService.__new__(S3StorageService)
    storage.bucket = "private-test-bucket"
    client = FakeStorageClient()
    storage.client = client
    return storage, client


def test_s3_storage_upload_download_delete_and_reject_unsafe_keys() -> None:
    storage, client = make_storage()
    key = storage.upload("evidence.pdf", b"%PDF-test")
    assert key.endswith(".pdf")
    assert storage.download(key) == b"%PDF-test"
    storage.delete(key)
    assert key not in client.objects

    with pytest.raises(ValueError, match="Invalid storage key"):
        storage.download("../evidence.pdf")


def test_s3_storage_distinguishes_missing_objects_from_provider_failures() -> None:
    storage, client = make_storage()
    with pytest.raises(FileNotFoundError):
        storage.download("a" * 32 + ".pdf")

    client.failure = RuntimeError("provider detail should not escape")
    with pytest.raises(StorageUnavailable, match="Object storage upload failed") as error:
        storage.upload("evidence.pdf", b"%PDF-test")
    assert "provider detail" not in str(error.value)


@pytest.mark.parametrize(
    ("configured_endpoint", "expected_endpoint"),
    [("", None), ("  \t ", None), ("https://objects.example.test", "https://objects.example.test")],
)
def test_s3_storage_normalizes_optional_endpoint_without_network(
    monkeypatch: pytest.MonkeyPatch,
    configured_endpoint: str,
    expected_endpoint: str | None,
) -> None:
    captured: dict[str, object] = {}

    def fake_boto3_client(service_name: str, **kwargs: object) -> object:
        captured["service_name"] = service_name
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        storage_module,
        "settings",
        SimpleNamespace(
            s3_bucket="private-test-bucket",
            s3_access_key_id="test-access-key",
            s3_secret_access_key=SecretStr("test-secret-key"),
            s3_region="us-east-1",
            s3_endpoint_url=configured_endpoint,
        ),
    )
    import boto3

    monkeypatch.setattr(boto3, "client", fake_boto3_client)

    S3StorageService()

    assert captured["service_name"] == "s3"
    assert captured["endpoint_url"] == expected_endpoint
