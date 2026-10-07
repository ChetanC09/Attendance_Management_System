import enum
import uuid

from pydantic import BaseModel


class RecognitionState(str, enum.Enum):
    RECOGNIZED = "recognized"
    UNKNOWN = "unknown"
    MULTIPLE_FACES = "multiple_faces"
    LOW_CONFIDENCE = "low_confidence"
    ERROR = "error"


class RecognitionResult(BaseModel):
    state: RecognitionState
    student_id: uuid.UUID | None = None
    confidence: float | None = None
    face_count: int = 0
    message: str | None = None


class AttendanceRecognitionResponse(BaseModel):
    state: RecognitionState
    attendance_state: str | None = None
    student_id: uuid.UUID | None = None
    confidence: float | None = None
    message: str | None = None
