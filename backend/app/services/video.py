from __future__ import annotations

import math
import time
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


def _video_analysis_interval(total_frames: int) -> int:
    base_interval = max(1, settings.video_frame_interval)
    if total_frames <= 0 or settings.video_max_analysis_frames <= 0:
        return base_interval
    capped_interval = math.ceil(total_frames / settings.video_max_analysis_frames)
    return max(base_interval, capped_interval)


def _should_analyze_frame(frame_index: int, interval: int) -> bool:
    return frame_index == 1 or frame_index % interval == 0


def _resize_video_frame(frame):
    max_side = max(0, settings.video_process_max_side)
    if not max_side:
        return frame

    height, width = frame.shape[:2]
    current_side = max(height, width)
    if current_side <= max_side:
        return frame

    scale = max_side / float(current_side)
    resized_width = max(1, int(width * scale))
    resized_height = max(1, int(height * scale))
    return cv2.resize(frame, (resized_width, resized_height), interpolation=cv2.INTER_AREA)


def _grab_next_frame(cap: cv2.VideoCapture, frame_index: int) -> tuple[bool, int]:
    grabbed = cap.grab()
    if not grabbed:
        return False, frame_index
    return True, frame_index + 1


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
        analysis_interval = _video_analysis_interval(total_frames)
        last_progress_commit = time.monotonic()
        last_seen: dict[str, int] = {}

        while True:
            grabbed, frame_index = _grab_next_frame(cap, frame_index)
            if not grabbed:
                break

            if not _should_analyze_frame(frame_index, analysis_interval):
                if time.monotonic() - last_progress_commit >= 1:
                    job.processed_frames = frame_index
                    job.progress = round((frame_index / total_frames) * 100, 2) if total_frames else 0
                    job.updated_at = app_now()
                    db.commit()
                    last_progress_commit = time.monotonic()
                continue

            success, frame = cap.retrieve()
            if not success:
                continue

            job.processed_frames = frame_index
            job.progress = round((frame_index / total_frames) * 100, 2) if total_frames else 0
            job.updated_at = app_now()
            db.commit()
            last_progress_commit = time.monotonic()

            detections = recognizer.recognize_frame(
                _resize_video_frame(frame),
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
            last_progress_commit = time.monotonic()

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
        analysis_interval = _video_analysis_interval(total_frames)
        last_progress_update = time.monotonic()
        last_seen: dict[str, int] = {}
        output_records: list[RecognitionRecordOut] = []

        while True:
            grabbed, frame_index = _grab_next_frame(cap, frame_index)
            if not grabbed:
                break

            if not _should_analyze_frame(frame_index, analysis_interval):
                if time.monotonic() - last_progress_update >= 1:
                    job["processed_frames"] = frame_index
                    job["progress"] = round((frame_index / total_frames) * 100, 2) if total_frames else 0
                    job["updated_at"] = app_now()
                    last_progress_update = time.monotonic()
                continue

            success, frame = cap.retrieve()
            if not success:
                continue

            job["processed_frames"] = frame_index
            job["progress"] = round((frame_index / total_frames) * 100, 2) if total_frames else 0
            job["updated_at"] = app_now()
            last_progress_update = time.monotonic()

            detections = recognizer.recognize_frame(
                _resize_video_frame(frame),
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
            last_progress_update = time.monotonic()

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
