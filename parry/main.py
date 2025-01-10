import cv2
import numpy as np
import pyautogui
from typing import Sequence, List
import keyboard
import time
import os
import threading

TEMPLATE_FOLDER = "templates/"
THRESHOLD = 0.4
KEY_TO_PRESS = "c"
SLEEP_INTERVAL = 0.03
SAVE_PATH = "matches/"
color_setting_running = False


class GrabberOBS:
    type = "obs_vc"
    device = None

    def obs_vc_init(self, capture_device=0):
        """
        Инициализирует захват видео с устройства.
        По умолчанию используется устройство с индексом 0.
        """
        self.device = cv2.VideoCapture(capture_device)
        if not self.device.isOpened():
            raise ValueError("Не удалось открыть устройство захвата видео.")

    def get_image(self, grab_area=None):
        """
        Захватывает кадр с устройства.

        Args:
            grab_area (tuple, optional): Область захвата (x, y, width, height).
                                         Если None, возвращается полный кадр.
        Returns:
            numpy.ndarray: Захваченный кадр.
        """
        ret, frame = self.device.read()
        if not ret:
            raise RuntimeError("Не удалось получить кадр с устройства.")

        if grab_area:
            x, y, w, h = grab_area
            frame = frame[y:y+h, x:x+w]

        return frame

    def release(self):
        """
        Освобождает устройство захвата.
        """
        if self.device:
            self.device.release()



# def capture_screen() -> np.ndarray:
#     """
#     Captures a screenshot of the screen and resize it.
#
#     Returns:
#         numpy.ndarray: An array representing the screen image.
#     """
#     screenshot = pyautogui.screenshot()
#     frame = np.array(screenshot)
#     frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
#     frame = cv2.resize(frame, (frame.shape[1] // 2, frame.shape[0] // 2))
#     return frame


def isolate_color(image: np.ndarray, h_min: np.ndarray, h_max: np.ndarray) -> np.ndarray:
    """
    Isolates specific color ranges in the given image using HSV color space.

    Parameters:
        image (numpy.ndarray): Input image.
        h_min (numpy.ndarray): Lower HSV boundary.
        h_max (numpy.ndarray): Upper HSV boundary.

    Returns:
        numpy.ndarray: Image with only the specified color range visible.
    """
    hsv_image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
    mask = cv2.inRange(hsv_image, h_min, h_max)
    result = cv2.bitwise_and(image, image, mask=mask)
    return result


def color_setting() -> None:
    """
    Launches a GUI window for dynamically setting HSV color ranges using sliders.
    Updates global variables for color range.
    """
    global color_setting_running, h_min, h_max
    color_setting_running = True

    def nothing(*arg):
        pass

    cv2.namedWindow("settings")
    cv2.createTrackbar('h1', 'settings', 0, 179, nothing)
    cv2.createTrackbar('s1', 'settings', 0, 255, nothing)
    cv2.createTrackbar('v1', 'settings', 0, 255, nothing)
    cv2.createTrackbar('h2', 'settings', 179, 179, nothing)
    cv2.createTrackbar('s2', 'settings', 255, 255, nothing)
    cv2.createTrackbar('v2', 'settings', 255, 255, nothing)

    while True:
        if not color_setting_running:
            break

        h1 = cv2.getTrackbarPos('h1', 'settings')
        s1 = cv2.getTrackbarPos('s1', 'settings')
        v1 = cv2.getTrackbarPos('v1', 'settings')
        h2 = cv2.getTrackbarPos('h2', 'settings')
        s2 = cv2.getTrackbarPos('s2', 'settings')
        v2 = cv2.getTrackbarPos('v2', 'settings')

        h_min = np.array([h1, s1, v1], np.uint8)
        h_max = np.array([h2, s2, v2], np.uint8)

        cv2.waitKey(1)

    cv2.destroyWindow("settings")


def start_color_setting() -> None:
    """
    Starts the color setting process in a separate thread if not already running.
    """
    global color_setting_running
    if not color_setting_running:
        threading.Thread(target=color_setting, daemon=True).start()


def load_templates() -> List[np.ndarray]:
    """
    Loads all templates from the specified folder as grayscale images.

    Returns:
        List[numpy.ndarray]: List of loaded template images.

    Raises:
        FileNotFoundError: If no valid templates are found in the folder.
    """
    templates = []
    for filename in os.listdir(TEMPLATE_FOLDER):
        if filename.startswith("temp") and filename.endswith(".jpg"):
            path = os.path.join(TEMPLATE_FOLDER, filename)
            template = cv2.imread(path, cv2.IMREAD_GRAYSCALE)
            if template is not None:
                templates.append(template)
    if not templates:
        raise FileNotFoundError(f"No valid templates found in folder: {TEMPLATE_FOLDER}.")
    return templates


def match_template(screen: np.ndarray, template: np.ndarray) -> tuple[bool, Sequence[int], float]:
    """
    Matches a template against a screen image using template matching.

    Parameters:
        screen (numpy.ndarray): Grayscale screen image.
        template (numpy.ndarray): Grayscale template image.

    Returns:
        tuple:
            bool: True if a match is found above the threshold, False otherwise.
            tuple[int, int]: Top-left coordinates of the detected match.
            float: Confidence score of the match.
    """
    try:
        gray_screen = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        gpu_screen = cv2.cuda_GpuMat()
        gpu_screen.upload(gray_screen)

        gpu_template = cv2.cuda_GpuMat()
        gpu_template.upload(template)

        result = cv2.cuda.createTemplateMatching(cv2.CV_32F).match(gpu_screen, gpu_template)
        result_host = result.download()
        _, max_val, _, max_loc = cv2.minMaxLoc(result_host)
        match = max_val >= THRESHOLD
        return match, max_loc, max_val
    except Exception:
        gray_screen = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
        result = cv2.matchTemplate(gray_screen, template, cv2.TM_CCOEFF_NORMED)
        _, max_val, _, max_loc = cv2.minMaxLoc(result)
        match = max_val >= THRESHOLD
        return match, max_loc, max_val


def save_matched_area(screen: np.ndarray, location: Sequence[int], template_shape: tuple[int, int], counter: int) -> None:
    """
    Saves the region of the screen corresponding to a detected match.

    Parameters:
        screen (numpy.ndarray): Grayscale screen image.
        location (tuple[int, int]): Top-left coordinates of the detected match.
        template_shape (tuple[int, int]): Shape of the template (height, width).
        counter (int): Unique identifier for saving multiple matches.
    """
    h, w = template_shape
    x, y = location
    matched_area = screen[y:y+h, x:x+w]
    os.makedirs(SAVE_PATH, exist_ok=True)
    filename = f"{SAVE_PATH}match_{counter}.png"
    cv2.imwrite(filename, matched_area)
    print(f"Matched area saved: {filename}")


if __name__ == '__main__':
    grabber = GrabberOBS()
    try:
        grabber.obs_vc_init(capture_device=0)
        grabber.device.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
        grabber.device.set(cv2.CAP_PROP_FRAME_HEIGHT, 720 )

        cv2.namedWindow("result", cv2.WINDOW_NORMAL)
        templates = load_templates()
        print(f"Loaded {len(templates)} templates. Starting screen monitoring...")
        time.sleep(2)
        h_min = np.array([82, 70, 144])
        h_max = np.array([133, 255, 255])
        counter = 0

        while True:
            if keyboard.is_pressed("end"):
                print("Terminating on user request ('end' key pressed).")
                break
            elif keyboard.is_pressed("home"):
                start_color_setting()

            img = grabber.get_image()
            blue_only = isolate_color(img, h_min, h_max)

            for idx, template in enumerate(templates):
                match, location, max_val = match_template(blue_only, template)
                if match:
                    counter += 1
                    print(f"Match {counter} found with template {idx + 1} (confidence: {max_val:.2f})")
                    save_matched_area(blue_only, location, template.shape, counter)
                    keyboard.press_and_release(KEY_TO_PRESS)
                    time.sleep(1)
                    break
            else:
                time.sleep(SLEEP_INTERVAL)

            cv2.imshow("result", blue_only)
            ch = cv2.waitKey(1)
            if ch == 27:
                break

        color_setting_running = False
        cv2.destroyAllWindows()
    finally:
        grabber.release()
        cv2.destroyAllWindows()
