from uuid import uuid4

from app.vision.schemas import RecognitionState
from app.vision.service import recognize_image


class FakeNumpy:
    float32 = "test-float32"

    @staticmethod
    def asarray(values, dtype=None):
        return [float(value) for value in values]

    @staticmethod
    def dot(left, right):
        return sum(a * b for a, b in zip(left, right, strict=True))

    class linalg:
        @staticmethod
        def norm(values):
            return sum(value * value for value in values) ** 0.5


class FakeVisionAdapter:
    """Synthetic deterministic test adapter; it is never used by production routes."""

    np = FakeNumpy

    def __init__(self, embedding, face_count: int = 1) -> None:
        self.embedding = embedding
        self.face_count = face_count

    def embedding_from_image(self, _image: bytes):
        return self.embedding, self.face_count


class FakeResult:
    def __init__(self, rows) -> None:
        self.rows = rows

    def all(self):
        return self.rows


class FakeDatabase:
    def __init__(self, rows=()) -> None:
        self.rows = rows

    def execute(self, _query):
        return FakeResult(self.rows)


def test_fake_adapter_states_are_deterministic_and_never_claim_real_inference(monkeypatch) -> None:
    monkeypatch.setattr(
        "app.vision.service.get_vision_engine", lambda: FakeVisionAdapter(None, face_count=0)
    )
    assert recognize_image(b"synthetic", FakeDatabase()).state == RecognitionState.UNKNOWN

    monkeypatch.setattr(
        "app.vision.service.get_vision_engine", lambda: FakeVisionAdapter(None, face_count=2)
    )
    assert recognize_image(b"synthetic", FakeDatabase()).state == RecognitionState.MULTIPLE_FACES

    monkeypatch.setattr(
        "app.vision.service.get_vision_engine",
        lambda: (_ for _ in ()).throw(RuntimeError("optional inference runtime unavailable")),
    )
    unavailable = recognize_image(b"synthetic", FakeDatabase())
    assert unavailable.state == RecognitionState.ERROR
    assert "unavailable" in unavailable.message


def test_fake_embeddings_cover_recognized_and_low_confidence_results(monkeypatch) -> None:
    student_id = uuid4()
    monkeypatch.setattr("app.vision.service.get_vision_engine", lambda: FakeVisionAdapter([1, 0]))
    recognized = recognize_image(b"synthetic", FakeDatabase([(student_id, [1, 0])]))
    assert recognized.state == RecognitionState.RECOGNIZED
    assert recognized.student_id == student_id
    assert recognized.confidence == 1.0

    monkeypatch.setattr("app.vision.service.get_vision_engine", lambda: FakeVisionAdapter([1, 0]))
    low_confidence = recognize_image(b"synthetic", FakeDatabase([(student_id, [0, 1])]))
    assert low_confidence.state == RecognitionState.LOW_CONFIDENCE
    assert low_confidence.confidence == 0.0
