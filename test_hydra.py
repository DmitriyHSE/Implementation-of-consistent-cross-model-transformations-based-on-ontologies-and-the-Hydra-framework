import os
import ast
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any

BASE_DIR = Path(__file__).parent
GENERATED_DIR = BASE_DIR / "generated"


def parse_version(version_str: str) -> Tuple[int, ...]:
    """Преобразует строку версии в кортеж чисел для сравнения"""
    parts = []
    for part in version_str.split('.'):
        if part.isdigit():
            parts.append(int(part))
        else:
            parts.append(0)
    while len(parts) < 3:
        parts.append(0)
    return tuple(parts[:3])


def extract_ontology_info(dir_name: str) -> Tuple[str, str]:
    """Извлекает название онтологии и версию из имени папки"""
    # Поддерживаем форматы: prefix_v1, prefix_v1_0, prefix_v1_0_0
    if '_v' in dir_name:
        parts = dir_name.split('_v')
        prefix = parts[0]
        version = parts[1].replace('_', '.')
    else:
        prefix = dir_name
        version = "0.0.0"
    return prefix, version


def analyze_ontology(file_path: Path) -> Dict[str, Dict[str, str]]:
    """Анализирует файл ontology_model.py и возвращает структуру классов с типами"""
    if not file_path.exists():
        return {}

    with open(file_path, 'r', encoding='utf-8') as f:
        tree = ast.parse(f.read(), filename=str(file_path))

    classes = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            fields = {}
            for item in node.body:
                if isinstance(item, ast.AnnAssign):
                    if isinstance(item.target, ast.Name):
                        field_name = item.target.id
                        if isinstance(item.annotation, ast.Name):
                            field_type = item.annotation.id
                        elif isinstance(item.annotation, ast.Subscript):
                            field_type = ast.unparse(item.annotation)
                        else:
                            field_type = "Any"
                        fields[field_name] = field_type
            classes[node.name] = fields
    return classes


def compare_versions(versions: List[Tuple[str, Dict[str, Dict[str, str]]]]) -> List[Dict[str, Any]]:
    """Сравнивает последовательные версии и возвращает список изменений"""
    changes = []
    for i in range(1, len(versions)):
        old_ver, old_data = versions[i - 1]
        new_ver, new_data = versions[i]

        diff = {
            'from_version': old_ver,
            'to_version': new_ver,
            'added_classes': set(),
            'removed_classes': set(),
            'changed_classes': {},
            'type_changes': {}
        }

        old_classes = set(old_data.keys())
        new_classes = set(new_data.keys())

        diff['added_classes'] = new_classes - old_classes
        diff['removed_classes'] = old_classes - new_classes

        for cls in old_classes & new_classes:
            old_fields = old_data[cls]
            new_fields = new_data[cls]

            added = set(new_fields.keys()) - set(old_fields.keys())
            removed = set(old_fields.keys()) - set(new_fields.keys())
            changed = {}

            for field in set(old_fields.keys()) & set(new_fields.keys()):
                if old_fields[field] != new_fields[field]:
                    changed[field] = {
                        'old': old_fields[field],
                        'new': new_fields[field]
                    }

            if added or removed or changed:
                diff['changed_classes'][cls] = {
                    'added': added,
                    'removed': removed,
                    'changed': changed
                }

            if changed:
                diff['type_changes'][cls] = changed

        changes.append(diff)
    return changes


def generate_report(ontology_name: str, changes: List[Dict[str, Any]]) -> str:
    """Формирует читаемый отчет об изменениях"""
    if not changes:
        return f"\nДля онтологии '{ontology_name}' не найдено изменений между версиями"

    report = [f"\nОтчет для онтологии: {ontology_name}"]

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
            if details['changed']:
                for field, types in details['changed'].items():
                    report.append(f"    ~ Изменен тип поля {field}: {types['old']} → {types['new']}")

    return "\n".join(report)


def main():
    print("=== Анализатор версий онтологий ===")

    if not GENERATED_DIR.exists():
        print(f"Ошибка: папка '{GENERATED_DIR}' не найдена!")
        return

    ontologies = {}
    for dir_name in os.listdir(GENERATED_DIR):
        dir_path = GENERATED_DIR / dir_name
        if dir_path.is_dir():
            ontology_name, version = extract_ontology_info(dir_name)
            model_data = analyze_ontology(dir_path / "ontology_model.py")
            if model_data:
                if ontology_name not in ontologies:
                    ontologies[ontology_name] = []
                ontologies[ontology_name].append((version, model_data))

    if not ontologies:
        print("Не найдено ни одной онтологии!")
        return

    for name, versions in ontologies.items():
        versions.sort(key=lambda x: parse_version(x[0]))
        changes = compare_versions(versions)
        print(generate_report(name, changes))


if __name__ == "__main__":
    main()