import sys
import subprocess
import json
import os
from pathlib import Path
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget, QPushButton,
    QListWidget, QLineEdit, QLabel, QFileDialog, QMessageBox, QFormLayout,
    QSpinBox, QCheckBox
)
from PyQt6.QtCore import Qt, QStandardPaths
from PyQt6.QtGui import QCloseEvent
import qdarkstyle

CONFIG_FILE = "scripts_config.json"


class ScriptRunnerApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.config_path = self.get_config_path()
        self.processes = {}
        self.scripts = []

        self.init_ui()
        self.load_config()

    def get_config_path(self):
        config_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        Path(config_dir).mkdir(parents=True, exist_ok=True)
        return os.path.join(config_dir, CONFIG_FILE)

    def init_ui(self):
        self.setWindowTitle("Python Script Runner")
        self.setGeometry(100, 100, 800, 600)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.layout = QVBoxLayout(self.central_widget)

        # Форма добавления скриптов
        self.form_layout = QFormLayout()

        self.script_name_input = QLineEdit()
        self.script_path_input = QLineEdit()
        self.script_path_input.setReadOnly(True)
        self.browse_script_btn = QPushButton("Обзор")
        self.browse_script_btn.clicked.connect(lambda: self.browse_file(self.script_path_input))

        self.venv_path_input = QLineEdit()
        self.venv_path_input.setReadOnly(True)
        self.browse_venv_btn = QPushButton("Обзор")
        self.browse_venv_btn.clicked.connect(lambda: self.browse_venv())

        self.auto_venv_check = QCheckBox("Автоопределение .venv")
        self.auto_venv_check.setChecked(True)

        self.script_args_input = QLineEdit()
        self.script_timeout = QSpinBox()
        self.script_timeout.setRange(1, 3600)
        self.script_timeout.setValue(60)

        self.form_layout.addRow("Название скрипта:", self.script_name_input)
        self.form_layout.addRow("Путь к скрипту:", self.script_path_input)
        self.form_layout.addRow("", self.browse_script_btn)
        self.form_layout.addRow("Путь к интерпретатору:", self.venv_path_input)
        self.form_layout.addRow("", self.browse_venv_btn)
        self.form_layout.addRow("", self.auto_venv_check)
        self.form_layout.addRow("Аргументы скрипта:", self.script_args_input)
        self.form_layout.addRow("Таймаут (сек):", self.script_timeout)

        self.add_script_button = QPushButton("Добавить скрипт")
        self.add_script_button.clicked.connect(self.add_script)
        self.form_layout.addRow(self.add_script_button)

        self.layout.addLayout(self.form_layout)

        # Список скриптов
        self.script_list = QListWidget()
        self.layout.addWidget(QLabel("Добавленные скрипты:"))
        self.layout.addWidget(self.script_list)

        # Управление
        self.control_layout = QHBoxLayout()
        self.run_button = QPushButton("Запуск")
        self.run_button.clicked.connect(self.run_script)
        self.stop_button = QPushButton("Остановить")
        self.stop_button.clicked.connect(self.stop_script)
        self.control_layout.addWidget(self.run_button)
        self.control_layout.addWidget(self.stop_button)
        self.layout.addLayout(self.control_layout)

    def browse_file(self, target_field):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", "Python Files (*.py)")
        if file_path:
            target_field.setText(file_path)
            if self.auto_venv_check.isChecked():
                self.auto_detect_venv(file_path)

    def browse_venv(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите интерпретатор",
            "",
            "Python Executable (python.exe)"
        )
        if file_path:
            self.venv_path_input.setText(file_path)

    def auto_detect_venv(self, script_path):
        script_dir = os.path.dirname(script_path)
        venv_path = os.path.join(script_dir, ".venv", "Scripts", "python.exe")
        if os.path.exists(venv_path):
            self.venv_path_input.setText(venv_path)
        else:
            self.venv_path_input.clear()

    def add_script(self):
        script_data = {
            "name": self.script_name_input.text(),
            "path": self.script_path_input.text(),
            "venv": self.venv_path_input.text(),
            "args": self.script_args_input.text(),
            "timeout": self.script_timeout.value()
        }

        if not script_data["name"] or not script_data["path"]:
            QMessageBox.warning(self, "Ошибка", "Название и путь к скрипту обязательны!")
            return

        self.scripts.append(script_data)
        self.script_list.addItem(script_data["name"])
        self.clear_form()

    def clear_form(self):
        self.script_name_input.clear()
        self.script_path_input.clear()
        self.venv_path_input.clear()
        self.script_args_input.clear()
        self.script_timeout.setValue(60)

    def run_script(self):
        selected = self.script_list.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите скрипт из списка!")
            return

        script = self.scripts[selected]
        try:
            interpreter = script["venv"] or "python"
            command = [interpreter, script["path"]]

            if script["args"]:
                command.extend(script["args"].split())

            process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                creationflags=subprocess.CREATE_NO_WINDOW
            )

            self.processes[script["name"]] = process
            QMessageBox.information(self, "Запуск", f"Скрипт '{script['name']}' запущен!")

        except Exception as e:
            QMessageBox.critical(self, "Ошибка", f"Ошибка запуска: {str(e)}")

    def stop_script(self):
        selected = self.script_list.currentRow()
        if selected == -1:
            QMessageBox.warning(self, "Ошибка", "Выберите скрипт из списка!")
            return

        script_name = self.scripts[selected]["name"]
        if process := self.processes.get(script_name):
            process.terminate()
            QMessageBox.information(self, "Остановка", f"Скрипт '{script_name}' остановлен!")
        else:
            QMessageBox.warning(self, "Ошибка", "Скрипт не запущен!")

    def save_config(self):
        with open(self.config_path, "w") as f:
            json.dump(self.scripts, f, indent=2)

    def load_config(self):
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    self.scripts = json.load(f)
                    for script in self.scripts:
                        self.script_list.addItem(script["name"])
            except Exception as e:
                QMessageBox.warning(self, "Ошибка", f"Ошибка загрузки конфига: {str(e)}")

    def closeEvent(self, event: QCloseEvent):
        self.save_config()
        super().closeEvent(event)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(qdarkstyle.load_stylesheet_pyqt6())
    window = ScriptRunnerApp()
    window.show()
    sys.exit(app.exec())