import os

DATASET_PATH = "dataset"
IMAGE_DIRS = ["images/train", "images/val"]
LABEL_DIRS = ["labels/train", "labels/val"]
VALID_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def check_dataset():
    errors = []

    for dir_path in IMAGE_DIRS + LABEL_DIRS:
        full_path = os.path.join(DATASET_PATH, dir_path)
        if not os.path.exists(full_path):
            errors.append(f"Directory missing: {full_path}")

    for image_dir, label_dir in zip(IMAGE_DIRS, LABEL_DIRS):
        image_path = os.path.join(DATASET_PATH, image_dir)
        label_path = os.path.join(DATASET_PATH, label_dir)

        if not os.path.exists(image_path) or not os.path.exists(label_path):
            continue

        image_files = [f for f in os.listdir(image_path) if os.path.splitext(f)[1].lower() in VALID_EXTENSIONS]
        label_files = [f for f in os.listdir(label_path) if f.endswith(".txt")]

        image_basenames = {os.path.splitext(f)[0] for f in image_files}
        label_basenames = {os.path.splitext(f)[0] for f in label_files}

        missing_labels = image_basenames - label_basenames
        if missing_labels:
            for missing in missing_labels:
                errors.append(f"Missing annotation for image: {os.path.join(image_path, missing)}")

        missing_images = label_basenames - image_basenames
        if missing_images:
            for missing in missing_images:
                errors.append(f"Missing image for annotation: {os.path.join(label_path, missing)}")

    return errors


if __name__ == "__main__":
    print("Checking dataset integrity...")
    errors = check_dataset()

    if errors:
        print("\nErrors found:")
        for error in errors:
            print(f"- {error}")
    else:
        print("\nDataset structure is correct!")
