import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from converter import OntologyConverter
from owl_to_python import generate_python_classes
from owl_to_java import generate_java_classes
from owl_to_cpp import generate_cpp_from_owl
import logging
import semver
from typing import Optional

class OntologyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Преобразователь онтологий")
        self.root.geometry("900x650")
        self.root.minsize(800, 550)
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("OntologyApp")
        self.source_file = tk.StringVar()
        self.owl_file = tk.StringVar()
        self.previous_owl_file = tk.StringVar()
        self.base_output_dir = tk.StringVar(value=str(Path.cwd() / "generated"))
        self.hydra_mode = tk.BooleanVar(value=False)
        self.version = tk.StringVar(value="1.0.0")
        self.status = tk.StringVar(value="Готово к работе!")
        self.folder_prefix = tk.StringVar(value="ontology")
        self.java_package = tk.StringVar(value="generated")
        self.create_widgets()
        self.ensure_output_dir()

    def create_widgets(self):
        style = ttk.Style()
        style.configure("TFrame", padding=5)
        style.configure("TLabel", padding=5)
        style.configure("TButton", padding=5)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        file_frame = ttk.LabelFrame(main_frame, text="1. Выбор исходного файла", padding=10)
        file_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            file_frame,
            text="Выбрать (XML/YAML/JSON)",
            command=self.select_source_file
        ).pack(side=tk.LEFT)

        ttk.Label(
            file_frame,
            textvariable=self.source_file,
            wraplength=600,
            anchor=tk.W
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        convert_frame = ttk.LabelFrame(main_frame, text="2. Преобразование в OWL", padding=10)
        convert_frame.pack(fill=tk.X, pady=5)

        self.convert_btn = ttk.Button(
            convert_frame,
            text="Преобразовать в OWL",
            command=self.convert_to_owl,
            state=tk.DISABLED
        )
        self.convert_btn.pack(side=tk.LEFT)

        ttk.Label(convert_frame, text="Версия:").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Entry(convert_frame, textvariable=self.version, width=10).pack(side=tk.LEFT)

        ttk.Label(
            convert_frame,
            textvariable=self.owl_file,
            wraplength=500,
            anchor=tk.W
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        prev_frame = ttk.LabelFrame(main_frame, text="Дополнительно: Выбор предыдущей версии", padding=10)
        prev_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            prev_frame,
            text="Выбрать предыдущую OWL",
            command=self.select_previous_owl_file
        ).pack(side=tk.LEFT)

        ttk.Checkbutton(
            prev_frame,
            text="Внедрение Hydra",
            variable=self.hydra_mode
        ).pack(side=tk.LEFT)

        ttk.Label(
            prev_frame,
            textvariable=self.previous_owl_file,
            wraplength=500,
            anchor=tk.W
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        python_frame = ttk.LabelFrame(main_frame, text="3. Генерирование кода на Python", padding=10)
        python_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            python_frame,
            text="Выбрать OWL-файл",
            command=self.select_owl_file
        ).pack(side=tk.LEFT)

        self.generate_python_btn = ttk.Button(
            python_frame,
            text="Генерировать Python",
            command=self.generate_python,
            state=tk.DISABLED
        )
        self.generate_python_btn.pack(side=tk.LEFT, padx=10)


        java_frame = ttk.LabelFrame(main_frame, text="4. Генерирование кода на Java", padding=10)
        java_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            java_frame,
            text="Выбрать OWL-файл",
            command=self.select_owl_file
        ).pack(side=tk.LEFT)

        self.generate_java_btn = ttk.Button(
            java_frame,
            text="Генерировать Java",
            command=self.generate_java,
            state=tk.DISABLED
        )
        self.generate_java_btn.pack(side=tk.LEFT, padx=10)


        cpp_frame = ttk.LabelFrame(main_frame, text="5. Генерирование кода на C++", padding=10)
        cpp_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            cpp_frame,
            text="Выбрать OWL-файл",
            command=self.select_owl_file
        ).pack(side=tk.LEFT)

        self.generate_cpp_btn = ttk.Button(
            cpp_frame,
            text="Генерировать C++",
            command=self.generate_cpp,
            state=tk.DISABLED
        )
        self.generate_cpp_btn.pack(side=tk.LEFT, padx=10)


        naming_frame = ttk.LabelFrame(main_frame, text="Выходные данные", padding=10)
        naming_frame.pack(fill=tk.X, pady=5)

        ttk.Label(naming_frame, text="Префикс папки:").pack(side=tk.LEFT)
        ttk.Entry(naming_frame, textvariable=self.folder_prefix, width=20).pack(side=tk.LEFT, padx=5)

        ttk.Label(naming_frame, text="Путь:").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Entry(
            naming_frame,
            textvariable=self.base_output_dir,
            width=30
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        status_frame = ttk.Frame(main_frame)
        status_frame.pack(fill=tk.X, pady=10)

        ttk.Label(
            status_frame,
            textvariable=self.status,
            relief=tk.SUNKEN,
            anchor=tk.W
        ).pack(fill=tk.X)

    def ensure_output_dir(self):
        output_dir = Path(self.base_output_dir.get())
        if not output_dir.exists():
            output_dir.mkdir(parents=True)

    def select_source_file(self):
        filetypes = [
            ("XML files", "*.xml"),
            ("YAML files", "*.yaml *.yml"),
            ("JSON files", "*.json"),
            ("All files", "*.*")
        ]

        filename = filedialog.askopenfilename(
            title="Выбрать исходный файл",
            filetypes=filetypes
        )

        if filename:
            self.source_file.set(filename)
            self.owl_file.set("")
            self.update_buttons()
            self.set_status(f"Выбрано: {Path(filename).name}")

    def select_previous_owl_file(self):
        filename = filedialog.askopenfilename(
            title="Выбрать предыдущую версию OWL File",
            filetypes=[("OWL files", "*.owl"), ("All files", "*.*")]
        )

        if filename:
            self.previous_owl_file.set(filename)
            self.set_status(f"Выбранная предыдущая версия: {Path(filename).name}")

    def select_owl_file(self):
        filename = filedialog.askopenfilename(
            title="Выбрать OWL-файл",
            filetypes=[("OWL files", "*.owl"), ("All files", "*.*")]
        )

        if filename:
            self.owl_file.set(filename)
            self.update_buttons()
            self.set_status(f"Выбранный OWL-файл: {Path(filename).name}")

    def update_buttons(self):
        self.convert_btn.config(
            state=tk.NORMAL if self.source_file.get() else tk.DISABLED
        )
        self.generate_python_btn.config(
            state=tk.NORMAL if self.owl_file.get() else tk.DISABLED
        )
        self.generate_java_btn.config(
            state=tk.NORMAL if self.owl_file.get() else tk.DISABLED
        )
        self.generate_cpp_btn.config(
            state=tk.NORMAL if self.owl_file.get() else tk.DISABLED
        )

    def set_status(self, message: str):
        self.status.set(message)
        self.root.update()

    def convert_to_owl(self):
        input_file = self.source_file.get()
        version = self.version.get()

        try:
            semver.VersionInfo.parse(version)
            self.set_status("Конвертирование в OWL...")
            output_file = Path(input_file).with_suffix(".owl")

            converter = OntologyConverter()
            converter.convert(input_file, str(output_file), version)

            self.owl_file.set(str(output_file))
            self.update_buttons()
            self.set_status(f"Конвертирован в OWL (v{version})")
            messagebox.showinfo(
                "Успех",
                f"Успешно конвертировано в:\n{output_file}\nВерсия: {version}",
                parent=self.root
            )
        except ValueError as e:
            messagebox.showerror(
                "Ошибка версии",
                f"Неправильный формат версии: {str(e)}\nИспользовать правильные версии (например, 1.0.0)",
                parent=self.root
            )
            self.set_status("Ошибка версии")
        except Exception as e:
            messagebox.showerror(
                "Ошибка конвертации",
                str(e),
                parent=self.root
            )
            self.set_status("Не удалось выполнить преобразование")

    def generate_python(self):
        owl_file = self.owl_file.get()
        previous_owl = self.previous_owl_file.get() if self.previous_owl_file.get() else None
        base_output_dir = self.base_output_dir.get()
        hydra_mode = self.hydra_mode.get()
        folder_prefix = self.folder_prefix.get()

        try:
            self.ensure_output_dir()
            self.set_status("Генерация кода на Python...")

            output_dir = generate_python_classes(
                owl_file=owl_file,
                base_output_dir=base_output_dir,
                hydra_mode=hydra_mode,
                version=None,
                previous_version=previous_owl,
                folder_prefix=folder_prefix
            )

            self.set_status(f"Python код сгенерирован в: {output_dir}")
            messagebox.showinfo(
                "Успех",
                f"Python код успешно сгенерирован в:\n{output_dir}",
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                "Ошибка генерации кода",
                str(e),
                parent=self.root
            )
            self.set_status("Python генерация не удалась")

    def generate_java(self):
        owl_file = self.owl_file.get()
        previous_owl = self.previous_owl_file.get() if self.previous_owl_file.get() else None
        base_output_dir = self.base_output_dir.get()
        folder_prefix = self.folder_prefix.get()
        java_package = self.java_package.get()
        hydra_mode = self.hydra_mode.get()

        try:
            self.ensure_output_dir()
            self.set_status("Генерация кода на Java...")

            output_dir = generate_java_classes(
                owl_file=owl_file,
                base_output_dir=base_output_dir,
                package_name=java_package,
                version=None,
                previous_version=previous_owl,
                folder_prefix=folder_prefix
            )

            self.set_status(f"Java код сгенерирован в: {output_dir}")
            messagebox.showinfo(
                "Успех",
                f"Java код успешно сгенерирован в:\n{output_dir}",
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                "Ошибка генерации кода",
                str(e),
                parent=self.root
            )
            self.set_status("Java генерация не удалась")


    def generate_cpp(self):
        owl_file = self.owl_file.get()
        previous_owl = self.previous_owl_file.get() if self.previous_owl_file.get() else None
        base_output_dir = self.base_output_dir.get()
        folder_prefix = self.folder_prefix.get()

        try:
            self.ensure_output_dir()
            self.set_status("Генерация кода на C++...")

            output_dir = generate_cpp_from_owl(
                owl_file=owl_file,
                base_output_dir=base_output_dir,
                version=None,
                previous_version=previous_owl,
                folder_prefix=folder_prefix
            )

            self.set_status(f"C++ код сгенерирован в: {output_dir}")
            messagebox.showinfo(
                "Успех",
                f"C++ код успешно сгенерирован в:\n{output_dir}",
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                "Ошибка генерации кода",
                str(e),
                parent=self.root
            )
            self.set_status("C++ генерация не удалась")

if __name__ == "__main__":
    root = tk.Tk()
    app = OntologyApp(root)
    root.mainloop()