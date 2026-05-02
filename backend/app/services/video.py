from __future__ import annotations

from datetime import datetime
from pathlib import Path

import cv2

from ..config import settings
from ..database import SessionLocal
from ..models import RecognitionJob, RecognitionRecord
from ..schemas import RecognitionRecordOut
from ..time_utils import app_now
from .recognizer import PlateDetection, PlateRecognizer


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


def process_video_job(job_id: str, video_path: str, source_filename: str | None, recognizer: PlateRecognizer) -> None:
    db = SessionLocal()
    cap = None
    try:
        job = db.get(RecognitionJob, job_id)
        if not job:
            return

        job.status = "running"
        db.commit()

        cap = cv2.VideoCapture(str(Path(video_path)))
        if not cap.isOpened():
            raise RuntimeError("无法打开视频文件")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        job.total_frames = total_frames
        db.commit()

        frame_index = 0
        last_seen: dict[str, int] = {}

        while True:
            success, frame = cap.read()
            if not success:
                break

            frame_index += 1
            if frame_index % settings.video_frame_interval != 0:
                continue

            detections = recognizer.recognize_frame(
                frame,
                source_type="video",
                source_filename=source_filename,
                frame_index=frame_index,
            )
            for detection in detections:
                if detection.plate_text == "无法识别":
                    continue

                last_frame = last_seen.get(detection.plate_text)
                if last_frame is not None and frame_index - last_frame <= settings.duplicate_frame_window:
                    continue
                last_seen[detection.plate_text] = frame_index

                db.add(
                    RecognitionRecord(
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
                )

            job.processed_frames = frame_index
            job.progress = round((frame_index / total_frames) * 100, 2) if total_frames else 0
            job.updated_at = app_now()
            db.commit()

        job.status = "completed"
        job.progress = 100.0
        job.processed_frames = frame_index
        job.updated_at = app_now()
        db.commit()
    except Exception as exc:
        job = db.get(RecognitionJob, job_id)
        if job:
            job.status = "failed"
            job.error_message = str(exc)
            job.updated_at = app_now()
            db.commit()
    finally:
        if cap is not None:
            cap.release()
        try:
            Path(video_path).unlink(missing_ok=True)
        except OSError:
            pass
        db.close()


def process_guest_video_job(
    guest_jobs: dict[str, dict],
    job_id: str,
    video_path: str,
    source_filename: str | None,
    recognizer: PlateRecognizer,
) -> None:
    cap = None
    try:
        job = guest_jobs.get(job_id)
        if not job:
            return

        job["status"] = "running"
        job["updated_at"] = app_now()

        cap = cv2.VideoCapture(str(Path(video_path)))
        if not cap.isOpened():
            raise RuntimeError("无法打开视频文件")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        job["total_frames"] = total_frames

        frame_index = 0
        last_seen: dict[str, int] = {}
        output_records: list[RecognitionRecordOut] = []

        while True:
            success, frame = cap.read()
            if not success:
                break

            frame_index += 1
            if frame_index % settings.video_frame_interval != 0:
                continue

            detections = recognizer.recognize_frame(
                frame,
                source_type="video",
                source_filename=source_filename,
                frame_index=frame_index,
                persist_images=False,
            )

            for detection in detections:
                if detection.plate_text == "无法识别":
                    continue
                last_frame = last_seen.get(detection.plate_text)
                if last_frame is not None and frame_index - last_frame <= settings.duplicate_frame_window:
                    continue
                last_seen[detection.plate_text] = frame_index
                output_records.append(_record_out_from_detection(detection))

            job["processed_frames"] = frame_index
            job["progress"] = round((frame_index / total_frames) * 100, 2) if total_frames else 0
            job["updated_at"] = app_now()

        job["status"] = "completed"
        job["progress"] = 100.0
        job["processed_frames"] = frame_index
        job["updated_at"] = app_now()
        job["records"] = [record.model_dump(mode="json") for record in output_records]
    except Exception as exc:
        job = guest_jobs.get(job_id)
        if job:
            job["status"] = "failed"
            job["error_message"] = str(exc)
            job["updated_at"] = app_now()
            job["records"] = []
    finally:
        if cap is not None:
            cap.release()
        try:
            Path(video_path).unlink(missing_ok=True)
        except OSError:
            pass
