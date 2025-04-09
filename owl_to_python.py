from rdflib import Graph, RDF, RDFS, OWL
from jinja2 import Template
from pathlib import Path
import logging


def generate_python_classes(owl_file: str) -> None:
    """
    Генерация Python-классов из OWL-файла
    Args:
        owl_file: Путь к OWL-файлу (относительный или абсолютный)
    """
    # 1. Проверка и нормализация пути
    owl_path = Path(owl_file).absolute()
    if not owl_path.exists():
        raise FileNotFoundError(f"OWL файл не найден по пути: {owl_path}")
    if not owl_path.is_file():
        raise ValueError(f"Указанный путь не является файлом: {owl_path}")

    # 2. Загрузка и парсинг OWL
    g = Graph()
    try:
        g.parse(owl_path)
        logging.info(f"Успешно загружен OWL-файл: {owl_path}")
    except Exception as e:
        raise ValueError(f"Ошибка парсинга OWL-файла: {str(e)}")

    # 3. Извлечение классов
    classes = set()
    for cls in g.subjects(RDF.type, OWL.Class):
        class_name = str(cls).split("#")[-1].split("/")[-1]
        if class_name:
            classes.add(class_name)

    # 4. Извлечение свойств
    properties = []
    for prop in g.subjects(RDF.type, OWL.ObjectProperty):
        prop_name = str(prop).split("#")[-1].split("/")[-1]
        domain = g.value(prop, RDFS.domain)
        range_ = g.value(prop, RDFS.range)

        domain_name = str(domain).split("#")[-1].split("/")[-1] if domain else None
        range_name = str(range_).split("#")[-1].split("/")[-1] if range_ else None

        properties.append({
            "name": prop_name,
            "domain": domain_name,
            "range": range_name
        })

    # 5. Генерация Python-кода
    template = Template("""
# Автосгенерированный код из OWL
# Источник: {{ owl_file }}
from dataclasses import dataclass
from typing import Dict

{% for class_name in classes %}
@dataclass
class {{ class_name }}:
    \"\"\"Класс {{ class_name }} из онтологии\"\"\"
    pass
{% endfor %}

class OntologyModel:
    \"\"\"Модель онтологии со связями\"\"\"

    def __init__(self):
        {% for prop in properties %}
        self.{{ prop.name }}: Dict[{% if prop.domain %}{{ prop.domain }}{% else %}str{% endif %}, {% if prop.range %}{{ prop.range }}{% else %}str{% endif %}] = {}
        \"\"\"{{ prop.name }}: {{ prop.domain }} -> {{ prop.range }}\"\"\"
        {% endfor %}
""")

    generated_code = template.render(
        owl_file=str(owl_path),
        classes=sorted(classes),
        properties=properties
    )

    # 6. Сохранение результата
    output_path = owl_path.parent / "generated" / "ontology_model.py"
    output_path.parent.mkdir(exist_ok=True)

    try:
        with open(output_path, "w", encoding="utf-8") as f:
            f.write(generated_code)
        logging.info(f"Python-код успешно сгенерирован: {output_path}")
    except IOError as e:
        raise IOError(f"Ошибка записи в файл {output_path}: {str(e)}")


if __name__ == "__main__":
    # Пример использования
    try:
        generate_python_classes("university_ontology_v1.owl")
    except Exception as e:
        print(f"Ошибка: {str(e)}")