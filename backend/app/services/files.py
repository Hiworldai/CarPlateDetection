from __future__ import annotations

import shutil
import uuid
from pathlib import Path

import cv2
from fastapi import UploadFile


def ensure_storage_dirs(storage_root: Path) -> None:
    for name in ("uploads", "plates", "frames"):
        (storage_root / name).mkdir(parents=True, exist_ok=True)


def safe_suffix(filename: str | None) -> str:
    if not filename:
        return ""
    suffix = Path(filename).suffix.lower()
    return suffix if len(suffix) <= 12 else ""


def unique_name(filename: str | None, prefix: str = "") -> str:
    clean_prefix = f"{prefix}_" if prefix else ""
    return f"{clean_prefix}{uuid.uuid4().hex}{safe_suffix(filename)}"


def save_upload_file(upload: UploadFile, directory: Path, prefix: str = "") -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    destination = directory / unique_name(upload.filename, prefix=prefix)
    with destination.open("wb") as output:
        shutil.copyfileobj(upload.file, output)
    return destination


def get_video_duration_seconds(path: Path) -> float | None:
    cap = cv2.VideoCapture(str(path))
    try:
        if not cap.isOpened():
            return None
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0)
        frame_count = float(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        if fps <= 0 or frame_count <= 0:
            return None
        return frame_count / fps
    finally:
        cap.release()
