#coding:utf-8
import cv2
import time
import os
import csv
import json
import re
from datetime import datetime
from ultralytics import YOLO
import detect_tools as tools
from PIL import ImageFont


def get_license_result(image):
    """
    image: 输入的车牌截取照片
    输出: 车牌号与置信度
    这里先保留模拟结果，后面你换成真实OCR就行
    """
    return "模拟车牌", 0.99


def resize_for_infer(img, target_width=960):
    """
    推理前缩放，减少YOLO计算量
    返回: resized_img, scale
    scale = resized_width / original_width
    """
    h, w = img.shape[:2]
    if w <= target_width:
        return img, 1.0

    scale = target_width / float(w)
    resized = cv2.resize(
        img,
        (target_width, int(h * scale)),
        interpolation=cv2.INTER_LINEAR
    )
    return resized, scale


def expand_bbox(bbox, img_shape, pad_ratio=0.25):
    """
    在上一次框的基础上扩展一点，作为下一次ROI搜索区域
    bbox: (x1, y1, x2, y2)
    """
    x1, y1, x2, y2 = bbox
    h, w = img_shape[:2]

    bw = x2 - x1
    bh = y2 - y1

    pad_x = int(bw * pad_ratio)
    pad_y = int(bh * pad_ratio)

    nx1 = max(0, x1 - pad_x)
    ny1 = max(0, y1 - pad_y)
    nx2 = min(w, x2 + pad_x)
    ny2 = min(h, y2 + pad_y)

    return nx1, ny1, nx2, ny2


def safe_filename(text):
    """
    清理文件名中的非法字符
    """
    if not text:
        return "unknown"
    text = str(text).strip()
    return re.sub(r'[\\/:*?"<>| ]+', "_", text)


def save_result_to_csv(csv_path, row):
    with open(csv_path, "a", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(row)


def save_latest_result_to_json(json_path, data):
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


fontC = ImageFont.truetype("Font/platech.ttf", 50, 0)

print("加载YOLO模型...")
path = 'models/best.pt'

try:
    model = YOLO(path, task='detect')
    print("YOLO模型加载成功")
except Exception as e:
    print(f"YOLO模型加载失败: {e}")
    raise SystemExit

camera_id = 0
print(f"打开摄像头: {camera_id}")

cap = cv2.VideoCapture(camera_id)

# 加回摄像头参数设置，减少延迟并限制分辨率
cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)

if not cap.isOpened():
    print(f"无法打开摄像头: {camera_id}")
    print("请检查摄像头是否已连接或被其他程序占用")
    raise SystemExit

print(f"成功打开摄像头: {camera_id}")
print(f"摄像头宽度: {int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))}")
print(f"摄像头高度: {int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))}")
print(f"摄像头帧率: {cap.get(cv2.CAP_PROP_FPS)}")

# -------------------------
# 结果保存目录
# -------------------------
RESULT_DIR = "results"
PLATE_DIR = os.path.join(RESULT_DIR, "plates")
FRAME_DIR = os.path.join(RESULT_DIR, "frames")
CSV_PATH = os.path.join(RESULT_DIR, "history.csv")
JSON_PATH = os.path.join(RESULT_DIR, "latest_result.json")

os.makedirs(RESULT_DIR, exist_ok=True)
os.makedirs(PLATE_DIR, exist_ok=True)
os.makedirs(FRAME_DIR, exist_ok=True)

# history.csv 不存在时写入表头
if not os.path.exists(CSV_PATH):
    with open(CSV_PATH, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow([
            "time",
            "frame_index",
            "plate_text",
            "det_score",
            "rec_score",
            "x1",
            "y1",
            "x2",
            "y2",
            "plate_image",
            "frame_image"
        ])

# -------------------------
# 性能优化参数
# -------------------------
runtime_limit = 0           # 0 表示不限时；测试时可以改成 10
DETECT_INTERVAL = 5         # 每5帧做一次检测
OCR_INTERVAL = 10           # 每10帧做一次OCR
MAX_LOST = 5                # 连续丢失5次后清空目标
ROI_PAD_RATIO = 0.25        # ROI外扩比例
DISPLAY_SCALE = 0.5         # 显示缩放比例
INFER_WIDTH = 960           # 推理宽度，越小越快
CONF_THRESH = 0.35          # 检测阈值

# 结果保存去重参数
SAVE_COOLDOWN = 2.0         # 同样结果至少间隔2秒再保存一次

start_time = time.time()
if runtime_limit > 0:
    print(f"开始检测，将在 {runtime_limit} 秒后自动停止")
else:
    print("开始检测，不限时运行，按 q 退出")
print(f"识别结果将保存到: {RESULT_DIR}")

# -------------------------
# 状态缓存
# -------------------------
frame_index = 0

last_bbox = None            # (x1, y1, x2, y2)
last_text = ""
last_det_score = 0.0
last_rec_score = 0.0
lost_count = 0

# 最近一次保存状态（避免每一帧都重复保存）
last_saved_text = ""
last_save_time = 0.0

# FPS统计
fps_counter = 0
fps_start_time = time.time()
show_fps = 0.0

while cap.isOpened():
    if runtime_limit > 0 and (time.time() - start_time > runtime_limit):
        print(f"运行时间已达 {runtime_limit} 秒，自动停止检测")
        break

    success, frame = cap.read()
    if not success:
        print("摄像头读取失败，结束")
        break

    frame_index += 1

    # 是否做检测 / OCR
    do_detect = (
        frame_index % DETECT_INTERVAL == 0
        or last_bbox is None
        or lost_count >= MAX_LOST
    )
    do_ocr = (
        frame_index % OCR_INTERVAL == 0
        or last_text == ""
    )

    # 默认先复用上一次结果
    current_bbox = last_bbox
    current_text = last_text
    current_det_score = last_det_score
    current_rec_score = last_rec_score

    if do_detect:
        # 1) 优先在上一次目标附近做ROI检测
        search_frame = frame
        offset_x, offset_y = 0, 0

        if last_bbox is not None and lost_count < MAX_LOST:
            rx1, ry1, rx2, ry2 = expand_bbox(last_bbox, frame.shape, ROI_PAD_RATIO)
            search_frame = frame[ry1:ry2, rx1:rx2]
            offset_x, offset_y = rx1, ry1

        # 2) 推理前缩放
        infer_frame, infer_scale = resize_for_infer(search_frame, INFER_WIDTH)

        try:
            results = model.predict(
                source=infer_frame,
                conf=CONF_THRESH,
                imgsz=640,
                verbose=False
            )

            found = False

            if results and len(results) > 0 and results[0].boxes is not None:
                boxes_tensor = results[0].boxes.xyxy
                confs_tensor = results[0].boxes.conf

                if boxes_tensor is not None and len(boxes_tensor) > 0:
                    boxes = boxes_tensor.cpu().numpy()
                    confs = confs_tensor.cpu().numpy()

                    # 只取最高置信度的一个框，最省性能
                    best_idx = confs.argmax()
                    x1, y1, x2, y2 = boxes[best_idx]
                    det_score = float(confs[best_idx])

                    # 映射回 search_frame 坐标
                    x1 = int(x1 / infer_scale)
                    y1 = int(y1 / infer_scale)
                    x2 = int(x2 / infer_scale)
                    y2 = int(y2 / infer_scale)

                    # 再映射回原图坐标
                    x1 += offset_x
                    y1 += offset_y
                    x2 += offset_x
                    y2 += offset_y

                    # 边界保护
                    x1 = max(0, min(x1, frame.shape[1] - 1))
                    y1 = max(0, min(y1, frame.shape[0] - 1))
                    x2 = max(0, min(x2, frame.shape[1] - 1))
                    y2 = max(0, min(y2, frame.shape[0] - 1))

                    if x2 > x1 and y2 > y1:
                        current_bbox = (x1, y1, x2, y2)
                        current_det_score = det_score
                        lost_count = 0
                        found = True

                        # 3) OCR降频执行
                        if do_ocr:
                            plate_img = frame[y1:y2, x1:x2]
                            text, rec_score = get_license_result(plate_img)

                            if text:
                                current_text = text
                                current_rec_score = float(rec_score)

            if not found:
                lost_count += 1
                if lost_count >= MAX_LOST:
                    current_bbox = None
                    current_det_score = 0.0

        except Exception as e:
            print(f"检测错误: {e}")
            lost_count += 1
            if lost_count >= MAX_LOST:
                current_bbox = None
                current_det_score = 0.0

    # 更新缓存
    last_bbox = current_bbox
    last_text = current_text
    last_det_score = current_det_score
    last_rec_score = current_rec_score

    # 绘制
    draw_frame = frame.copy()

    if current_bbox is not None:
        x1, y1, x2, y2 = current_bbox
        label = f"{current_text if current_text else '识别中'}  D:{current_det_score:.2f}  R:{current_rec_score:.2f}"
        draw_frame = tools.drawRectBox(draw_frame, [x1, y1, x2, y2], label, fontC)

        # 保存结果到一个地方
        should_save = False
        now_ts = time.time()

        # 只在有文字结果时保存，并做简单去重
        if current_text:
            if current_text != last_saved_text:
                should_save = True
            elif now_ts - last_save_time >= SAVE_COOLDOWN:
                should_save = True

        if should_save:
            now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            file_time = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            safe_text = safe_filename(current_text)

            # 保存车牌截图
            plate_img = frame[y1:y2, x1:x2]
            plate_filename = f"{file_time}_{safe_text}.jpg"
            plate_path = os.path.join(PLATE_DIR, plate_filename)
            cv2.imwrite(plate_path, plate_img)

            # 保存带框整帧图
            frame_filename = f"{file_time}_{safe_text}_frame.jpg"
            frame_path = os.path.join(FRAME_DIR, frame_filename)
            cv2.imwrite(frame_path, draw_frame)

            # 追加保存历史
            save_result_to_csv(CSV_PATH, [
                now_str,
                frame_index,
                current_text,
                round(current_det_score, 4),
                round(current_rec_score, 4),
                x1,
                y1,
                x2,
                y2,
                plate_path,
                frame_path
            ])

            # 覆盖保存最新结果
            save_latest_result_to_json(JSON_PATH, {
                "time": now_str,
                "frame_index": frame_index,
                "plate_text": current_text,
                "det_score": round(current_det_score, 4),
                "rec_score": round(current_rec_score, 4),
                "bbox": [x1, y1, x2, y2],
                "plate_image": plate_path,
                "frame_image": frame_path
            })

            print(f"已保存识别结果: {current_text}")

            last_saved_text = current_text
            last_save_time = now_ts

    # FPS统计
    fps_counter += 1
    if fps_counter >= 30:
        now = time.time()
        show_fps = fps_counter / max(now - fps_start_time, 1e-6)
        fps_counter = 0
        fps_start_time = now

    cv2.putText(
        draw_frame,
        f"FPS:{show_fps:.1f}  DET:{DETECT_INTERVAL}  OCR:{OCR_INTERVAL}  LOST:{lost_count}",
        (20, 35),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.9,
        (0, 255, 0),
        2
    )

    # 只在显示时缩放
    show_frame = cv2.resize(
        draw_frame,
        dsize=None,
        fx=DISPLAY_SCALE,
        fy=DISPLAY_SCALE,
        interpolation=cv2.INTER_LINEAR
    )

    cv2.imshow("YOLO Plate Detection", show_frame)

    if cv2.waitKey(1) & 0xFF == ord("q"):
        break

cap.release()
cv2.destroyAllWindows()
print("摄像头检测完成")
print(f"全部结果已保存到: {RESULT_DIR}")