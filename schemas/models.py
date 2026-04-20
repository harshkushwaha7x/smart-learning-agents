"""Pydantic schemas for strict validation of all pipeline data structures."""

from typing import List, Optional, Dict
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, field_validator


class ContentStatus(str, Enum):
    APPROVED = "approved"
    REJECTED = "rejected"
    PENDING = "pending"


class AttemptStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    PENDING = "pending"


class Severity(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Difficulty(str, Enum):
    EASY = "Easy"
    MEDIUM = "Medium"
    HARD = "Hard"


class BloomsLevel(str, Enum):
    REMEMBERING = "Remembering"
    UNDERSTANDING = "Understanding"
    APPLYING = "Applying"
    ANALYZING = "Analyzing"
    EVALUATING = "Evaluating"
    CREATING = "Creating"


REQUIRED_SCORE_KEYS = {"age_appropriateness", "correctness", "clarity", "coverage"}


class MCQ(BaseModel):
    question: str = Field(..., min_length=10)
    options: List[str] = Field(..., min_length=4, max_length=4)
    correct_index: int = Field(..., ge=0, le=3)


class Explanation(BaseModel):
    text: str = Field(..., min_length=50)
    grade: int = Field(..., ge=1, le=12)


class TeacherNotes(BaseModel):
    learning_objective: str = Field(...)
    common_misconceptions: List[str] = Field(default_factory=list)


class GeneratedContent(BaseModel):
    explanation: Explanation
    mcqs: List[MCQ] = Field(..., min_length=4, max_length=4)
    teacher_notes: TeacherNotes


class ReviewFeedback(BaseModel):
    field: str = Field(..., description="Schema field path, e.g. 'explanation.text'")
    issue: str
    severity: Severity = Severity.MEDIUM


class ReviewResult(BaseModel):
    scores: Dict[str, int]
    pass_overall: bool
    average_score: float = Field(..., ge=1, le=5)
    feedback: List[ReviewFeedback] = Field(default_factory=list)

    @field_validator("scores")
    @classmethod
    def validate_score_keys(cls, v: Dict[str, int]) -> Dict[str, int]:
        missing = REQUIRED_SCORE_KEYS - set(v.keys())
        if missing:
            raise ValueError(f"Missing required score keys: {missing}")
        for key, score in v.items():
            if not (1 <= score <= 5):
                raise ValueError(f"Score for '{key}' must be 1-5, got {score}")
        return v


class Tags(BaseModel):
    subject: str
    topic: str
    grade: int = Field(..., ge=1, le=12)
    difficulty: Difficulty
    content_type: List[str] = Field(..., min_length=1)
    blooms_level: BloomsLevel


class Attempt(BaseModel):
    attempt_number: int = Field(..., ge=1)
    status: AttemptStatus
    draft: Optional[GeneratedContent] = None
    review: Optional[ReviewResult] = None
    refined: Optional[GeneratedContent] = None
    refinement_feedback: Optional[str] = None
    timestamp_start: datetime
    timestamp_end: Optional[datetime] = None


class GenerationInput(BaseModel):
    grade: int = Field(..., ge=1, le=12)
    topic: str = Field(..., min_length=3)


class FinalResult(BaseModel):
    status: ContentStatus
    content: Optional[GeneratedContent] = None
    tags: Optional[Tags] = None


class RunArtifact(BaseModel):
    run_id: str
    input: GenerationInput
    attempts: List[Attempt] = Field(default_factory=list)
    final: FinalResult
    timestamps: Dict[str, datetime]
    user_id: Optional[str] = None
