# import os
# import cv2
# import imgaug.augmenters as iaa
#
# # Путь к папке с изображениями
# input_folder = os.getcwd()
# output_folder = os.path.join(os.getcwd(), "aug")
# os.makedirs(output_folder, exist_ok=True)
#
# # Создаем список аугментаций
# augmentations = iaa.Sequential([
#     iaa.Fliplr(0.5),  # Отражение по горизонтали с вероятностью 50%
#     iaa.Flipud(0.2),  # Отражение по вертикали с вероятностью 20%
#     iaa.Affine(rotate=(-20, 20)),  # Поворот на -20 до 20 градусов
#     iaa.Multiply((0.8, 1.2)),  # Изменение яркости (80% до 120%)
#     iaa.AdditiveGaussianNoise(scale=(10, 20)),  # Добавление шума
# ])
#
# # Найти все изображения TyrWarrior_*.jpg
# images = [f for f in os.listdir(input_folder) if f.startswith("TyrWarrior_") and f.endswith(".png")]
#
# # Выполнение аугментации для каждого изображения
# for img_name in images:
#     img_path = os.path.join(input_folder, img_name)
#     image = cv2.imread(img_path)
#
#     if image is None:
#         print(f"Не удалось загрузить изображение: {img_name}")
#         continue
#
#     # Применяем аугментации
#     augmented_images = augmentations(images=[image])
#
#     # Сохраняем результаты
#     for i, aug_img in enumerate(augmented_images):
#         output_path = os.path.join(output_folder, f"{img_name.split('.')[0]}_aug_{i+1}.png")
#         cv2.imwrite(output_path, aug_img)
#
# print("Аугментация завершена.")
import os
import cv2
import albumentations as A
from albumentations.core.composition import OneOf
from albumentations.core.transforms_interface import ImageOnlyTransform

# Создаем трансформации
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

print("Augmentation completed.")
