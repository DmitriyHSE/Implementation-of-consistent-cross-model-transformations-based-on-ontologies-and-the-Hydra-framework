import tkinter as tk
from tkinter import filedialog, messagebox
from pathlib import Path
from converter import OntologyConverter
from owl_to_python import generate_python_classes
import logging
import os


class OntologyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ontology Converter")
        self.root.geometry("600x400")

        # Настройка логгирования
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("OntologyApp")

        # Переменные состояния
        self.source_file = tk.StringVar()
        self.owl_file = tk.StringVar()
        self.output_dir = tk.StringVar(value=str(Path.cwd() / "generated"))

        # Инициализация интерфейса
        self.create_widgets()
        self.ensure_output_dir()

    def ensure_output_dir(self):
        """Создаёт выходную директорию, если её нет"""
        output_dir = Path(self.output_dir.get())
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

    def create_widgets(self):
        # Стили
        button_style = {'padx': 10, 'pady': 5}
        label_style = {'padx': 10, 'pady': 5, 'anchor': 'w'}

        # Фрейм для выбора файла
        file_frame = tk.LabelFrame(self.root, text="1. Выберите исходный файл", padx=10, pady=10)
        file_frame.pack(fill="x", padx=10, pady=5)

        tk.Button(
            file_frame,
            text="Выбрать файл (XML/YAML/JSON)",
            command=self.select_source_file,
            **button_style
        ).pack(side="left")

        self.source_label = tk.Label(
            file_frame,
            textvariable=self.source_file,
            wraplength=400,
            justify="left",
            **label_style
        )
        self.source_label.pack(side="left", expand=True, fill="x")

        # Фрейм для OWL конвертации
        owl_frame = tk.LabelFrame(self.root, text="2. Конвертация в OWL", padx=10, pady=10)
        owl_frame.pack(fill="x", padx=10, pady=5)

        self.convert_btn = tk.Button(
            owl_frame,
            text="Конвертировать в OWL",
            command=self.convert_to_owl,
            state="disabled",
            **button_style
        )
        self.convert_btn.pack(side="left")

        self.owl_label = tk.Label(
            owl_frame,
            textvariable=self.owl_file,
            wraplength=400,
            justify="left",
            **label_style
        )
        self.owl_label.pack(side="left", expand=True, fill="x")

        # Фрейм для генерации Python
        python_frame = tk.LabelFrame(self.root, text="3. Генерация Python-кода", padx=10, pady=10)
        python_frame.pack(fill="x", padx=10, pady=5)

        tk.Button(
            python_frame,
            text="Выбрать OWL-файл",
            command=self.select_owl_file,
            **button_style
        ).pack(side="left")

        self.generate_btn = tk.Button(
            python_frame,
            text="Сгенерировать Python",
            command=self.generate_python,
            state="disabled",
            **button_style
        )
        self.generate_btn.pack(side="left")

        tk.Label(
            python_frame,
            text="Выходная директория:",
            padx=10,
            pady=5
        ).pack(side="left")

        output_entry = tk.Entry(
            python_frame,
            textvariable=self.output_dir,
            width=30
        )
        output_entry.pack(side="left", fill="x", expand=True)

        # Статус бар
        self.status = tk.StringVar(value="Готов к работе")
        status_bar = tk.Label(
            self.root,
            textvariable=self.status,
            bd=1,
            relief="sunken",
            anchor="w"
        )
        status_bar.pack(fill="x", padx=10, pady=10)

    def select_source_file(self):
        """Выбор исходного файла"""
        filetypes = [
            ("XML files", "*.xml"),
            ("YAML files", "*.yaml *.yml"),
            ("JSON files", "*.json"),
            ("All files", "*.*")
        ]

        filename = filedialog.askopenfilename(
            title="Выберите файл для конвертации",
            filetypes=filetypes
        )

        if filename:
            self.logger.info(f"Выбран файл: {filename}")
            self.source_file.set(filename)
            self.owl_file.set("")
            self.update_buttons()
            self.status.set(f"Выбран файл: {Path(filename).name}")
            self.root.update()

    def select_owl_file(self):
        """Выбор OWL-файла"""
        filename = filedialog.askopenfilename(
            title="Выберите OWL-файл",
            filetypes=[("OWL files", "*.owl"), ("All files", "*.*")]
        )

        if filename:
            self.logger.info(f"Выбран OWL-файл: {filename}")
            self.owl_file.set(filename)
            self.update_buttons()
            self.status.set(f"Выбран OWL-файл: {Path(filename).name}")

    def update_buttons(self):
        """Обновление состояния кнопок"""
        self.convert_btn.config(state="normal" if self.source_file.get() else "disabled")
        self.generate_btn.config(state="normal" if self.owl_file.get() else "disabled")
        self.root.update()

    def convert_to_owl(self):
        """Конвертация в OWL"""
        input_file = self.source_file.get()  # Используем input_file вместо source
        if not input_file:
            self.status.set("Ошибка: не выбран исходный файл")
            return

        try:
            source_path = Path(input_file)
            output_file = source_path.with_suffix(".owl")

            self.logger.info(f"Конвертация {input_file} -> {output_file}")
            self.status.set("Конвертация...")
            self.root.update()

            converter = OntologyConverter()
            converter.convert(input_file, str(output_file))

            self.owl_file.set(str(output_file))
            self.update_buttons()
            self.status.set(f"Успешно сконвертировано в: {output_file.name}")
            messagebox.showinfo(
                "Успех",
                f"Файл успешно сконвертирован:\n{output_file}",
                parent=self.root
            )
        except Exception as e:
            self.logger.error(f"Ошибка конвертации: {str(e)}")
            self.status.set(f"Ошибка: {str(e)}")
            messagebox.showerror(
                "Ошибка",
                f"Не удалось сконвертировать файл:\n{str(e)}",
                parent=self.root
            )

    def generate_python(self):
        """Генерация Python-кода"""
        owl_file = self.owl_file.get()
        output_dir = self.output_dir.get()

        if not owl_file:
            self.status.set("Ошибка: не выбран OWL-файл")
            return

        try:
            self.ensure_output_dir()
            self.logger.info(f"Генерация Python из {owl_file} в {output_dir}")
            self.status.set("Генерация Python-кода...")
            self.root.update()

            generate_python_classes(owl_file, output_dir)

            output_path = Path(output_dir) / "ontology_model.py"
            self.status.set(f"Python-код сгенерирован в: {output_path}")
            self.logger.info(f"Успешно сгенерирован Python-код: {output_path}")

            messagebox.showinfo(
                "Успех",
                f"Python-код успешно сгенерирован:\n{output_path}\n\n"
                f"Директория: {Path(output_dir).absolute()}",
                parent=self.root
            )
        except Exception as e:
            self.logger.error(f"Ошибка генерации: {str(e)}")
            self.status.set(f"Ошибка генерации: {str(e)}")
            messagebox.showerror(
                "Ошибка",
                f"Не удалось сгенерировать Python-код:\n{str(e)}",
                parent=self.root
            )


if __name__ == "__main__":
    root = tk.Tk()
    app = OntologyApp(root)
    root.mainloop()