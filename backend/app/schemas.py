from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, field_serializer

from .time_utils import app_time_iso


class RecognitionRecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int | None = None
    plate_text: str
    det_score: float
    rec_score: float
    source_type: str
    source_filename: str | None = None
    plate_image_path: str | None = None
    frame_image_path: str | None = None
    bbox_json: str | None = None
    recognized_at: datetime
    created_at: datetime | None = None

    @field_serializer("recognized_at", "created_at")
    def serialize_app_time(self, value: datetime | None) -> str | None:
        return app_time_iso(value)


class RecognitionListOut(BaseModel):
    items: list[RecognitionRecordOut]
    total: int
    page: int
    per_page: int


class ImageRecognitionOut(BaseModel):
    records: list[RecognitionRecordOut]
    message: str
    persisted: bool


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    source_type: str
    filename: str | None = None
    status: str
    progress: float
    total_frames: int
    processed_frames: int
    error_message: str | None = None
    created_at: datetime
    updated_at: datetime
    records: list[RecognitionRecordOut] = []

    @field_serializer("created_at", "updated_at")
    def serialize_app_time(self, value: datetime | None) -> str | None:
        return app_time_iso(value)


class JobCreateOut(BaseModel):
    job_id: str
    status: str
    persisted: bool


class AuthLoginIn(BaseModel):
    username: str
    password: str


class AuthUserOut(BaseModel):
    authenticated: bool
    username: str | None = None
    storage_mode: str
