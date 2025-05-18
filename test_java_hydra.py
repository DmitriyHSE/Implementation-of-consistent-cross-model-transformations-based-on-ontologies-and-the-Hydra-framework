import os
import javalang
from pathlib import Path
from typing import Dict, List, Set, Tuple, Any
import semver

BASE_DIR = Path(__file__).parent
GENERATED_DIR = BASE_DIR / "generated"


def parse_version(version_str: str) -> Tuple[int, ...]:
    try:
        return semver.VersionInfo.parse(version_str).to_tuple()
    except ValueError:
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
    if '_v' in dir_name:
        parts = dir_name.split('_v')
        prefix = parts[0]
        version = parts[1].replace('_', '.')
    else:
        prefix = dir_name
        version = "0.0.0"
    return prefix, version


def analyze_java_classes(java_file: Path) -> Dict[str, Dict[str, str]]:
    if not java_file.exists():
        return {}

    with open(java_file, 'r', encoding='utf-8') as f:
        content = f.read()

    try:
        tree = javalang.parse.parse(content)
    except javalang.parser.JavaSyntaxError as e:
        print(f"Error parsing Java file {java_file}: {e}")
        return {}

    classes = {}
    for path, node in tree.filter(javalang.tree.ClassDeclaration):
        class_name = node.name
        fields = {}

        # Обрабатываем поля класса
        for field in node.fields:
            field_type = str(field.type)
            for declarator in field.declarators:
                fields[declarator.name] = field_type

        classes[class_name] = {
            'fields': fields,
            'file_path': str(java_file)
        }

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
            'changed_classes': {},
            'type_changes': {},
            'moved_classes': {}
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
            changed = {}

            for field in set(old_fields.keys()) & set(new_fields.keys()):
                if old_fields[field] != new_fields[field]:
                    changed[field] = {
                        'old': old_fields[field],
                        'new': new_fields[field]
                    }

            file_changed = old_data[cls]['file_path'] != new_data[cls]['file_path']

            if added or removed or changed or file_changed:
                diff['changed_classes'][cls] = {
                    'added': added,
                    'removed': removed,
                    'changed': changed,
                    'file_changed': file_changed
                }

            if changed:
                diff['type_changes'][cls] = changed

            if file_changed:
                diff['moved_classes'][cls] = {
                    'old_path': old_data[cls]['file_path'],
                    'new_path': new_data[cls]['file_path']
                }

        changes.append(diff)
    return changes


def generate_report(ontology_name: str, changes: List[Dict[str, Any]]) -> str:
    if not changes:
        return f"\nДля онтологии '{ontology_name}' не найдено изменений между версиями"

    report = [
        f"\nОтчет по изменениям онтологии: {ontology_name}",
        "=" * 50
    ]

    for change in changes:
        report.append(
            f"\nИзменения между версиями {change['from_version']} → {change['to_version']}:"
        )
        report.append("-" * 60)

        if change['added_classes']:
            report.append("\nДобавленные классы:")
            for cls in sorted(change['added_classes']):
                report.append(f"  + {cls}")

        if change['removed_classes']:
            report.append("\nУдаленные классы:")
            for cls in sorted(change['removed_classes']):
                report.append(f"  - {cls}")

        if change['moved_classes']:
            report.append("\nПеремещенные классы:")
            for cls, paths in change['moved_classes'].items():
                report.append(f"  > {cls}:")
                report.append(f"      из: {paths['old_path']}")
                report.append(f"      в:  {paths['new_path']}")

        for cls, details in change['changed_classes'].items():
            report.append(f"\nИзменения в классе {cls}:")

            if details['added']:
                report.append("  Добавленные поля:")
                for field in sorted(details['added']):
                    report.append(f"    + {field}")

            if details['removed']:
                report.append("  Удаленные поля:")
                for field in sorted(details['removed']):
                    report.append(f"    - {field}")

            if details['changed']:
                report.append("  Измененные типы полей:")
                for field, types in details['changed'].items():
                    report.append(f"    ~ {field}: {types['old']} → {types['new']}")

            if details['file_changed']:
                report.append("  Класс перемещен в другой файл")

    return "\n".join(report)


def collect_java_files(base_dir: Path) -> Dict[str, Any]:
    ontology_data = {}

    for dir_name in os.listdir(base_dir):
        dir_path = base_dir / dir_name
        if dir_path.is_dir():
            ontology_name, version = extract_ontology_info(dir_name)
            java_files = list((dir_path / "src/main/java").rglob("*.java"))

            if not java_files:
                continue

            if ontology_name not in ontology_data:
                ontology_data[ontology_name] = []

            classes_data = {}
            for java_file in java_files:
                file_classes = analyze_java_classes(java_file)
                classes_data.update(file_classes)

            if classes_data:
                ontology_data[ontology_name].append((version, classes_data))

    return ontology_data


def main():
    print("=== Анализатор версий Java онтологий ===")
    print(f"Поиск онтологий в директории: {GENERATED_DIR}")

    if not GENERATED_DIR.exists():
        print(f"Ошибка: директория '{GENERATED_DIR}' не найдена!")
        return

    ontologies = collect_java_files(GENERATED_DIR)

    if not ontologies:
        print("Не найдено ни одной онтологии в Java формате!")
        return

    for name, versions in ontologies.items():
        versions.sort(key=lambda x: parse_version(x[0]))

        if len(versions) < 2:
            print(f"\nДля онтологии '{name}' найдена только одна версия {versions[0][0]}")
            continue

        changes = compare_versions(versions)
        print(generate_report(name, changes))


if __name__ == "__main__":
    main()