import cv2
import os
from pathlib import Path
from ultralytics import YOLO

model = YOLO("runs/detect/yolo11_custom_training5/weights/best.pt")

input_folder = Path("testvideo")
output_folder = Path("autodata")
output_folder.mkdir(parents=True, exist_ok=True)

base_name = "AutoTyrWarriorval"
conf_threshold = 0.7


video_files = list(input_folder.glob("*.mp4"))

for video_file in video_files:
    cap = cv2.VideoCapture(str(video_file))
    files_in_folder = os.listdir(os.path.join(os.getcwd(), "autodata"))
    matching_files = [f for f in files_in_folder if f.startswith(base_name) and f.endswith(".png")]

    next_number = len(matching_files) + 1
    frame_count = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        results = model(frame)

        detections = results[0].boxes

        valid_annotations = False
        for det in detections:
            conf = det.conf[0].item()

            if conf >= conf_threshold:

                x1, y1, w, h = det.xywh[0][:4]
                x1, y1, w, h = x1.item(), y1.item(), w.item(), h.item()

                x_center = x1 / frame.shape[1]
                y_center = y1 / frame.shape[0]
                width = w / frame.shape[1]
                height = h / frame.shape[0]

                if width > 0 and height > 0 and 0 <= x_center <= 1 and 0 <= y_center <= 1:
                    yolo_annotation = f"{int(det.cls[0].item())} {x_center:.6f} {y_center:.6f} {width:.6f} {height:.6f}\n"

                    annotation_file = output_folder / f"{base_name}_{frame_count}.txt"
                    with open(annotation_file, "a") as f:
                        f.write(yolo_annotation)
                    valid_annotations = True

        if valid_annotations:
            output_image_path = output_folder / f"{base_name}_{frame_count}.png"
            cv2.imwrite(str(output_image_path), frame)
            frame_count += 1

    cap.release()

print("Обработка завершена.")
