import logging
import uuid
from abc import ABC, abstractmethod
from functools import lru_cache

from app.vision.schemas import RecognitionResult, RecognitionState

logger = logging.getLogger(__name__)


class VisionService(ABC):
    @abstractmethod
    def embedding_from_image(self, image_bytes: bytes) -> tuple[list[float] | None, int]:
        """Return an embedding and detected face count; no attendance writes happen here."""


class InsightFaceVisionService(VisionService):
    def __init__(self) -> None:
        try:
            import cv2
            import numpy as np
            from insightface.app import FaceAnalysis
        except ImportError as error:
            raise RuntimeError(
                "Install the optional backend vision dependencies to enable recognition"
            ) from error
        self.cv2 = cv2
        self.np = np
        self.analysis = FaceAnalysis(name="buffalo_l", providers=["CPUExecutionProvider"])
        self.analysis.prepare(ctx_id=-1, det_size=(640, 640))

    def embedding_from_image(self, image_bytes: bytes) -> tuple[list[float] | None, int]:
        raw = self.np.frombuffer(image_bytes, dtype=self.np.uint8)
        image = self.cv2.imdecode(raw, self.cv2.IMREAD_COLOR)
        if image is None:
            return None, 0
        faces = self.analysis.get(image)
        if len(faces) != 1:
            return None, len(faces)
        vector = self.np.asarray(faces[0].normed_embedding, dtype=self.np.float32)
        return vector.tolist(), 1


@lru_cache(maxsize=1)
def get_vision_engine() -> InsightFaceVisionService:
    return InsightFaceVisionService()


def recognize_image(image_bytes: bytes, db, minimum_confidence: float = 0.45) -> RecognitionResult:
    try:
        engine = get_vision_engine()
        embedding, face_count = engine.embedding_from_image(image_bytes)
    except RuntimeError as error:
        return RecognitionResult(state=RecognitionState.ERROR, message=str(error))
    except Exception:
        logger.exception("Face recognition failed")
        return RecognitionResult(
            state=RecognitionState.ERROR, message="Recognition processing failed"
        )

    if face_count > 1:
        return RecognitionResult(state=RecognitionState.MULTIPLE_FACES, face_count=face_count)
    if not embedding:
        return RecognitionResult(state=RecognitionState.UNKNOWN, face_count=face_count)

    from sqlalchemy import select

    from app.models.attendance import FaceEmbedding, FaceProfile
    from app.models.user import User

    profiles = db.execute(
        select(FaceProfile.student_id, FaceEmbedding.embedding)
        .join(FaceEmbedding, FaceEmbedding.profile_id == FaceProfile.id)
        .join(User, User.id == FaceProfile.student_id)
        .where(FaceProfile.revoked_at.is_(None), User.is_active.is_(True))
    ).all()
    best_id: uuid.UUID | None = None
    best_score = -1.0
    query = engine.np.asarray(embedding, dtype=engine.np.float32)
    for student_id, stored in profiles:
        candidate = engine.np.asarray(stored, dtype=engine.np.float32)
        score = float(
            engine.np.dot(query, candidate)
            / (engine.np.linalg.norm(query) * engine.np.linalg.norm(candidate))
        )
        if score > best_score:
            best_id, best_score = student_id, score
    if best_id is None:
        return RecognitionResult(state=RecognitionState.UNKNOWN, face_count=1)
    if best_score < minimum_confidence:
        return RecognitionResult(
            state=RecognitionState.LOW_CONFIDENCE, confidence=best_score, face_count=1
        )
    return RecognitionResult(
        state=RecognitionState.RECOGNIZED,
        student_id=best_id,
        confidence=best_score,
        face_count=1,
    )
