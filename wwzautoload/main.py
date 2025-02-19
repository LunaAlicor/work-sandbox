import difflib

import cv2
import numpy as np
import keyboard
import time
import os
from colorama import Fore, init
import sys
import pyautogui
import datetime
import win32gui
from pywinauto import Application

init(autoreset=True)


class CrashError(Exception):
    pass


class GrabberOBS:
    def __init__(self, capture_device=0):
        self.device = cv2.VideoCapture(capture_device)
        if not self.device.isOpened():
            raise ValueError("Не удалось открыть устройство захвата видео.")

    def get_image(self, grab_area=None):
        ret, frame = self.device.read()
        if not ret:
            raise RuntimeError("Не удалось получить кадр с устройства.")
        if grab_area:
            x, y, w, h = grab_area
            frame = frame[y:y + h, x:x + w]
        return frame

    def release(self):
        if self.device:
            self.device.release()


def get_all_windows():
    windows = []

    def enum_handler(hwnd, _):
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if title:
                windows.append(title)
    win32gui.EnumWindows(enum_handler, None)
    return windows


def find_closest_window(target_name):
    windows = get_all_windows()
    matches = difflib.get_close_matches(target_name, windows, n=1, cutoff=0.5)
    return matches[0] if matches else None


def get_window_bbox(window_name):
    best_match = find_closest_window(window_name)
    if best_match:
        hwnd = win32gui.FindWindow(None, best_match)
        if hwnd:
            rect = win32gui.GetWindowRect(hwnd)
            return {
                "top": rect[1], "left": rect[0],
                "width": rect[2] - rect[0], "height": rect[3] - rect[1]
            }
    return None


def capture_window(window_name):
    bbox = get_window_bbox(window_name)
    if bbox:
        return np.array(pyautogui.screenshot(region=(
            bbox["left"], bbox["top"], bbox["width"], bbox["height"]
        )))
    return None


def send_key_to_wwz(key, window_name):
    try:
        best_match = find_closest_window(window_name)
        if not best_match:
            print(f"Окно, похожее на '{window_name}', не найдено.")
            return
        app = Application().connect(title=best_match)
        wwz_window = app.window(title=best_match)
        wwz_window.send_keystrokes(key)
    except Exception as e:
        print(f"Ошибка отправки клавиши: {e}")


def detect_crash_screen(screen):
    crash_template = cv2.imread('crash1.png', 0)
    screen_gray = cv2.cvtColor(screen, cv2.COLOR_BGR2GRAY)
    res = cv2.matchTemplate(screen_gray, crash_template, cv2.TM_CCOEFF_NORMED)
    threshold = 0.8
    loc = np.where(res >= threshold)
    if np.any(loc):
        return True
    return False


def timer(func):
    def wrapped(*args, **kwargs):
        start = datetime.datetime.now()
        answer = func(*args, **kwargs)
        res_time = datetime.datetime.now() - start
        print(f"Время загрузки: {res_time}")
        return answer
    return wrapped


def press_enter():
    keyboard.send('enter')
    time.sleep(0.5)
    keyboard.release('enter')
    time.sleep(0.5)


def press_down(number):
    for _ in range(number):
        keyboard.press('down')
        time.sleep(0.5)
        keyboard.release('down')
    time.sleep(0.5)


def press_key(key, times=1, delay=0.5):
    for _ in range(times):
        keyboard.press_and_release(key)
        time.sleep(delay)


def navigate_to_episode_menu():
    press_enter()
    time.sleep(0.5)
    press_down(2)
    time.sleep(0.5)
    press_enter()
    time.sleep(1)


def mse(image1, image2):
    err = np.sum((image1.astype("float") - image2.astype("float")) ** 2)
    err /= float(image1.shape[0] * image1.shape[1])
    return err


def psnr(image1, image2):
    mse_value = mse(image1, image2)
    if mse_value == 0:
        return 100
    max_pixel = 255.0
    return 20 * np.log10(max_pixel / np.sqrt(mse_value))


def compare_psnr(image1, image2_path):
    img1 = cv2.cvtColor(image1, cv2.COLOR_BGR2GRAY) if len(image1.shape) == 3 else image1
    img2 = cv2.imread(image2_path, cv2.IMREAD_GRAYSCALE)
    if img2 is None:
        raise ValueError(f"Не удалось загрузить изображение: {image2_path}")
    img1 = cv2.resize(img1, (img2.shape[1], img2.shape[0]))
    return psnr(img1, img2)


@timer
def wait_loading(episode_num, chapter_num, scene_name):
    similarity_reached = False
    image_filename = f"ep{episode_num}g{chapter_num}.png"
    image_path = os.path.join(LOADSCREENS_FOLDER, image_filename)

    while True:
        if keyboard.is_pressed("end"):
            print("Выход из программы.")
            break
        # screen = grabber.get_image()
        screen = np.array(pyautogui.screenshot())
        if detect_crash_screen(screen):
            print("\n", Fore.RED + scene_name)
            raise CrashError
        else:
            similarity = compare_psnr(screen, image_path)
            if similarity >= 20:
                similarity_reached = True
            if similarity_reached and similarity < 20:
                print("\n", Fore.GREEN + scene_name)
                break
            sys.stdout.write(f"\rСходство: {similarity}%")
            sys.stdout.flush()
    print()


def wait_main_menu():
    similarity_reached = False
    image_filename = f"back.png"
    image_path = os.path.join(LOADSCREENS_FOLDER, image_filename)

    while True:
        if keyboard.is_pressed("end"):
            print("Выход из программы.")
            break
        # screen = grabber.get_image()
        screen = np.array(pyautogui.screenshot())
        similarity = compare_psnr(screen, image_path)
        if similarity >= 20:

            similarity_reached = True
        if similarity_reached and similarity < 20:
            break
    time.sleep(1)


def skip_intro():
    keyboard.press("enter")
    time.sleep(5)
    keyboard.release("enter")


def back_to_menu():
    press_key("esc")
    time.sleep(0.5)
    press_key("down", 2)
    time.sleep(0.5)
    press_key("enter", 2)
    time.sleep(0.5)


def play_episode(episode_num, episode_name, chapters):
    time.sleep(1)
    for chapter_index, (chapter_name, _) in enumerate(chapters.items(), start=0):
        navigate_to_episode_menu()
        press_key("down", episode_num)
        time.sleep(1)
        press_key("enter", 1)
        time.sleep(0.5)
        press_key("down", chapter_index)
        time.sleep(1)
        press_key("enter", 1)
        time.sleep(1)
        press_key("enter", 1)
        time.sleep(5)
        wait_loading(episode_num, chapter_index+1, f"{episode_name} - {chapter_name}")
        time.sleep(1)
        skip_intro()
        time.sleep(1)
        back_to_menu()
        time.sleep(0.5)
        wait_main_menu()
        time.sleep(0.5)


if __name__ == "__main__":
    # grabber = GrabberOBS()
    # grabber.device.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    # grabber.device.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    # cv2.namedWindow("result", cv2.WINDOW_NORMAL)
    time.sleep(5)
    LOADSCREENS_FOLDER = os.path.join(os.getcwd(), "loadingscreens")
    print("Можно начинать")
    win_name = ""

    check_tree = {
        "кампания": {
            "не в сети": {
                "эпизод 1: нью-йорк": {
                    "сошествие": False,
                    "туннельное зрение": False,
                    "огонь, вода, и медные трубы": False,
                    "Против течения": False,
                },
                "эпизод 2: иерусалим": {
                    "утечка мозгов": False,
                    "мертвое, мертвое море": False,
                    "техподдержка": False,
                },
                "эпизод 3: москва": {
                    "знак свыше": False,
                    "ключи от города": False,
                    "нервы на пределе": False,
                    "воскрешение": False,
                },
                "эпизод 4: токио": {
                    "заходящее солнце": False,
                    "последний рейс": False,
                    "билет в одну сторону": False,
                },
                "эпизод 5: марсель": {
                    "французское сопротивление": False,
                    "ракетный расчет": False,
                    "последний оплот": False,
                },
                "эпизод 6: рим": {
                    "святая земля": False,
                    "призыв к оружию": False,
                    "последний рывок": False,
                },
                "эпизод 7: камчатка": {
                    "зимняя стужа": False,
                    "гудящие провода": False,
                    "атомный альянс": False,
                },
            }
        }
    }
    while True:
        if keyboard.is_pressed('home'):
            break
    start = datetime.datetime.now()
    try:
        for episode_index, (episode_name, chapters) in enumerate(check_tree["кампания"]["не в сети"].items(), start=1):
            play_episode(episode_index, episode_name, chapters)
        # grabber.release()
        end = datetime.datetime.now()
    except CrashError:
        end = datetime.datetime.now()
        print("Произошел crash")
    finally:
        if not end:
            end = datetime.datetime.now()
        print(f"Общее время проверки {end-start}")
        while True:
            if keyboard.is_pressed("end"):
                break
