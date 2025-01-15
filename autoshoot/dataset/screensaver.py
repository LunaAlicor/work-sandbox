import sys
import os
from PyQt5.QtWidgets import QApplication, QRubberBand, QMainWindow, QMenu, QAction
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QGuiApplication, QPixmap, QPainter, QScreen, QCursor
from pynput import keyboard
from PyQt5.QtWidgets import QApplication


class ScreenshotTool(QMainWindow):
    def __init__(self, screen, enemy_name):
        super().__init__()
        self.full_screenshot = screen.grabWindow(0)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowFullScreen)
        self.rubber_band = None
        self.start_pos = None
        self.enemy_name = enemy_name
        self.setStyleSheet("background: none;")
        self.pixmap = QPixmap(self.full_screenshot.size())
        self.pixmap.fill(Qt.transparent)
        painter = QPainter(self.pixmap)
        painter.drawPixmap(0, 0, self.full_screenshot)
        painter.end()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        painter.end()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
            self.rubber_band.setGeometry(QRect(self.start_pos, QSize()))
            self.rubber_band.show()

    def mouseMoveEvent(self, event):
        if self.rubber_band:
            self.rubber_band.setGeometry(QRect(self.start_pos, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton and self.rubber_band:
            rect = self.rubber_band.geometry()
            self.capture_screenshot(rect)
            self.rubber_band.hide()
            self.rubber_band = None
            self.close()

    def capture_full_screenshot(self):
        full_pixmap = self.full_screenshot

        base_name = self.enemy_name
        files_in_folder = os.listdir(os.getcwd())
        matching_files = [f for f in files_in_folder if f.startswith(base_name) and f.endswith(".png")]

        next_number = len(matching_files) + 1
        file_name = f"{base_name}_{next_number}.png"

        file_path = os.path.join(os.getcwd(), file_name)

        full_pixmap.save(file_path, "png")
        print(f"Полный Screenshot сохранён: {file_path}")

    def capture_screenshot(self, rect):
        cropped_pixmap = self.full_screenshot.copy(rect)
        base_name = self.enemy_name
        files_in_folder = os.listdir(os.getcwd())
        matching_files = [f for f in files_in_folder if f.startswith(base_name) and f.endswith(".png")]

        next_number = len(matching_files) + 1
        file_name = f"{base_name}_{next_number}.png"

        file_path = os.path.join(os.getcwd(), file_name)

        cropped_pixmap.save(file_path, "png")
        print(f"Screenshot сохранён: {file_path}")


def show_menu():
    pass


def get_current_screen():
    screen = QGuiApplication.screenAt(QCursor.pos())
    if not screen:
        screen = QGuiApplication.primaryScreen()
    return screen


def on_key_press(key):
    try:
        if key == keyboard.Key.insert:
            app = QApplication(sys.argv)
            screen = get_current_screen()
            screenshot_tool = ScreenshotTool(screen, "TyrWarrior")
            screenshot_tool.show()
            app.exec_()

        elif key == keyboard.Key.page_up:
            app = QApplication(sys.argv)
            screen = get_current_screen()
            screenshot_tool = ScreenshotTool(screen, "TyrWarrior")
            screenshot_tool.capture_full_screenshot()

        elif key == keyboard.Key.home:
            show_menu()

    except AttributeError:
        pass


if __name__ == "__main__":
    print("Чтобы сделать изображение, нужно нажать клавишу 'insert' и выделить область")
    print("Нажмите 'Home' для открытия меню")
    print("Нажмите 'Page Up' для захвата полного скриншота")
    with keyboard.Listener(on_press=on_key_press) as listener:
        listener.join()
