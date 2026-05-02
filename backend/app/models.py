from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from .database import Base
from .time_utils import app_now


class RecognitionRecord(Base):
    __tablename__ = "recognition_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True, autoincrement=True)
    plate_text: Mapped[str] = mapped_column(String(64), index=True)
    det_score: Mapped[float] = mapped_column(Float, default=0.0)
    rec_score: Mapped[float] = mapped_column(Float, default=0.0)
    source_type: Mapped[str] = mapped_column(String(32), index=True)
    source_filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    plate_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    frame_image_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    bbox_json: Mapped[str | None] = mapped_column(Text, nullable=True)
    recognized_at: Mapped[datetime] = mapped_column(DateTime, default=app_now, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=app_now)


class RecognitionJob(Base):
    __tablename__ = "recognition_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)
    source_type: Mapped[str] = mapped_column(String(32), default="video", index=True)
    filename: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    progress: Mapped[float] = mapped_column(Float, default=0.0)
    total_frames: Mapped[int] = mapped_column(Integer, default=0)
    processed_frames: Mapped[int] = mapped_column(Integer, default=0)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=app_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=app_now, onupdate=app_now)
