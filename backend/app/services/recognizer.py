from __future__ import annotations

import json
import re
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

from ..config import Settings
from ..time_utils import app_now


PROVINCES = "京津沪渝冀豫云辽黑湘皖鲁新苏浙赣鄂桂甘晋蒙陕吉闽贵粤青藏川宁琼使领警学港澳"
PLATE_ALLOWED = set(PROVINCES + "ABCDEFGHJKLMNPQRSTUVWXYZ0123456789")
LETTER_FIXES = str.maketrans({"0": "O", "1": "I", "2": "Z", "5": "S", "8": "B"})
DIGIT_FIXES = str.maketrans({"O": "0", "Q": "0", "D": "0", "I": "1", "L": "1", "Z": "2", "S": "5", "B": "8"})


@dataclass
class PlateCandidate:
    bbox: tuple[int, int, int, int]
    score: float
    source: str
    color: str | None = None
    preset_text: str | None = None
    preset_rec_score: float = 0.0


@dataclass
class PlateDetection:
    plate_text: str
    det_score: float
    rec_score: float
    bbox_json: str
    source_type: str
    source_filename: str | None
    plate_image_path: str | None
    frame_image_path: str | None
    recognized_at: datetime


class PlateRecognizer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.model = None
        self.ocr = None
        self.font = None
        self.plates_dir = settings.upload_dir / "plates"
        self.frames_dir = settings.upload_dir / "frames"

    def load(self) -> None:
        import torch  # noqa: F401 - initialize torch DLL paths before PaddleOCR imports albumentations
        from paddleocr import PaddleOCR
        from ultralytics import YOLO

        if not self.settings.yolo_model_path.exists():
            raise FileNotFoundError(f"YOLO model not found: {self.settings.yolo_model_path}")
        if not self.settings.ocr_rec_model_dir.exists():
            raise FileNotFoundError(f"OCR rec model not found: {self.settings.ocr_rec_model_dir}")

        self.model = YOLO(str(self.settings.yolo_model_path), task="detect")
        self.ocr = PaddleOCR(
            use_angle_cls=False,
            lang="ch",
            det=False,
            det_model_dir=str(self.settings.ocr_det_model_dir),
            cls_model_dir=str(self.settings.ocr_cls_model_dir),
            rec_model_dir=str(self.settings.ocr_rec_model_dir),
            show_log=False,
        )
        if self.settings.font_path.exists():
            self.font = ImageFont.truetype(str(self.settings.font_path), 32, 0)

    def recognize_image_file(
        self,
        image_path: Path,
        source_type: str = "image",
        source_filename: str | None = None,
        persist_images: bool = True,
    ) -> list[PlateDetection]:
        image = cv2.imdecode(np.fromfile(str(image_path), dtype=np.uint8), cv2.IMREAD_COLOR)
        if image is None:
            raise ValueError(f"Could not read image: {image_path}")
        return self.recognize_frame(
            image,
            source_type=source_type,
            source_filename=source_filename,
            persist_images=persist_images,
        )

    def recognize_frame(
        self,
        frame: np.ndarray,
        source_type: str,
        source_filename: str | None = None,
        frame_index: int | None = None,
        persist_images: bool = True,
    ) -> list[PlateDetection]:
        if self.model is None or self.ocr is None:
            raise RuntimeError("Recognizer has not been loaded")

        candidates = self._detect_plate_candidates(frame)

        annotated = frame.copy()
        detections: list[PlateDetection] = []
        frame_stamp = app_now()
        frame_token = self._file_token(source_type, source_filename, frame_index)

        for candidate in candidates:
            x1, y1, x2, y2 = candidate.bbox
            if x2 <= x1 or y2 <= y1:
                continue

            crop = frame[y1:y2, x1:x2]
            if candidate.preset_text:
                plate_text = self._normalize_plate_text(candidate.preset_text)
                rec_score = candidate.preset_rec_score
            else:
                plate_text, rec_score = self._ocr_plate(crop)
            if candidate.source == "color" and not plate_text:
                continue
            plate_text = plate_text or "无法识别"
            det_score = candidate.score
            annotated = self._draw_label(annotated, [x1, y1, x2, y2], plate_text, det_score, rec_score)

            plate_media_path = None
            if persist_images:
                plate_filename = f"{frame_token}_{len(detections) + 1}_{uuid.uuid4().hex[:8]}.jpg"
                plate_path = self.plates_dir / plate_filename
                self.plates_dir.mkdir(parents=True, exist_ok=True)
                cv2.imwrite(str(plate_path), crop)
                plate_media_path = self._media_path("plates", plate_filename)

            detections.append(
                PlateDetection(
                    plate_text=plate_text,
                    det_score=det_score,
                    rec_score=rec_score,
                    bbox_json=json.dumps([x1, y1, x2, y2], ensure_ascii=False),
                    source_type=source_type,
                    source_filename=source_filename,
                    plate_image_path=plate_media_path,
                    frame_image_path=None,
                    recognized_at=frame_stamp,
                )
            )

        if not detections:
            for candidate in self._detect_ocr_plate_candidates(frame):
                x1, y1, x2, y2 = candidate.bbox
                if x2 <= x1 or y2 <= y1:
                    continue

                crop = frame[y1:y2, x1:x2]
                plate_text = self._normalize_plate_text(candidate.preset_text)
                if not plate_text:
                    continue

                rec_score = candidate.preset_rec_score
                det_score = candidate.score
                annotated = self._draw_label(annotated, [x1, y1, x2, y2], plate_text, det_score, rec_score)

                plate_media_path = None
                if persist_images:
                    plate_filename = f"{frame_token}_{len(detections) + 1}_{uuid.uuid4().hex[:8]}.jpg"
                    plate_path = self.plates_dir / plate_filename
                    self.plates_dir.mkdir(parents=True, exist_ok=True)
                    cv2.imwrite(str(plate_path), crop)
                    plate_media_path = self._media_path("plates", plate_filename)

                detections.append(
                    PlateDetection(
                        plate_text=plate_text,
                        det_score=det_score,
                        rec_score=rec_score,
                        bbox_json=json.dumps([x1, y1, x2, y2], ensure_ascii=False),
                        source_type=source_type,
                        source_filename=source_filename,
                        plate_image_path=plate_media_path,
                        frame_image_path=None,
                        recognized_at=frame_stamp,
                    )
                )

        if not detections:
            return []

        self._refine_detections_with_full_ocr(frame, detections)
        annotated = frame.copy()
        for detection in detections:
            bbox = json.loads(detection.bbox_json)
            annotated = self._draw_label(annotated, bbox, detection.plate_text, detection.det_score, detection.rec_score)

        frame_media_path = None
        if persist_images:
            frame_filename = f"{frame_token}_{uuid.uuid4().hex[:8]}_frame.jpg"
            frame_path = self.frames_dir / frame_filename
            self.frames_dir.mkdir(parents=True, exist_ok=True)
            cv2.imwrite(str(frame_path), annotated)
            frame_media_path = self._media_path("frames", frame_filename)
        for detection in detections:
            detection.frame_image_path = frame_media_path

        return detections

    def _ocr_plate(self, image: np.ndarray) -> tuple[str | None, float]:
        best_text: str | None = None
        best_confidence = 0.0
        best_score = -1.0

        for variant in self._plate_ocr_variants(image):
            text, confidence = self._ocr_plate_once(variant)
            normalized = self._normalize_plate_text(text)
            if not normalized:
                continue

            score = confidence + self._plate_format_score(normalized)
            if score > best_score:
                best_text = normalized
                best_confidence = confidence
                best_score = score

        return best_text, best_confidence

    def _ocr_plate_once(self, image: np.ndarray) -> tuple[str | None, float]:
        raw_result: Any = self.ocr.ocr(image, det=False, cls=False)
        if not raw_result:
            return None, 0.0

        lines = raw_result[0] if isinstance(raw_result, list) and raw_result else raw_result
        if not lines:
            return None, 0.0

        first = lines[0]
        text: str | None = None
        confidence = 0.0

        if isinstance(first, (list, tuple)) and len(first) >= 2:
            maybe_text = first[1]
            if isinstance(maybe_text, (list, tuple)) and len(maybe_text) >= 2:
                text = str(maybe_text[0])
                confidence = float(maybe_text[1])
            elif isinstance(first[0], str):
                text = str(first[0])
                confidence = float(first[1] or 0)

        if not text:
            return None, 0.0

        text = text.replace("路", "").replace(" ", "").strip()
        return text or None, confidence

    def _detect_plate_candidates(self, frame: np.ndarray) -> list[PlateCandidate]:
        candidates: list[PlateCandidate] = []

        results = self.model.predict(
            source=frame,
            conf=self.settings.detect_confidence,
            imgsz=640,
            verbose=False,
        )
        if results and results[0].boxes is not None and len(results[0].boxes) > 0:
            boxes = results[0].boxes.xyxy.cpu().numpy()
            confs = results[0].boxes.conf.cpu().numpy()
            order = np.argsort(-confs)
            for index in order:
                bbox = self._expand_bbox(self._clip_bbox(boxes[index], frame.shape), frame.shape, pad_ratio=0.06)
                candidates.append(PlateCandidate(bbox=bbox, score=float(confs[index]), source="yolo"))

        for candidate in self._detect_color_plate_candidates(frame):
            if not any(self._iou(candidate.bbox, existing.bbox) > 0.45 for existing in candidates):
                candidates.append(candidate)

        return candidates

    def _detect_ocr_plate_candidates(self, frame: np.ndarray) -> list[PlateCandidate]:
        raw_result: Any = self.ocr.ocr(frame, det=True, cls=False)
        if not raw_result:
            return []

        lines = raw_result[0] if isinstance(raw_result, list) and raw_result else []
        candidates: list[PlateCandidate] = []
        for line in lines or []:
            if not isinstance(line, (list, tuple)) or len(line) < 2:
                continue

            box, text_info = line[0], line[1]
            if not isinstance(text_info, (list, tuple)) or len(text_info) < 2:
                continue

            normalized = self._normalize_plate_text(str(text_info[0]))
            if not normalized:
                continue

            points = np.asarray(box, dtype=np.float32)
            if points.ndim != 2 or points.shape[1] != 2:
                continue

            x1, y1 = np.floor(points.min(axis=0)).astype(int)
            x2, y2 = np.ceil(points.max(axis=0)).astype(int)
            bbox = self._expand_bbox(self._clip_bbox(np.array([x1, y1, x2, y2]), frame.shape), frame.shape, pad_ratio=0.12)
            confidence = float(text_info[1] or 0.0)
            candidates.append(
                PlateCandidate(
                    bbox=bbox,
                    score=max(0.5, min(confidence, 0.99)),
                    source="ocr",
                    preset_text=normalized,
                    preset_rec_score=confidence,
                )
            )

        candidates.sort(key=lambda item: item.preset_rec_score, reverse=True)
        deduped: list[PlateCandidate] = []
        for candidate in candidates:
            if not any(self._iou(candidate.bbox, existing.bbox) > 0.35 for existing in deduped):
                deduped.append(candidate)
        return deduped[:4]

    def _refine_detections_with_full_ocr(self, frame: np.ndarray, detections: list[PlateDetection]) -> None:
        if not any(detection.rec_score < 0.95 for detection in detections):
            return

        for candidate in self._detect_ocr_plate_candidates(frame):
            normalized = self._normalize_plate_text(candidate.preset_text)
            if not normalized:
                continue

            for detection in detections:
                bbox = tuple(json.loads(detection.bbox_json))
                if self._iou(candidate.bbox, bbox) <= 0.35:
                    continue

                is_better_text = len(normalized) > len(detection.plate_text)
                is_better_score = candidate.preset_rec_score > detection.rec_score
                if is_better_text or is_better_score:
                    detection.plate_text = normalized
                    detection.rec_score = candidate.preset_rec_score
                    detection.det_score = max(detection.det_score, candidate.score)
                    detection.bbox_json = json.dumps(list(candidate.bbox), ensure_ascii=False)

    def _detect_color_plate_candidates(self, frame: np.ndarray) -> list[PlateCandidate]:
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        masks = {
            "blue": cv2.inRange(hsv, np.array([90, 50, 45]), np.array([135, 255, 255])),
            "yellow": cv2.inRange(hsv, np.array([12, 55, 80]), np.array([40, 255, 255])),
            "green": cv2.inRange(hsv, np.array([35, 35, 55]), np.array([95, 255, 255])),
            "white": cv2.inRange(hsv, np.array([0, 0, 150]), np.array([180, 65, 255])),
        }
        red_mask_1 = cv2.inRange(hsv, np.array([0, 45, 55]), np.array([10, 255, 255]))
        red_mask_2 = cv2.inRange(hsv, np.array([165, 45, 55]), np.array([180, 255, 255]))
        masks["red"] = cv2.bitwise_or(red_mask_1, red_mask_2)
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (9, 3))
        frame_h, frame_w = frame.shape[:2]
        candidates: list[PlateCandidate] = []

        for color, mask in masks.items():
            mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
            mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
            contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

            for contour in contours:
                x, y, w, h = cv2.boundingRect(contour)
                if h == 0:
                    continue
                aspect = w / float(h)
                area = cv2.contourArea(contour)
                fill = area / max(w * h, 1)
                if w < 45 or h < 14 or aspect < 1.7 or aspect > 7.5 or fill < 0.18:
                    continue
                if w * h < max(700, frame_w * frame_h * 0.0005):
                    continue

                bbox = self._expand_bbox((x, y, x + w, y + h), frame.shape, pad_ratio=0.16)
                candidates.append(PlateCandidate(bbox=bbox, score=0.55, source="color", color=color))

        candidates.sort(key=lambda item: (item.score, (item.bbox[2] - item.bbox[0]) * (item.bbox[3] - item.bbox[1])), reverse=True)
        deduped: list[PlateCandidate] = []
        for candidate in candidates:
            if not any(self._iou(candidate.bbox, existing.bbox) > 0.35 for existing in deduped):
                deduped.append(candidate)
        return deduped[:6]

    @staticmethod
    def _plate_ocr_variants(image: np.ndarray) -> list[np.ndarray]:
        if image.size == 0:
            return []

        variants = [image]
        h, w = image.shape[:2]
        scale = 3 if w < 140 else 2
        resized = cv2.resize(image, (w * scale, h * scale), interpolation=cv2.INTER_CUBIC)
        variants.append(resized)

        lab = cv2.cvtColor(resized, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = cv2.merge((clahe.apply(l_channel), a_channel, b_channel))
        variants.append(cv2.cvtColor(enhanced, cv2.COLOR_LAB2BGR))

        gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
        gray = cv2.bilateralFilter(gray, 5, 35, 35)
        sharp = cv2.addWeighted(gray, 1.6, cv2.GaussianBlur(gray, (0, 0), 1.1), -0.6, 0)
        variants.append(cv2.cvtColor(sharp, cv2.COLOR_GRAY2BGR))

        return variants

    @staticmethod
    def _normalize_plate_text(text: str | None) -> str | None:
        if not text:
            return None

        text = text.upper().replace("·", "").replace("-", "").replace("_", "")
        text = text.replace(" ", "").replace("路", "")
        chars = [ch for ch in text if ch in PLATE_ALLOWED]
        if not chars:
            return None

        first_province_index = next((index for index, ch in enumerate(chars) if ch in PROVINCES), None)
        if first_province_index is not None:
            chars = chars[first_province_index:]

        if len(chars) >= 2 and chars[0] in PROVINCES:
            chars[1] = chars[1].translate(LETTER_FIXES)

        if len(chars) >= 8 and chars[0] in PROVINCES and chars[2].isalpha():
            # New-energy plates often use one letter followed mostly by digits. This fixes D/O/Q -> 0
            # without changing the energy marker at position 3.
            for index in range(3, len(chars)):
                chars[index] = chars[index].translate(DIGIT_FIXES)
        elif len(chars) >= 7 and chars[0] in PROVINCES:
            for index in range(2, len(chars)):
                if chars[index] in {"O", "Q"}:
                    chars[index] = "0"

        normalized = "".join(chars)
        match = re.search(rf"[{PROVINCES}][A-Z][A-Z0-9]{{5,6}}", normalized)
        if match:
            normalized = match.group(0)
        elif len(normalized) > 8:
            normalized = normalized[:8]

        if not 6 <= len(normalized) <= 8:
            return None
        return normalized if normalized[0] in PROVINCES else None

    @staticmethod
    def _plate_format_score(text: str) -> float:
        if re.fullmatch(rf"[{PROVINCES}][A-Z][A-Z0-9]{{5}}", text):
            return 0.35
        if re.fullmatch(rf"[{PROVINCES}][A-Z][A-Z0-9]{{6}}", text):
            return 0.45
        if text and text[0] in PROVINCES:
            return 0.15
        return 0.0

    def _draw_label(
        self,
        image: np.ndarray,
        bbox: list[int],
        text: str,
        det_score: float,
        rec_score: float,
    ) -> np.ndarray:
        x1, y1, x2, y2 = bbox
        cv2.rectangle(image, (x1, y1), (x2, y2), (20, 170, 120), 2)
        label = f"{text} D:{det_score:.2f} R:{rec_score:.2f}"

        if self.font is None:
            cv2.putText(image, label, (x1, max(24, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (20, 170, 120), 2)
            return image

        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        pil_image = Image.fromarray(rgb_image)
        draw = ImageDraw.Draw(pil_image)
        draw.text((x1, max(0, y1 - 34)), label, fill=(20, 170, 120), font=self.font)
        return cv2.cvtColor(np.asarray(pil_image), cv2.COLOR_RGB2BGR)

    @staticmethod
    def _clip_bbox(box: np.ndarray, shape: tuple[int, ...]) -> tuple[int, int, int, int]:
        h, w = shape[:2]
        x1, y1, x2, y2 = [int(value) for value in box]
        return max(0, x1), max(0, y1), min(w - 1, x2), min(h - 1, y2)

    @staticmethod
    def _expand_bbox(bbox: tuple[int, int, int, int], shape: tuple[int, ...], pad_ratio: float) -> tuple[int, int, int, int]:
        x1, y1, x2, y2 = bbox
        h, w = shape[:2]
        pad_x = int((x2 - x1) * pad_ratio)
        pad_y = int((y2 - y1) * pad_ratio)
        return max(0, x1 - pad_x), max(0, y1 - pad_y), min(w - 1, x2 + pad_x), min(h - 1, y2 + pad_y)

    @staticmethod
    def _iou(first: tuple[int, int, int, int], second: tuple[int, int, int, int]) -> float:
        ax1, ay1, ax2, ay2 = first
        bx1, by1, bx2, by2 = second
        ix1, iy1 = max(ax1, bx1), max(ay1, by1)
        ix2, iy2 = min(ax2, bx2), min(ay2, by2)
        iw, ih = max(0, ix2 - ix1), max(0, iy2 - iy1)
        intersection = iw * ih
        first_area = max(0, ax2 - ax1) * max(0, ay2 - ay1)
        second_area = max(0, bx2 - bx1) * max(0, by2 - by1)
        union = first_area + second_area - intersection
        return intersection / union if union else 0.0

    @staticmethod
    def _media_path(directory: str, filename: str) -> str:
        return f"/media/{directory}/{filename}"

    @staticmethod
    def _file_token(source_type: str, source_filename: str | None, frame_index: int | None) -> str:
        safe_source = "".join(ch if ch.isalnum() else "_" for ch in (source_filename or source_type))[:48]
        frame_part = f"_f{frame_index}" if frame_index is not None else ""
        return f"{app_now().strftime('%Y%m%d_%H%M%S_%f')}_{safe_source}{frame_part}"
