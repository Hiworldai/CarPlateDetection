from __future__ import annotations

import uuid
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from ..config import settings
from ..dependencies import get_db, get_optional_user, get_recognizer
from ..models import RecognitionJob, RecognitionRecord
from ..schemas import ImageRecognitionOut, JobCreateOut, JobOut, RecognitionListOut, RecognitionRecordOut
from ..services.exporter import build_excel
from ..services.files import save_upload_file
from ..services.recognizer import PlateDetection, PlateRecognizer
from ..services.records import build_record_query, list_records
from ..services.video import process_guest_video_job, process_video_job
from ..time_utils import app_now

router = APIRouter()


def _record_out_from_detection(detection: PlateDetection) -> RecognitionRecordOut:
    return RecognitionRecordOut(
        id=None,
        plate_text=detection.plate_text,
        det_score=detection.det_score,
        rec_score=detection.rec_score,
        source_type=detection.source_type,
        source_filename=detection.source_filename,
        plate_image_path=detection.plate_image_path,
        frame_image_path=detection.frame_image_path,
        bbox_json=detection.bbox_json,
        recognized_at=detection.recognized_at,
        created_at=None,
    )


@router.post("/recognitions/image", response_model=ImageRecognitionOut)
def recognize_image(
    file: UploadFile = File(...),
    source_type: str = Form("image"),
    db: Session = Depends(get_db),
    recognizer: PlateRecognizer = Depends(get_recognizer),
    user: str | None = Depends(get_optional_user),
) -> ImageRecognitionOut:
    if source_type not in {"image", "camera"}:
        raise HTTPException(status_code=400, detail="source_type must be image or camera")

    upload_path = save_upload_file(file, settings.upload_dir / "uploads", prefix=source_type)
    persisted = bool(user)
    try:
        detections = recognizer.recognize_image_file(
            upload_path,
            source_type=source_type,
            source_filename=file.filename,
            persist_images=persisted,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        Path(upload_path).unlink(missing_ok=True)

    if persisted:
        records: list[RecognitionRecordOut] = []
        for detection in detections:
            record = RecognitionRecord(
                plate_text=detection.plate_text,
                det_score=detection.det_score,
                rec_score=detection.rec_score,
                source_type=detection.source_type,
                source_filename=detection.source_filename,
                plate_image_path=detection.plate_image_path,
                frame_image_path=detection.frame_image_path,
                bbox_json=detection.bbox_json,
                recognized_at=detection.recognized_at,
            )
            db.add(record)
            db.flush()
            db.refresh(record)
            records.append(RecognitionRecordOut.model_validate(record))
        db.commit()
    else:
        records = [_record_out_from_detection(detection) for detection in detections]

    message = "识别完成" if records else "未检测到车牌"
    return ImageRecognitionOut(records=records, message=message, persisted=persisted)


@router.post("/recognitions/video", response_model=JobCreateOut)
def recognize_video(
    background_tasks: BackgroundTasks,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    recognizer: PlateRecognizer = Depends(get_recognizer),
    user: str | None = Depends(get_optional_user),
) -> JobCreateOut:
    upload_path = save_upload_file(file, settings.upload_dir / "uploads", prefix="video")
    persisted = bool(user)
    job_id = str(uuid.uuid4())

    if persisted:
        job = RecognitionJob(id=job_id, source_type="video", filename=file.filename, status="queued", progress=0)
        db.add(job)
        db.commit()
        background_tasks.add_task(process_video_job, job_id, str(upload_path), file.filename, recognizer)
    else:
        request.app.state.guest_jobs[job_id] = {
            "id": job_id,
            "source_type": "video",
            "filename": file.filename,
            "status": "queued",
            "progress": 0.0,
            "total_frames": 0,
            "processed_frames": 0,
            "error_message": None,
            "created_at": app_now(),
            "updated_at": app_now(),
            "records": [],
        }
        background_tasks.add_task(
            process_guest_video_job,
            request.app.state.guest_jobs,
            job_id,
            str(upload_path),
            file.filename,
            recognizer,
        )

    return JobCreateOut(job_id=job_id, status="queued", persisted=persisted)


@router.get("/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, request: Request, db: Session = Depends(get_db)) -> JobOut:
    job = db.get(RecognitionJob, job_id)
    if job:
        return JobOut.model_validate(job)

    guest_job = request.app.state.guest_jobs.get(job_id)
    if guest_job:
        return JobOut(**guest_job)
    raise HTTPException(status_code=404, detail="Job not found")


@router.get("/recognitions", response_model=RecognitionListOut)
def get_recognitions(
    plate_text: str | None = Query(None),
    source_type: str | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
    user: str | None = Depends(get_optional_user),
) -> RecognitionListOut:
    if not user:
        raise HTTPException(status_code=401, detail="Please login first")
    items, total = list_records(db, plate_text, source_type, start_time, end_time, page, per_page)
    return RecognitionListOut(items=[RecognitionRecordOut.model_validate(item) for item in items], total=total, page=page, per_page=per_page)


@router.get("/recognitions/export")
def export_recognitions(
    plate_text: str | None = Query(None),
    source_type: str | None = Query(None),
    start_time: datetime | None = Query(None),
    end_time: datetime | None = Query(None),
    db: Session = Depends(get_db),
    user: str | None = Depends(get_optional_user),
) -> StreamingResponse:
    if not user:
        raise HTTPException(status_code=401, detail="Please login first")
    query = build_record_query(plate_text, source_type, start_time, end_time)
    records = db.execute(query.order_by(RecognitionRecord.recognized_at.desc())).scalars().all()
    output = build_excel(records)
    filename = f"plate-recognitions-{app_now().strftime('%Y%m%d%H%M%S')}.xlsx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        output,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers=headers,
    )
