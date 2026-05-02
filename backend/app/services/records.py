from __future__ import annotations

from datetime import datetime

from sqlalchemy import Select, func, select
from sqlalchemy.orm import Session

from ..models import RecognitionRecord


def build_record_query(
    plate_text: str | None = None,
    source_type: str | None = None,
    start_time: datetime | None = None,
    end_time: datetime | None = None,
) -> Select:
    query = select(RecognitionRecord)
    if plate_text:
        query = query.where(RecognitionRecord.plate_text.like(f"%{plate_text}%"))
    if source_type:
        query = query.where(RecognitionRecord.source_type == source_type)
    if start_time:
        query = query.where(RecognitionRecord.recognized_at >= start_time)
    if end_time:
        query = query.where(RecognitionRecord.recognized_at <= end_time)
    return query


def count_records(db: Session, query: Select) -> int:
    count_query = select(func.count()).select_from(query.order_by(None).subquery())
    return int(db.execute(count_query).scalar_one())


def list_records(
    db: Session,
    plate_text: str | None,
    source_type: str | None,
    start_time: datetime | None,
    end_time: datetime | None,
    page: int,
    per_page: int,
) -> tuple[list[RecognitionRecord], int]:
    query = build_record_query(plate_text, source_type, start_time, end_time)
    total = count_records(db, query)
    items = db.execute(
        query.order_by(RecognitionRecord.recognized_at.desc(), RecognitionRecord.id.desc())
        .offset((page - 1) * per_page)
        .limit(per_page)
    ).scalars().all()
    return items, total
