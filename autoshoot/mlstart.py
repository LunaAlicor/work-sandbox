from ultralytics import YOLO


def train_yolo_model():

    model = YOLO('yolo11n.pt')

    model.train(
        data='dataset.yaml',
        epochs=100,
        imgsz=1024,  # 640
        batch=16,  # 16
        name='yolo11_custom_training',
        device=0
    )


if __name__ == "__main__":
    train_yolo_model()
