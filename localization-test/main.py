# -*- coding: utf-8 -*-

import sys
import os
import pyperclip
from PyQt5.QtWidgets import QApplication, QRubberBand, QMainWindow, QMenu, QAction
from PyQt5.QtCore import Qt, QRect, QSize
from PyQt5.QtGui import QGuiApplication, QPixmap, QPainter, QColor, QCursor
from pynput import keyboard
import pytesseract
from PIL import Image
import difflib
from colorama import Fore, init

init(autoreset=True)

LANGUAGES = {
    "ENGLISH": "eng",
    "RUSSIAN": "rus",
    "RUSSIAN+ENGLISH": "rus+eng",
    "GERMAN": "deu",
    "SPANISH": "spa",
    "SPANISH LATIN AMERICA": "spa",
    "ITALIAN": "ita",
    "FRENCH": "fra",
    "BRAZILIAN PORTUGUESE": "por",
    "POLISH": "pol",
    "CZECH": "ces",
    "UKRAINIAN": "ukr",
    "TURKISH": "tur",
    "CHINESE TRADITIONAL": "chi_tra",
    "CHINESE SIMPLIFIED": "chi_sim",
    "KOREAN": "kor",
    "JAPANESE": "jpn",
    "THAI": "tha",
}

current_language = "eng"


class ScreenshotTool(QMainWindow):
    def __init__(self, screen):
        """
        Initialize the screenshot tool.

        :param screen: The screen object to capture a full screenshot.
        """
        super().__init__()
        self.full_screenshot = screen.grabWindow(0)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setWindowState(Qt.WindowFullScreen)
        self.rubber_band = None
        self.start_pos = None
        self.overlay_color = QColor(255, 0, 0)
        self.setStyleSheet("background: none;")
        self.pixmap = QPixmap(self.full_screenshot.size())
        self.pixmap.fill(Qt.transparent)
        painter = QPainter(self.pixmap)
        painter.drawPixmap(0, 0, self.full_screenshot)
        painter.end()
        self.selected_rect = None

    def paintEvent(self, event):
        """
        Handle paint events to render the overlay and screenshot.

        :param event: The paint event object.
        """
        painter = QPainter(self)
        painter.drawPixmap(0, 0, self.pixmap)
        if self.selected_rect:
            painter.setPen(Qt.NoPen)
            painter.setBrush(self.overlay_color)
            painter.drawRect(self.selected_rect)
        painter.end()

    def mousePressEvent(self, event):
        """
        Handle mouse press events to start selection.

        :param event: The mouse event object.
        """
        if event.button() == Qt.LeftButton:
            self.start_pos = event.pos()
            self.rubber_band = QRubberBand(QRubberBand.Rectangle, self)
            self.rubber_band.setGeometry(QRect(self.start_pos, QSize()))
            self.rubber_band.show()

    def mouseMoveEvent(self, event):
        """
        Handle mouse move events to adjust the selection rectangle.

        :param event: The mouse event object.
        """
        if self.rubber_band:
            self.rubber_band.setGeometry(QRect(self.start_pos, event.pos()).normalized())

    def mouseReleaseEvent(self, event):
        """
        Handle mouse release events to finalize the selection and capture the screenshot.

        :param event: The mouse event object.
        """
        if event.button() == Qt.LeftButton and self.rubber_band:
            rect = self.rubber_band.geometry()
            self.selected_rect = rect
            self.capture_screenshot(rect)
            self.rubber_band.hide()
            self.rubber_band = None
            self.close()

    def capture_screenshot(self, rect):
        """
        Capture a cropped screenshot based on the selected rectangle.

        :param rect: The QRect object representing the selection.
        """
        cropped_pixmap = self.full_screenshot.copy(rect)
        cropped_pixmap.save("screenshot.png", "png")
        print("Screenshot сохранен: screenshot.png")
        self.extract_text_from_image(cropped_pixmap)

    def extract_text_from_image(self, pixmap):
        """
        Extract text from the cropped screenshot using OCR.

        :param pixmap: The QPixmap object of the cropped screenshot.
        """
        global current_language
        image = pixmap.toImage()
        image.save("temp_image.png")
        pil_image = Image.open("temp_image.png")
        text = pytesseract.image_to_string(pil_image, lang=current_language)
        print("Распознанный текст:")
        print(text)
        pyperclip.copy(text)
        self.compare_with_file(text)

    def compare_with_file(self, extracted_text):
        """
        Compare the extracted text with phrases in a file and display the best match.

        :param extracted_text: The text extracted from the image.
        """
        with open('text.txt', 'r', encoding='utf-8') as f:
            phrases = f.readlines()
        extracted_text = extracted_text.strip().lower()
        phrases = [phrase.strip().lower() for phrase in phrases]
        best_match = ""
        best_ratio = 0
        for phrase in phrases:
            ratio = difflib.SequenceMatcher(None, extracted_text, phrase).ratio()
            if ratio > best_ratio:
                best_ratio = ratio
                best_match = phrase
        print(f"Лучшее совпадение: {best_match} с коэффициентом совпадения {best_ratio * 100:.2f}%")
        if best_ratio > 0.9:
            print(Fore.GREEN + f"Совпадение > 90%: {best_match} ({best_ratio * 100:.2f}%)")
            self.overlay_color = QColor(0, 255, 0)
        else:
            print(Fore.RED + f"Совпадение < 90%: {best_match} ({best_ratio * 100:.2f}%)")
            self.overlay_color = QColor(255, 0, 0)
        self.repaint()


def get_current_screen():
    """
    Retrieve the current screen where the cursor is located.

    :return: The screen object.
    """
    screen = QGuiApplication.screenAt(QCursor.pos())
    if not screen:
        screen = QGuiApplication.primaryScreen()
    return screen


def show_menu():
    """
    Display a context menu for changing the language or closing the application.
    """
    global current_language
    app = QApplication(sys.argv)
    menu = QMenu()
    language_menu = QMenu("Сменить язык", menu)
    for language_name, language_code in LANGUAGES.items():
        language_action = QAction(language_name, language_menu)

        def set_language(language_name=language_name, code=language_code):
            global current_language
            current_language = code
            print(f"Язык изменен на {language_name} ({code})")

        language_action.triggered.connect(
            lambda checked, name=language_name, code=language_code: set_language(name, code))
        language_menu.addAction(language_action)
    close_program_action = QAction("Закрыть программу", menu)

    def close_program():
        print("Программа закрыта")
        sys.exit()

    close_program_action.triggered.connect(close_program)
    menu.addMenu(language_menu)
    menu.addAction(close_program_action)
    cursor_pos = QCursor.pos()
    menu.exec_(cursor_pos)


def on_key_press(key):
    """
    Handle keyboard key press events to trigger screenshot or menu.

    :param key: The key object pressed by the user.
    """
    try:
        if key == keyboard.Key.insert:
            app = QApplication(sys.argv)
            screen = get_current_screen()
            screenshot_tool = ScreenshotTool(screen)
            screenshot_tool.show()
            app.exec_()
        elif key == keyboard.Key.home:
            show_menu()
    except AttributeError:
        pass


if __name__ == "__main__":
    """
    Main entry point of the application.
    """
    print("Чтобы извлечь текст с изображения, нужно нажать клавишу 'insert' и выделить область")
    print("Нажмите 'Home' для открытия меню")
    pytesseract.pytesseract.tesseract_cmd = os.path.join(os.getcwd(), "tess", "tesseract.exe")
    with keyboard.Listener(on_press=on_key_press) as listener:
        listener.join()
