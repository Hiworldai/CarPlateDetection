from __future__ import annotations

import shutil
import uuid
from pathlib import Path

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
