import cv2
import torch
from torchvision import transforms
from PIL import Image
import numpy as np
import os
from ultralytics import YOLO
import time


class AimBot:
    def __init__(self, confidence_threshold=0.8):
        """

        """
        self.confidence_threshold = confidence_threshold

    def select_target(self, detections):
        """

        """
        valid_detections = [d for d in detections if d['confidence'] >= self.confidence_threshold]

        if not valid_detections:
            return None

        # Найти самый большой прямоугольник по площади
        largest_detection = max(valid_detections, key=lambda d: (d['coordinates'][2] - d['coordinates'][0]) * (d['coordinates'][3] - d['coordinates'][1]))

        x1, y1, x2, y2 = largest_detection['coordinates']
        center_x = int((x1 + x2) / 2)
        center_y = int((y1 + y2) / 2)

        return {
            "coordinates": largest_detection['coordinates'],
            "center": (center_x, center_y),
            "label": largest_detection['label'],
            "confidence": largest_detection['confidence']
        }


model = YOLO("runs/detect/yolo11_custom_training5/weights/best.pt")


class GrabberOBS:
    type = "obs_vc"
    device = None
    model = None
    transform = None

    def obs_vc_init(self, capture_device=0, model=None, transform=None):
        self.device = cv2.VideoCapture(capture_device)
        if not self.device.isOpened():
            raise ValueError("Не удалось открыть устройство захвата видео.")

        self.model = model
        if self.model:
            self.model.eval()

        self.transform = transform or transforms.Compose([
            transforms.Resize((224, 224)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.5], std=[0.5])
        ])

    def get_image(self, grab_area=None):
        ret, frame = self.device.read()
        if not ret:
            raise RuntimeError("Не удалось получить кадр с устройства.")

        if grab_area:
            x, y, w, h = grab_area
            frame = frame[y:y + h, x:x + w]

        return frame

    def predict(self, frame):
        if not self.model:
            raise ValueError("Модель не инициализирована.")

        results = self.model(frame)

        detections = []
        for result in results:
            for box in result.boxes:
                x1, y1, x2, y2 = box.xyxy[0].tolist()
                confidence = box.conf[0].item()
                cls = int(box.cls[0].item())
                label = self.model.names[cls]
                detections.append({
                    "coordinates": (x1, y1, x2, y2),
                    "confidence": confidence,
                    "class_id": cls,
                    "label": label
                })

        return detections

    def release(self):
        if self.device:
            self.device.release()


grabber = GrabberOBS()
aimbot = AimBot(confidence_threshold=0.8)

prev_frame_time = 0
new_frame_time = 0
grabber.obs_vc_init(capture_device=0, model=model)

try:
    while True:
        frame = grabber.get_image()

        new_frame_time = time.time()
        fps = 1 / (new_frame_time - prev_frame_time) if prev_frame_time else 0
        prev_frame_time = new_frame_time
        fps_text = f"FPS: {int(fps)}"
        cv2.putText(frame, fps_text, (10, 60), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0), 2, cv2.LINE_AA)

        results = grabber.predict(frame)
        target = aimbot.select_target(results)

        if target:
            center_x, center_y = target["center"]
            cv2.circle(frame, (center_x, center_y), 5, (0, 0, 255), -1)
            cv2.putText(frame, f"Target: {target['label']} {target['confidence']:.2f}",
                        (center_x + 10, center_y - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)

        for detection in results:
            x1, y1, x2, y2 = detection["coordinates"]
            confidence = detection["confidence"]
            label = detection["label"]

            cv2.rectangle(frame, (int(x1), int(y1)), (int(x2), int(y2)), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} {confidence:.2f}",
                        (int(x1), int(y1) - 10),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        cv2.imshow("Inference", frame)
        if cv2.waitKey(1) & 0xFF == ord('o'):
            break
finally:
    grabber.release()
    cv2.destroyAllWindows()
