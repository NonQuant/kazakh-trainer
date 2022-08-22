# подключения к необходимым библиотекам
import sqlite3
import sys
import time
import csv
import datetime
from random import choice, randint
from design.project import Ui_MainWindow
from design.res_dialog import Ui_Dialog
from design.recordings_window import Ui_Form
from PyQt5.QtWidgets import QDialog, QInputDialog, QMessageBox
from PyQt5.QtWidgets import QApplication, QMainWindow, QWidget, QTableWidgetItem
from PyQt5.QtCore import QTimer, Qt
from PyQt5 import QtCore, QtWidgets, QtGui
from PyQt5.QtGui import QPixmap
from converter import convert_to_lat

# адаптация к экранам с высоким разрешением (HiRes)
if hasattr(QtCore.Qt, 'AA_EnableHighDpiScaling'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_EnableHighDpiScaling, True)

if hasattr(QtCore.Qt, 'AA_UseHighDpiPixmaps'):
    QtWidgets.QApplication.setAttribute(QtCore.Qt.AA_UseHighDpiPixmaps, True)

# константы cc3c2f FEDB39
DATABASE = "data\\trainer_db.db"

# correct, incorrect, main text, highlighting, background
DARK = ["#0CF25D", "#D92525", "#97adac", "#02ccdb", "#383A3B"]

LIGHT = ["#2ac780", "#FA1010", "#000000", "#7D77F6", "#FFFFFF"]

GRADIENT = ["#FFA900", "#DD4A48", "#F7E2E2", "#F7FA86", "#212324"]


def get_pixmap(theme):
    if theme == "dark":
        return QPixmap("data\\dark.jpeg")
    if theme == "gradient":
        return QPixmap("data\\gradient.jpg")
    return QPixmap("data\\light.png")


class RecordingsWindow(QWidget, Ui_Form):
    def __init__(self, user, theme):
        super().__init__()  # конструктор родительского класса
        # Вызываем метод для загрузки интерфейса из класса Ui_MainWindow,
        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon('data\\keyboard.png'))  # изменение иконки приложения

        # связываемся с БД
        self.con = sqlite3.connect(DATABASE)

        self.user = user

        # столбцы в БД и заголовки для отображаемой таблицы
        self.titles = ['Дата', 'Текст', 'Режим', 'Время', 'Скорость печати']
        self.columns = ["record_id", 'data', 'text_id', 'difficulty_id', 'time', 'typing_speed']
        
        self.all_ids = []

        self.change_theme(theme)  # устанавливаем тему
        self.username_label.setText(self.user)  # устанавливаем пользователя
        self.username_label.setAttribute(Qt.WA_NoSystemBackground)
        self.average_result_label.setAttribute(Qt.WA_NoSystemBackground)
        self.load_table()  # заргужаем таблицу

        # связываем кнопки с функциями
        self.delete_btn.clicked.connect(self.delete_elem)

    def load_table(self):
        # Создание курсора
        cur = self.con.cursor()

        # получаем данные из бд путем запроса
        result = cur.execute(f"""
        SELECT {', '.join(self.columns)} FROM Recordings
            WHERE user_id=(
        SELECT user_id FROM Users WHERE nickname='{self.user}')
        """).fetchall()

        # устанавливаем имена столбцов и количество рядов, столбцов
        self.recordings_table.setColumnCount(len(self.titles))
        self.recordings_table.setHorizontalHeaderLabels(self.titles)
        self.recordings_table.setRowCount(len(result))

        avg_res = []  # переменная для среднего результата
        # перебираем элементы
        for i, row in enumerate(result):
            for j, col in enumerate(row):
                # подменяем элемент с id на его значение
                if self.columns[j] == "record_id":
                    self.all_ids.append(col)
                    print(f"adding elems{self.all_ids}")
                    continue
                elif self.columns[j] == 'text_id':
                    que = f"""
                    SELECT text FROM Texts
                        WHERE text_id={col}"""

                    col = cur.execute(que).fetchall()[0][0]

                elif self.columns[j] == 'difficulty_id':
                    que = f"""
                    SELECT mode FROM Difficults
                        WHERE difficulty_id={col}"""

                    col = cur.execute(que).fetchall()[0][0]
                    if col == "easy":
                        col = "Легкий"
                    if col == "normal":
                        col = "Средний"
                    if col == "hard":
                        col = "Сложный"

                elif self.columns[j] == "typing_speed":
                    avg_res.append(int(col))

                # загружаем элемент
                self.recordings_table.setItem(i, j - 1, QTableWidgetItem(str(col)))

        # делаем таблицу нередактируемой
        self.recordings_table.setEditTriggers(QtWidgets.QAbstractItemView.NoEditTriggers)

        # вывод среднего результата в окне
        if avg_res:
            self.average_result_label.setText(f"Средний результат: {round(sum(avg_res) / len(avg_res), 1)} cpm")
        else:
            self.average_result_label.setText(f"Еще нет записей")

    def delete_elem(self):
        # если пользователь ничего не выбрал, то вызвать ошибку
        if len(self.recordings_table.selectedItems()) == 0:
            error_message = QMessageBox(self)
            error_message.setIcon(QMessageBox.Critical)
            error_message.setText("Вы ничего не выбрали!")
            error_message.setInformativeText("Выберите строки для удаления")
            error_message.setWindowTitle("Удаление заисей отменена")
            error_message.exec_()
            return

        # Получаем список элементов без повторов и их id
        rows = list(set([i.row() for i in self.recordings_table.selectedItems()]))
        print(rows)
        ids = [str(self.all_ids[i]) for i in rows]  # [self.recordings_table.item(i, 0).text() for i in rows]
        # Спрашиваем у пользователя подтверждение на удаление элементов
        valid = QMessageBox.question(
            self, '', "Действительно удалить элементы с id " + ",".join(ids),
            QMessageBox.Yes, QMessageBox.No)
        # Если пользователь ответил утвердительно, удаляем элементы.
        # Не забываем зафиксировать изменения
        if valid == QMessageBox.Yes:
            # удаляем записи и сохраняем изменений
            cur = self.con.cursor()
            cur.execute("DELETE FROM Recordings WHERE record_id IN (" + ", ".join(
                '?' * len(ids)) + ")", ids)
            self.con.commit()

            # for i in ids:
            #     self.all_ids.remove(int(i))
            # print(f"after deleting{self.all_ids}")

        self.all_ids.clear()
        self.load_table()  # загружаем таблицу снова

    # функция смены темы
    def change_theme(self, theme):
        # если темы нет, то вызываем сообщение об ошибке
        try:
            if theme == "dark":
                colors = DARK
            elif theme == "light":
                colors = LIGHT
            else:
                colors = GRADIENT
            bg_color, text_color = colors[4], colors[3]
            self.setStyleSheet(f"""background-color: {bg_color};
                                           color: {text_color}""")
            for item in (self.username_label,
                         self.delete_btn,
                         self.average_result_label):
                item.setStyleSheet(f"color: {text_color}")
            self.background.setPixmap(get_pixmap(theme))
        except KeyError:
            error_message = QMessageBox(self)
            error_message.setIcon(QMessageBox.Critical)
            error_message.setText(f"Такой темы {theme} не существует")
            error_message.setWindowTitle("Смена темы отменена")
            error_message.exec_()

    # функция, которая вызывается, когда закрывается окно
    def closeEvent(self, *args, **kwargs):
        # Закрытие соединение с базой данных при закрытие окна
        self.con.close()


# Наследуемся от виджета из PyQt5.QtWidgets и от класса с интерфейсом
class MainWindow(QMainWindow, Ui_MainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QtGui.QIcon('data\\keyboard.png'))  # изменение иконки приложения
        # Вызываем метод для загрузки интерфейса из класса Ui_MainWindow,
        self.setupUi(self)
        self.generated_text = ""  # сгенерированный текст
        self.alphabet = "lat"
        self.text_id = 0

        self.background.setPixmap(get_pixmap("dark"))
        self.generated_text_html.setPixmap(get_pixmap("dark"))
        self.generated_text_html.setAttribute(Qt.WA_NoSystemBackground)
        for item in (self.entered_text,
                     self.hint_label,
                     self.username_label,
                     self.stopwatch_label):
            item.setAttribute(Qt.WA_NoSystemBackground)

        # связываемся с базой данных trainer_db.db
        self.con = sqlite3.connect(DATABASE)

        self.difficulty_mode = 'easy'  # легкий режим по умолчанию
        self.user = "Гость"  # пользователь по умолчанию
        self.theme = "dark"  # тема по умолчанию

        # переменные для отслеживания изменения программой текста и начала старта секундомера
        self.is_program_change = False
        self.is_stopwatch_start = False

        # # цвет для выделения правильного текста и неправильного текста
        # self.correct_color = DARK[0]
        # self.incorrect_color = DARK[1]
        # self.main_text_color = DARK[2]
        # self.highlighting_color = DARK[3]
        # self.background_color = DARK[4]
        self.set_dark_theme()

        # загружаем текст
        self.load_text(self.difficulty_mode)
        # при изменении текста в entered_text вызвать функцию text_changed
        self.entered_text.textChanged.connect(self.text_changed)

        # Создание секундомера
        self.stopwatch = QTimer(self)
        self.stopwatch.timeout.connect(self.show_stopwatch)
        self.start_time = 0  # время начало ввода
        self.timeInterval = 100  # интервал вызова секундомера
        self.time_r = 0  # разница между начальным временем и текущем временем. Изначально равен 0

        self.actual_text = ""  # ранее введенный текст
        self.actual_index = 0  # индекс ранее введенного текста

        self.interface_binding()  # привязка частей интерфейса к функциям

    # обработчик событий нажатия клавиш и мыши
    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:  # при нажатие на esc начать заново
            self.start_again()

    # начать заново ввод текста
    def start_again(self):
        self.is_program_change = True  # программа изменила текст
        self.reset_stopwatch()  # перезапустить секундомер
        self.load_text(self.difficulty_mode)  # ввести новый текст
        self.entered_text.setText("")  # обнулить вводимый текст
        self.is_program_change = False  # вернуться к исходному значению
        self.actual_index = 0
        self.actual_text = ""

    # загрузка нового текста со сложностью difficult из таблицы Texts
    def load_text(self, difficult):
        # Создание курсора
        cur = self.con.cursor()

        # Выполнение запроса и получение всех результатов
        texts = cur.execute(f"""
        SELECT text FROM Texts 
            WHERE difficulty_id=(
        SELECT difficulty_id FROM Difficults 
            WHERE mode = '{difficult}')
        """).fetchall()

        # выбирание случайного текста, пока он совпадает с текстом в generated_text
        text = choice(texts)[0]
        while self.generated_text == text:
            text = choice(texts)[0]

        # Получение text_id путем запроса из таблицы Texts
        self.text_id = cur.execute(f"""
            SELECT text_id FROM Texts
                WHERE text='{text}'""").fetchall()[0][0]

        if self.alphabet == "lat":
            text = convert_to_lat(text)

        self.generated_text = text
        self.generated_text_html.setTextFormat(Qt.RichText)
        self.generated_text_html.setText(
            f"<font color='{self.highlighting_color}'>{text.split()[0] + ' '}<font>"
            f"<font color='{self.main_text_color}'>{' '.join(text.split()[1:])}<font>")  # вставить новый текст в generated_text

    # обработчик события изменения текста
    def text_changed(self):
        if not self.is_program_change:  # если пользователь ввел текст
            if not self.is_stopwatch_start:  # если таймер был не запущен, запустить его
                self.start_stopwatch()
            self.compare_texts()  # начать сравнивать тексты

    # функция сравнения текстов из generated_text и entered_text
    def compare_texts(self):
        # запоминаем положение курсора
        cursor = self.entered_text.textCursor()

        generated_text = self.generated_text
        entered_text = self.entered_text.toPlainText()
        if entered_text == "":
            return

        font_size = 4  # размер текста
        is_correct = True  # переменная для отслеживания корректности ввода

        html = ""

        # перебор символов в entered_text
        for index, character in enumerate(entered_text):
            index += self.actual_index
            if index <= len(generated_text) - 1:
                if generated_text[index] != character:
                    is_correct = False
            else:
                is_correct = False
            color = self.correct_color if is_correct else self.incorrect_color
            html += f"<font color='{color}' size = {font_size} >{character}</font>"
        self.is_program_change = True  # показываем что изменяем программу вручную
        self.entered_text.setHtml(html)
        self.is_program_change = False  # отключаем режим изменения

        # возвращаем курсор на место, так как при setHtml его позиция обнуляется
        self.entered_text.setTextCursor(cursor)

        if is_correct and entered_text[-1] == " " or \
                is_correct and len(self.actual_text) + len(entered_text) == len(generated_text):
            self.actual_text += entered_text  # расширяем введенный ранее текст
            self.actual_index = len(self.actual_text)  # соответственно увеличиваем и индекс введенного текста
            self.is_program_change = True
            self.entered_text.setText("")
            self.is_program_change = False

            self.generated_text_html.setTextFormat(Qt.RichText)

            if self.actual_text != generated_text:
                written = generated_text[:self.actual_index]
                next_word = generated_text[self.actual_index:].split()[0] + " "
                further = " ".join(generated_text[self.actual_index:].split()[1:])
                self.generated_text_html.setText(
                    f"<font color='{self.correct_color}'>{written}</font><font color='{self.main_text_color}'>"
                    f"<font color='{self.highlighting_color}'>{next_word}</font>"
                    f"<font color='{self.main_text_color}'>{further}</font>")  # делаем введенное слово из текста зеленым

        # если пользователь весь текст правильно, то вызвать функций показа, загрузки записи и начать заново
        if is_correct and len(self.actual_text) == len(generated_text):
            self.generated_text_html.setText(f"<font color='{self.correct_color}'>{generated_text}<font>")
            self.stopwatch.stop()
            self.show_and_load_recording()
            self.start_again()

    # функция показа и загрузки записи
    def show_and_load_recording(self):
        # Создание курсора
        cur = self.con.cursor()

        # Получение user_id путем запроса из таблицы Users
        user_id = cur.execute(f"""
            SELECT user_id FROM Users 
                WHERE nickname='{self.user}'""").fetchall()[0][0]

        # Получение текущей даты при помощи библиотеки datetime
        data = str(datetime.datetime.now().date())

        # Получение difficulty_id путем запроса из таблицы Texts
        difficulty_id = cur.execute(f"""
            SELECT difficulty_id FROM Difficults
                WHERE mode='{self.difficulty_mode}'""").fetchall()[0][0]

        # Получение time через self.stopwatch_label.text()
        typing_time = self.stopwatch_label.text()

        # typing_speed = S / time * 60 сим/мин
        typing_speed = round(len(self.generated_text) / self.time_r * 60, 1)

        # добавляем запись в бд и показываем результат пользователю
        self.load_recording(user_id, data, self.text_id, difficulty_id, typing_time, typing_speed)
        self.show_result(typing_time, typing_speed)

    def load_recording(self, user_id, data, text_id, difficulty_id, typing_time, typing_speed):
        # Создание курсора
        cur = self.con.cursor()

        que = f"""INSERT INTO Recordings(user_id, data, text_id, difficulty_id, time, typing_speed) 
        VALUES ({user_id}, '{data}', {text_id}, {difficulty_id}, '{typing_time}', {typing_speed})"""

        cur.execute(que)

        self.con.commit()

    # функция показа результата пользователя
    def show_result(self, typing_time, typing_speed):
        dialog = ResultsDialog(typing_time, typing_speed, self.theme)
        dialog.show()
        dialog.exec()

    # запуск секундомера
    def start_stopwatch(self):
        self.is_stopwatch_start = True
        self.start_time = time.time()  # в качестве начального времени установить текущее время
        self.time_r = 0  # Обнулить разницу во времени
        self.stopwatch_label.setText('00:00')
        self.stopwatch.start(self.timeInterval)  # запуск секундомера с интервалом timeInterval

    # сброс секундомера
    def reset_stopwatch(self):
        self.is_stopwatch_start = False
        self.start_time = 0  # в качестве начального времени установить 0
        self.time_r = 0  # Обнулить разницу во времени
        self.stopwatch_label.setText('00:00')
        self.stopwatch.stop()  # остановка секундомера

    # функция показа значения секундомера
    def show_stopwatch(self):
        # обновить разницу во времени
        self.time_r = int(time.time() - self.start_time)

        # перевод времени в минуту и секунду
        minutes = self.time_r // 60
        seconds = self.time_r % 60
        if minutes > 59:  # если минут больше чем 59, то вывод максимального времени
            self.timer_label.setText('59:59')
        else:
            # создание строки для удобного показа времени
            minutes = str(minutes)
            seconds = str(seconds)
            stopwatch_text = '0' * (2 - len(minutes)) + minutes + ':' + '0' * (2 - len(seconds)) + seconds
            self.stopwatch_label.setText(stopwatch_text)

    # функция для привязки частей интерфейса к функциям
    def interface_binding(self):
        # настройки темы
        self.dark_theme.triggered.connect(lambda: self.change_theme("dark"))
        self.light_theme.triggered.connect(lambda: self.change_theme("light"))
        self.gradient_theme.triggered.connect(lambda: self.change_theme("gradient"))

        # настройки сложности
        self.easy_mode.triggered.connect(lambda: self.change_difficulty('easy'))
        self.normal_mode.triggered.connect(lambda: self.change_difficulty('normal'))
        self.hard_mode.triggered.connect(lambda: self.change_difficulty('hard'))

        # настройки пользователя
        self.register_user.triggered.connect(self.registration)
        self.login_user.triggered.connect(self.login)

        # меню результатов
        self.results_menu.triggered.connect(self.show_recordings)

        self.cyrillic.triggered.connect(self.change_alphabet)
        self.latin.triggered.connect(self.change_alphabet)

    # функция показа окна результата
    def show_recordings(self):
        self.recordings_window = RecordingsWindow(self.user, self.theme)
        self.recordings_window.show()

    def change_alphabet(self):
        if self.alphabet == "lat":
            self.alphabet = "cyr"
            return
        self.alphabet = "lat"

    # функция смены темы приложения
    def change_theme(self, theme):
        if self.theme == theme:
            return

        self.theme = theme
        if theme == "light":
            colors = self.set_light_theme()
        elif theme == "dark":
            colors = self.set_dark_theme()
        else:
            colors = self.set_gradient_theme()

        self.generated_text_html.setStyleSheet(f"color: {colors[2]};")
        self.entered_text.setStyleSheet(f"color: {colors[0]};")
        self.username_label.setStyleSheet(f"color: {colors[2]}")
        self.stopwatch_label.setStyleSheet(f"color: {colors[2]};")

        self.generated_text_html.setTextFormat(Qt.RichText)
        text = self.generated_text
        self.generated_text_html.setText(
            f"<font color='{self.highlighting_color}'>{text.split()[0] + ' '}<font>"
            f"<font color='{self.main_text_color}'>{' '.join(text.split()[1:])}<font>")  # вставить новый текст в generated_text

        self.compare_texts()

    # функция установки светлой темы
    def set_light_theme(self):
        colors = LIGHT
        self.correct_color = colors[0]
        self.incorrect_color = colors[1]
        self.main_text_color = colors[2]
        self.highlighting_color = colors[3]
        self.background_color = colors[4]

        self.setStyleSheet(f"color: {colors[2]};")
        self.hint_label.setStyleSheet(f"color: #3e3f40;")
        self.menubar.setStyleSheet(f"color: black;")

        self.background.setPixmap(get_pixmap("light"))

        return colors

    # функция установки темной темы
    def set_dark_theme(self):
        colors = DARK
        self.correct_color = colors[0]
        self.incorrect_color = colors[1]
        self.main_text_color = colors[2]
        self.highlighting_color = colors[3]
        self.background_color = colors[4]

        self.setStyleSheet(f"background-color: {colors[4]}; color: white;")
        self.hint_label.setStyleSheet(f"color: #87898a;")
        self.menubar.setStyleSheet(f"color: white;")

        self.background.setPixmap(get_pixmap("dark"))

        return colors

    # функция установки океанной темы
    def set_gradient_theme(self):
        colors = GRADIENT
        self.correct_color = colors[0]
        self.incorrect_color = colors[1]
        self.main_text_color = colors[2]
        self.highlighting_color = colors[3]
        self.background_color = colors[4]

        self.setStyleSheet(f"background-color: {colors[4]}; color: white;")
        self.hint_label.setStyleSheet(f"color: #C0D9E5;")
        self.menubar.setStyleSheet(f"color: white;")

        self.background.setPixmap(get_pixmap("gradient"))

        return colors

    # функция изменения сложности
    def change_difficulty(self, diff):
        # если сложность осталась такой же, то ничего не менять
        if self.difficulty_mode == diff:
            return

        # начинаем заново, так как изменилась сложность
        self.difficulty_mode = diff
        self.start_again()

    # функция регистрации пользователя
    def registration(self):
        # вызов диалогового окна
        username, ok_pressed = QInputDialog.getText(self, "Регистрация", "Введите имя пользователя:")

        # если пользователь нажал на ОК, то добавить его в таблицу Users в БД и начать заново
        if ok_pressed:
            self.add_user(username)
            self.start_again()

    # добавление пользователя в БД
    def add_user(self, username):
        # создаем курсор и выполняем запрос
        cur = self.con.cursor()
        users = map(lambda x: x[0], cur.execute("""SELECT nickname FROM Users""").fetchall())

        # если пользователь уже существует, то вызвать окно с ошибкой
        if username in users:
            error_message = QMessageBox(self)
            error_message.setIcon(QMessageBox.Critical)
            error_message.setText("Пользователь уже существует!")
            error_message.setInformativeText("Введите другое имя пользователя")
            error_message.setWindowTitle("Регистрация отменена")
            error_message.exec_()
            return

        # добавляем пользователя в таблицу Users из БД
        cur.execute(f"INSERT INTO Users(nickname) VALUES('{username}')")

        # зафиксировать изменения в БД
        self.con.commit()

        # поменять пользователя и изменить ник отображаемый в окне
        self.user = username
        self.username_label.setText(username)

    # функция для входа в пользователя
    def login(self):
        # создаем курсор
        cur = self.con.cursor()

        # получение ников для входа
        users = map(lambda x: x[0], cur.execute("""SELECT nickname FROM Users""").fetchall())

        # вызываем диалоговое окно для выбора пользователя
        username, ok_pressed = QInputDialog.getItem(self, "Вход", "Выберите пользователя: ",
                                                    users, 1, False)

        # если пользователь нажал на ОК, то сменить пользователя
        if ok_pressed:
            # смена пользователя и изменить ник отображаемый в окне
            self.user = username
            self.username_label.setText(username)
            self.start_again()  # начинаем заново, так как сменился пользователь

    # функция, которая вызывается, когда закрывается окно
    def closeEvent(self, *args, **kwargs):
        # Закрытие соединение с базой данных при закрытие окна
        self.con.close()


# окно для вывода результата пользователя
class ResultsDialog(QDialog, Ui_Dialog):
    def __init__(self, typing_time, result, theme):
        super().__init__()  # конструктор родительского класса
        # Вызываем метод для загрузки интерфейса из класса Ui_Dialog,
        self.setupUi(self)
        self.setWindowIcon(QtGui.QIcon('data\\keyboard.png'))  # изменение иконки приложения
        self.change_theme(theme)
        for item in (self.comment_label,
                     self.time_label,
                     self.cpm_label):
            item.setAttribute(Qt.WA_NoSystemBackground)
        self.button_box.accepted.connect(self.accept_data)  # привязка функции кнопки ОК
        self.time_label.setText(f"Общее время: {typing_time}")
        self.cpm_label.setText(f"Символов в минуту: {result}")
        img_num = randint(1, 2)
        try:
            if result <= 100:
                self.comment_label.setText("Постарайтесь лучше!")
                img = f"data\\very_bad{img_num}.jpeg"
            elif 100 < result <= 200:
                self.comment_label.setText("Для начала неплохо!")
                img = f"data\\bad{img_num}.jpeg"
            elif 200 < result <= 350:
                self.comment_label.setText("Отличный результат!")
                img = f"data\\good{img_num}.jpeg"
            else:
                self.comment_label.setText("Превосходно!")
                img = f"data\\very_good{img_num}.jpeg"
            pixmap = QPixmap(img)
            pixmap = pixmap.scaled(191, 191)
            self.image_label.setPixmap(pixmap)  # вставка картинки в label
        except Exception:
            error_message = QMessageBox(self)
            error_message.setIcon(QMessageBox.Critical)
            error_message.setText("Картинка не найдена!")
            error_message.exec_()

    # функция для закрытия окна на нажатие ОК
    def accept_data(self):
        self.close()

    def change_theme(self, theme):
        try:
            if theme == "dark":
                colors = DARK
            elif theme == "light":
                colors = LIGHT
            else:
                colors = GRADIENT
            text_color, bg_color = colors[3], colors[4]
            self.setStyleSheet(f"""background-color: {bg_color};
                                           color: {text_color}""")
            for item in (self.comment_label,
                         self.time_label,
                         self.cpm_label):
                item.setStyleSheet("color: {text_color}")
            self.background.setPixmap(get_pixmap(theme))
        except KeyError:
            error_message = QMessageBox(self)
            error_message.setIcon(QMessageBox.Critical)
            error_message.setText(f"Такой темы {theme} не существует")
            error_message.setWindowTitle("Смена темы отменена")
            error_message.exec_()


if __name__ == '__main__':
    # Создание класса приложения PyQT
    app = QApplication(sys.argv)
    # создание экземпляра класса MyWidget
    main_window = MainWindow()
    # показ экземпляра
    main_window.show()
    # при завершение исполнения QApplication завершить программу
    sys.exit(app.exec())
