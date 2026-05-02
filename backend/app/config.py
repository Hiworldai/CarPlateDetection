from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional until backend deps are installed
    load_dotenv = None


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if load_dotenv:
    load_dotenv(PROJECT_ROOT / "backend" / ".env")


def _csv_env(name: str, default: str) -> list[str]:
    raw_value = os.getenv(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _path_env(name: str, default: Path) -> Path:
    configured = Path(os.getenv(name, str(default)))
    if configured.is_absolute():
        return configured
    return PROJECT_ROOT / configured


@dataclass(frozen=True)
class Settings:
    app_name: str = os.getenv("APP_NAME", "Car Plate Recognition API")
    debug: bool = os.getenv("DEBUG", "false").lower() == "true"
    database_url: str = os.getenv(
        "DATABASE_URL",
        "mysql+pymysql://root:password@127.0.0.1:3306/car_plate_detection?charset=utf8mb4",
    )
    api_prefix: str = "/api"
    allowed_origins: list[str] = None
    session_secret: str = os.getenv("SESSION_SECRET", "change-this-session-secret")
    admin_username: str = os.getenv("ADMIN_USERNAME", "admin")
    admin_password: str = os.getenv("ADMIN_PASSWORD", "change-this-admin-password")
    upload_dir: Path = _path_env("UPLOAD_DIR", PROJECT_ROOT / "backend" / "storage")
    yolo_model_path: Path = _path_env("YOLO_MODEL_PATH", PROJECT_ROOT / "models" / "best.pt")
    ocr_cls_model_dir: Path = _path_env(
        "OCR_CLS_MODEL_DIR",
        PROJECT_ROOT / "paddleModels" / "whl" / "cls" / "ch_ppocr_mobile_v2.0_cls_infer",
    )
    ocr_det_model_dir: Path = _path_env(
        "OCR_DET_MODEL_DIR",
        PROJECT_ROOT / "paddleModels" / "whl" / "det" / "ch" / "ch_PP-OCRv4_det_infer",
    )
    ocr_rec_model_dir: Path = _path_env(
        "OCR_REC_MODEL_DIR",
        PROJECT_ROOT / "paddleModels" / "whl" / "rec" / "ch" / "ch_PP-OCRv4_rec_infer",
    )
    font_path: Path = _path_env("FONT_PATH", PROJECT_ROOT / "Font" / "platech.ttf")
    detect_confidence: float = float(os.getenv("DETECT_CONFIDENCE", "0.35"))
    video_frame_interval: int = int(os.getenv("VIDEO_FRAME_INTERVAL", "5"))
    duplicate_frame_window: int = int(os.getenv("DUPLICATE_FRAME_WINDOW", "30"))

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "allowed_origins",
            _csv_env("ALLOWED_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173"),
        )


settings = Settings()
