import os
import logging
from pathlib import Path
from typing import Dict, List, Tuple, Any
import pytest
from owl_to_cpp import generate_cpp_from_owl

BASE_DIR = Path(__file__).parent
GENERATED_DIR = BASE_DIR / "generated"
logger = logging.getLogger(__name__)

VERSION_1 = "1.0.0"
VERSION_2 = "1.1.0"
ONTOLOGY_NAME = "SampleOntology"


def parse_version(version_str: str) -> Tuple[int, ...]:
    parts = []
    for part in version_str.split('.'):
        if part.isdigit():
            parts.append(int(part))
        else:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def analyze_cpp_classes(file_path: Path) -> Dict[str, Dict[str, str]]:
    if not file_path.exists():
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    classes = {}
    for line in content.splitlines():
        if "class" in line:
            class_name = line.split("class")[1].strip().split("{")[0]
            classes[class_name] = {
                'fields': {},
                'methods': []
            }

        if "std::string" in line or "int" in line or "float" in line:
            parts = line.split(" ")
            field_type = parts[0]
            field_name = parts[1].strip(';')
            classes[class_name]['fields'][field_name] = field_type

    return classes


def compare_versions(versions: List[Tuple[str, Dict[str, Any]]]) -> List[Dict[str, Any]]:
    changes = []
    for i in range(1, len(versions)):
        old_ver, old_data = versions[i - 1]
        new_ver, new_data = versions[i]

        diff = {
            'from_version': old_ver,
            'to_version': new_ver,
            'added_classes': set(),
            'removed_classes': set(),
            'changed_classes': {}
        }

        old_classes = set(old_data.keys())
        new_classes = set(new_data.keys())

        diff['added_classes'] = new_classes - old_classes
        diff['removed_classes'] = old_classes - new_classes

        for cls in old_classes & new_classes:
            old_fields = old_data[cls]['fields']
            new_fields = new_data[cls]['fields']

            added = set(new_fields.keys()) - set(old_fields.keys())
            removed = set(old_fields.keys()) - set(new_fields.keys())

            if added or removed:
                diff['changed_classes'][cls] = {
                    'added': added,
                    'removed': removed
                }

        changes.append(diff)
    return changes


def generate_report(changes: List[Dict[str, Any]]) -> str:
    if not changes:
        return "\nНет изменений между версиями"

    report = []
    for change in changes:
        report.append(f"\nИзменения {change['from_version']} → {change['to_version']}:")
        if change['added_classes']:
            report.append(f"  + Добавлены классы: {', '.join(change['added_classes'])}")
        if change['removed_classes']:
            report.append(f"  - Удалены классы: {', '.join(change['removed_classes'])}")

        for cls, details in change['changed_classes'].items():
            report.append(f"\n  Изменения в классе {cls}:")
            if details['added']:
                report.append(f"    + Добавлены поля: {', '.join(details['added'])}")
            if details['removed']:
                report.append(f"    - Удалены поля: {', '.join(details['removed'])}")

    return "\n".join(report)


def collect_cpp_classes(base_dir: Path) -> Dict[str, Any]:
    ontology_data = {}

    for dir_name in os.listdir(base_dir):
        dir_path = base_dir / dir_name
        if dir_path.is_dir():
            ontology_name, version = dir_name.split('_v')
            src_dir = dir_path / "src"
            cpp_files = list(src_dir.rglob("*.cpp"))

            if not cpp_files:
                continue

            if ontology_name not in ontology_data:
                ontology_data[ontology_name] = []

            classes_data = {}
            for cpp_file in cpp_files:
                file_classes = analyze_cpp_classes(cpp_file)
                classes_data.update(file_classes)

            if classes_data:
                ontology_data[ontology_name].append((version, classes_data))

    return ontology_data


def test_cpp_hydra():
    print("=== Анализ изменений в версиях C++ онтологии ===")
    print(f"Поиск онтологий в директории: {GENERATED_DIR}")

    if not GENERATED_DIR.exists():
        print(f"Ошибка: директория '{GENERATED_DIR}' не найдена!")
        return

    ontologies = collect_cpp_classes(GENERATED_DIR)

    if not ontologies:
        print("Не найдено ни одной онтологии C++!")
        return

    for name, versions in ontologies.items():
        versions.sort(key=lambda x: parse_version(x[0]))

        if len(versions) < 2:
            print(f"\nДля онтологии '{name}' найдена только одна версия {versions[0][0]}")
            continue

        changes = compare_versions(versions)
        print(generate_report(changes))


if __name__ == "__main__":
    test_cpp_hydra()
