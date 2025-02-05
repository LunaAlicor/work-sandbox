import cv2
import numpy as np
import keyboard
import time
import os
from colorama import Fore, init
import sys
import pyautogui
import datetime

init(autoreset=True)


def timer(func):
    def wrapped(*args, **kwargs):
        start = datetime.datetime.now()
        answer = func(*args, **kwargs)
        res_time = datetime.datetime.now() - start
        print(f"Время загрузки: {res_time}")
        return answer
    return wrapped


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
    press_key("down", 2)
    press_key("enter", 2)


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
        time.sleep(1)
        wait_loading(episode_num, chapter_index+1, f"{episode_name} - {chapter_name}")
        time.sleep(1)
        skip_intro()
        time.sleep(1)
        back_to_menu()
        time.sleep(0.5)
        wait_main_menu()
        time.sleep(0.5)


if __name__ == "__main__":
    grabber = GrabberOBS()
    grabber.device.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
    grabber.device.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
    cv2.namedWindow("result", cv2.WINDOW_NORMAL)
    time.sleep(10)
    LOADSCREENS_FOLDER = os.path.join(os.getcwd(), "loadingscreens")

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
                "эпизод 8: финикс": {
                    "обходной путь": False,
                    "запертые в темпе": False,
                    "борьба за дом": False,
                },
                "эпизод 9: вегас": {
                    "плохая раздача": False,
                    "вынужденные ставки": False,
                    "финальный стол": False,
                },
            }
        }
    }
    while True:
        if keyboard.is_pressed('home'):
            break

    for episode_index, (episode_name, chapters) in enumerate(check_tree["кампания"]["не в сети"].items(), start=1):
        play_episode(episode_index, episode_name, chapters)

    grabber.release()
