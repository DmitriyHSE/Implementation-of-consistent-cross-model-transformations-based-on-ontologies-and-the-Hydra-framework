import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from pathlib import Path
from converter import OntologyConverter
from owl_to_python import generate_python_classes
import logging
import semver
from typing import Optional


class OntologyApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ontology Converter")
        self.root.geometry("850x600")
        self.root.minsize(750, 500)

        # Configure logging
        logging.basicConfig(level=logging.INFO)
        self.logger = logging.getLogger("OntologyApp")

        # State variables
        self.source_file = tk.StringVar()
        self.owl_file = tk.StringVar()
        self.base_output_dir = tk.StringVar(value=str(Path.cwd() / "generated"))
        self.hydra_mode = tk.BooleanVar(value=False)
        self.version = tk.StringVar(value="1.0.0")
        self.status = tk.StringVar(value="Ready")

        # UI Setup
        self.create_widgets()
        self.ensure_output_dir()

    def create_widgets(self):
        style = ttk.Style()
        style.configure("TFrame", padding=5)
        style.configure("TLabel", padding=5)
        style.configure("TButton", padding=5)

        main_frame = ttk.Frame(self.root)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # File selection section
        file_frame = ttk.LabelFrame(main_frame, text="1. Select Source File", padding=10)
        file_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            file_frame,
            text="Browse (XML/YAML/JSON)",
            command=self.select_source_file
        ).pack(side=tk.LEFT)

        ttk.Label(
            file_frame,
            textvariable=self.source_file,
            wraplength=500,
            anchor=tk.W
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Conversion section
        convert_frame = ttk.LabelFrame(main_frame, text="2. Convert to OWL", padding=10)
        convert_frame.pack(fill=tk.X, pady=5)

        self.convert_btn = ttk.Button(
            convert_frame,
            text="Convert to OWL",
            command=self.convert_to_owl,
            state=tk.DISABLED
        )
        self.convert_btn.pack(side=tk.LEFT)

        ttk.Label(convert_frame, text="Version:").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Entry(convert_frame, textvariable=self.version, width=10).pack(side=tk.LEFT)

        ttk.Label(
            convert_frame,
            textvariable=self.owl_file,
            wraplength=400,
            anchor=tk.W
        ).pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)

        # Python generation section
        python_frame = ttk.LabelFrame(main_frame, text="3. Generate Python Code", padding=10)
        python_frame.pack(fill=tk.X, pady=5)

        ttk.Button(
            python_frame,
            text="Browse OWL File",
            command=self.select_owl_file
        ).pack(side=tk.LEFT)

        self.generate_btn = ttk.Button(
            python_frame,
            text="Generate Python",
            command=self.generate_python,
            state=tk.DISABLED
        )
        self.generate_btn.pack(side=tk.LEFT, padx=10)

        ttk.Checkbutton(
            python_frame,
            text="Enable Hydra",
            variable=self.hydra_mode
        ).pack(side=tk.LEFT)

        ttk.Label(python_frame, text="Output:").pack(side=tk.LEFT, padx=(20, 5))
        ttk.Entry(
            python_frame,
            textvariable=self.base_output_dir,
            width=30
        ).pack(side=tk.LEFT, fill=tk.X, expand=True)

        # Status bar
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
            title="Select Source File",
            filetypes=filetypes
        )

        if filename:
            self.source_file.set(filename)
            self.owl_file.set("")
            self.update_buttons()
            self.set_status(f"Selected: {Path(filename).name}")

    def select_owl_file(self):
        filename = filedialog.askopenfilename(
            title="Select OWL File",
            filetypes=[("OWL files", "*.owl"), ("All files", "*.*")]
        )

        if filename:
            self.owl_file.set(filename)
            self.update_buttons()
            self.set_status(f"Selected OWL: {Path(filename).name}")

    def update_buttons(self):
        self.convert_btn.config(
            state=tk.NORMAL if self.source_file.get() else tk.DISABLED
        )
        self.generate_btn.config(
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
            self.set_status("Converting to OWL...")
            output_file = Path(input_file).with_suffix(".owl")

            converter = OntologyConverter()
            converter.convert(input_file, str(output_file), version)

            self.owl_file.set(str(output_file))
            self.update_buttons()
            self.set_status(f"Converted to OWL (v{version})")
            messagebox.showinfo(
                "Success",
                f"Successfully converted to:\n{output_file}\nVersion: {version}",
                parent=self.root
            )
        except ValueError as e:
            messagebox.showerror(
                "Version Error",
                f"Invalid version format: {str(e)}\nUse semantic versioning (e.g. 1.0.0)",
                parent=self.root
            )
            self.set_status("Version error")
        except Exception as e:
            messagebox.showerror(
                "Conversion Error",
                str(e),
                parent=self.root
            )
            self.set_status("Conversion failed")

    def generate_python(self):
        owl_file = self.owl_file.get()
        base_output_dir = self.base_output_dir.get()
        hydra_mode = self.hydra_mode.get()

        try:
            self.ensure_output_dir()
            self.set_status("Generating Python code...")

            # Важное изменение: передаем None, чтобы converter взял версию из OWL-файла
            output_dir = generate_python_classes(
                owl_file=owl_file,
                base_output_dir=base_output_dir,
                hydra_mode=hydra_mode,
                version=None  # Берем версию из OWL-файла
            )

            self.set_status(f"Python code generated in: {output_dir}")
            messagebox.showinfo(
                "Success",
                f"Python code successfully generated in:\n{output_dir}",
                parent=self.root
            )
        except Exception as e:
            messagebox.showerror(
                "Generation Error",
                str(e),
                parent=self.root
            )
            self.set_status("Generation failed")


if __name__ == "__main__":
    root = tk.Tk()
    app = OntologyApp(root)
    root.mainloop()