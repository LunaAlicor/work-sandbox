import os
import cv2
import albumentations as A
from albumentations.core.composition import OneOf
from albumentations.core.transforms_interface import ImageOnlyTransform

transform = A.Compose([
    A.HorizontalFlip(p=0.5),
    A.VerticalFlip(p=0.2),
    A.RandomRotate90(),
    A.RandomBrightnessContrast(brightness_limit=0.2, contrast_limit=0.2, p=0.5),
    A.GaussNoise(p=0.3),
])

input_folder = os.getcwd()
output_folder = os.path.join(os.getcwd(), "aug")
os.makedirs(output_folder, exist_ok=True)

for img_name in os.listdir(input_folder):
    if img_name.endswith(".png"):
        img_path = os.path.join(input_folder, img_name)
        image = cv2.imread(img_path)
        if image is None:
            print(f"Could not read {img_name}")
            continue

        augmented = transform(image=image)["image"]
        output_path = os.path.join(output_folder, f"aug_{img_name}")
        cv2.imwrite(output_path, augmented)

print("Аугментация завершена.")
