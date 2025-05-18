from rdflib import Graph, RDF, RDFS, OWL, XSD, URIRef, Literal
from jinja2 import Template
from pathlib import Path
import logging
import yaml
from typing import Dict, List, Optional, Union, Any, Set
import semver
import sys
import importlib.util
from difflib import Differ
import json

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class OntologyDiff:
    @staticmethod
    def compare(old_g: Graph, new_g: Graph) -> Dict[str, Any]:
        diff = {
            'added_classes': set(),
            'removed_classes': set(),
            'changed_classes': {},
            'added_properties': set(),
            'removed_properties': set(),
            'changed_properties': {},
            'renamed': {}
        }

        old_classes = {str(c) for c in old_g.subjects(RDF.type, OWL.Class)}
        new_classes = {str(c) for c in new_g.subjects(RDF.type, OWL.Class)}

        old_props = {str(p) for p in old_g.subjects(RDF.type, (OWL.ObjectProperty, OWL.DatatypeProperty))}
        new_props = {str(p) for p in new_g.subjects(RDF.type, (OWL.ObjectProperty, OWL.DatatypeProperty))}

        diff['added_classes'] = new_classes - old_classes
        diff['removed_classes'] = old_classes - new_classes
        diff['added_properties'] = new_props - old_props
        diff['removed_properties'] = old_props - new_props

        diff['renamed'] = OntologyDiff._detect_renames(old_g, new_g, old_classes & new_classes)

        for cls in old_classes & new_classes:
            class_changes = OntologyDiff._compare_class(old_g, new_g, URIRef(cls))
            if class_changes:
                diff['changed_classes'][cls] = class_changes

        for prop in old_props & new_props:
            prop_changes = OntologyDiff._compare_property(old_g, new_g, URIRef(prop))
            if prop_changes:
                diff['changed_properties'][prop] = prop_changes

        return diff

    @staticmethod
    def _detect_renames(old_g: Graph, new_g: Graph, common_classes: Set[str]) -> Dict[str, str]:
        renames = {}
        d = Differ()

        for cls in common_classes:
            old_label = str(old_g.value(URIRef(cls), RDFS.label) or "")
            new_label = str(new_g.value(URIRef(cls), RDFS.label) or "")

            if old_label and new_label and old_label != new_label:
                similarity = sum(1 for s in d.compare(old_label, new_label) if s.startswith(' ')) / max(len(old_label),
                                                                                                        len(new_label))
                if similarity > 0.5:
                    renames[cls] = new_label

        return renames

    @staticmethod
    def _compare_class(old_g: Graph, new_g: Graph, class_uri: URIRef) -> Dict[str, Any]:
        changes = {}

        old_parents = {str(p) for p in old_g.objects(class_uri, RDFS.subClassOf)}
        new_parents = {str(p) for p in new_g.objects(class_uri, RDFS.subClassOf)}

        if old_parents != new_parents:
            changes['parents'] = {
                'added': list(new_parents - old_parents),
                'removed': list(old_parents - new_parents)
            }

        return changes

    @staticmethod
    def _compare_property(old_g: Graph, new_g: Graph, prop_uri: URIRef) -> Dict[str, Any]:
        changes = {}

        old_domain = str(old_g.value(prop_uri, RDFS.domain)) if old_g.value(prop_uri, RDFS.domain) else None
        new_domain = str(new_g.value(prop_uri, RDFS.domain)) if new_g.value(prop_uri, RDFS.domain) else None

        if old_domain != new_domain:
            changes['domain'] = {'old': old_domain, 'new': new_domain}

        old_range = str(old_g.value(prop_uri, RDFS.range)) if old_g.value(prop_uri, RDFS.range) else None
        new_range = str(new_g.value(prop_uri, RDFS.range)) if new_g.value(prop_uri, RDFS.range) else None

        if old_range != new_range:
            changes['range'] = {'old': old_range, 'new': new_range}

        old_type = 'ObjectProperty' if (prop_uri, RDF.type, OWL.ObjectProperty) in old_g else 'DatatypeProperty'
        new_type = 'ObjectProperty' if (prop_uri, RDF.type, OWL.ObjectProperty) in new_g else 'DatatypeProperty'

        if old_type != new_type:
            changes['type'] = {'old': old_type, 'new': new_type}

        return changes


class OntologyVersionManager:
    @staticmethod
    def load_version(g: Graph) -> str:
        version = g.value(URIRef("http://example.org/ontology#Ontology"), OWL.versionInfo)
        return str(version) if version else "1.0.0"

    @staticmethod
    def generate_migration_rules(old_g: Graph, new_g: Graph) -> Dict[str, Any]:
        diff = OntologyDiff.compare(old_g, new_g)
        rules = {
            'field_renames': {},
            'type_changes': {},
            'default_values': {},
            'removed_fields': {},
            'added_fields': {},
            'class_changes': {}
        }

        for prop_uri, changes in diff['changed_properties'].items():
            prop_name = prop_uri.split('#')[-1]

            if 'range' in changes:
                rules['type_changes'][prop_name] = {
                    'old': OntologyVersionManager._uri_to_type(changes['range']['old']),
                    'new': OntologyVersionManager._uri_to_type(changes['range']['new'])
                }

            if 'domain' in changes:
                rules['domain_changes'] = rules.get('domain_changes', {})
                rules['domain_changes'][prop_name] = {
                    'old': changes['domain']['old'].split('#')[-1],
                    'new': changes['domain']['new'].split('#')[-1]
                }

        for prop_uri in diff['added_properties']:
            prop_name = prop_uri.split('#')[-1]
            range_uri = str(new_g.value(URIRef(prop_uri), RDFS.range)) if new_g.value(URIRef(prop_uri),
                                                                                      RDFS.range) else None
            rules['added_fields'][prop_name] = {
                'type': OntologyVersionManager._uri_to_type(range_uri),
                'default': OntologyVersionManager._get_default_value(range_uri)
            }

        for prop_uri in diff['removed_properties']:
            prop_name = prop_uri.split('#')[-1]
            rules['removed_fields'][prop_name] = True

        for cls_uri, changes in diff['changed_classes'].items():
            cls_name = cls_uri.split('#')[-1]
            rules['class_changes'][cls_name] = changes

        for old_uri, new_name in diff['renamed'].items():
            old_name = old_uri.split('#')[-1]
            rules['field_renames'][old_name] = new_name

        return rules

    @staticmethod
    def _uri_to_type(uri: str) -> str:
        if not uri:
            return 'Any'
        if 'xsd' in uri:
            if 'string' in uri: return 'str'
            if 'integer' in uri: return 'int'
            if 'float' in uri: return 'float'
            if 'boolean' in uri: return 'bool'
            if 'date' in uri: return 'date'
        return 'Any'

    @staticmethod
    def _get_default_value(uri: str) -> Any:
        if not uri:
            return None
        if 'xsd' in uri:
            if 'string' in uri: return ""
            if 'integer' in uri: return 0
            if 'float' in uri: return 0.0
            if 'boolean' in uri: return False
        return None


class OwlToPythonConverter:
    def __init__(self):
        self.ns = {}
        self.class_hierarchy = {}
        self.current_version = "1.0.0"
        self.properties_info = []
        self.classes_info = []
        self.previous_version = None
        self.migration_rules = {}

    def _create_output_dir(self, ontology_name: str, base_dir: str, folder_prefix: Optional[str] = None) -> Path:
        """Создает папку для выходных файлов с кастомным именем и версией"""
        version_suffix = f"v{self.current_version.replace('.', '_')}"
        dir_name = f"{folder_prefix or ontology_name}_{version_suffix}"
        output_dir = Path(base_dir) / dir_name
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def convert(self, owl_file: str, base_output_dir: str = "generated",
                hydra_mode: bool = False, version: str = None,
                previous_version: str = None, folder_prefix: str = None) -> str:
        try:
            owl_path = Path(owl_file)
            self._validate_input(owl_path)

            g = Graph()
            self._parse_owl(g, owl_path)
            self.current_version = version or OntologyVersionManager.load_version(g)

            if previous_version:
                self._load_previous_version(previous_version, g)

            output_dir = self._create_output_dir(
                ontology_name=owl_path.stem,
                base_dir=base_output_dir,
                folder_prefix=folder_prefix
            )

            self._extract_namespaces(g)
            self._build_class_hierarchy(g)
            self.classes_info = self._extract_classes(g)
            self.properties_info = self._extract_properties(g)

            self._generate_model_file(output_dir, hydra_mode)

            if hydra_mode:
                self._generate_hydra_config(output_dir)
                self._generate_compatibility_layer(output_dir)

            self._create_init_file(output_dir)
            self._generate_changelog(output_dir)

            logger.info(f"Successfully generated code in: {output_dir}")
            return str(output_dir)
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
            raise

    def _load_previous_version(self, previous_version: str, current_g: Graph):
        prev_owl = Path(previous_version)
        if not prev_owl.exists():
            logger.warning(f"Previous version not found: {previous_version}")
            return

        prev_g = Graph()
        prev_g.parse(prev_owl)
        self.previous_version = OntologyVersionManager.load_version(prev_g)
        self.migration_rules = OntologyVersionManager.generate_migration_rules(prev_g, current_g)

    def _generate_changelog(self, output_dir: Path):
        if not self.migration_rules:
            return

        changelog = [
            "# Ontology Version Migration Guide",
            f"## From {self.previous_version} to {self.current_version}\n"
        ]

        if self.migration_rules.get('field_renames'):
            changelog.append("### Renamed Fields")
            for old, new in self.migration_rules['field_renames'].items():
                changelog.append(f"- `{old}` → `{new}`")

        if self.migration_rules.get('added_fields'):
            changelog.append("\n### Added Fields")
            for field, info in self.migration_rules['added_fields'].items():
                changelog.append(f"- `{field}` ({info['type']}) - default: `{info['default']}`")

        if self.migration_rules.get('removed_fields'):
            changelog.append("\n### Removed Fields")
            for field in self.migration_rules['removed_fields']:
                changelog.append(f"- `{field}`")

        if self.migration_rules.get('type_changes'):
            changelog.append("\n### Type Changes")
            for field, change in self.migration_rules['type_changes'].items():
                changelog.append(f"- `{field}`: {change['old']} → {change['new']}")

        (output_dir / "CHANGES.md").write_text("\n".join(changelog), encoding='utf-8')

    def _generate_compatibility_layer(self, output_dir: Path):
        template = Template('''# Auto-generated compatibility layer
from typing import Dict, Any, Union
from dataclasses import asdict
import semver

class OntologyAdapter:
    """Handle version migrations between ontology versions"""
    CURRENT_VERSION = "{{ version }}"
    MIGRATION_RULES = {{ migration_rules|tojson }}

    @classmethod
    def migrate(cls, old_data: Dict[str, Any], old_version: str) -> Dict[str, Any]:
        if old_version == cls.CURRENT_VERSION:
            return old_data

        migrated = old_data.copy()

        # Apply field renames
        for old_field, new_field in cls.MIGRATION_RULES.get('field_renames', {}).items():
            for entity_type, entity_data in migrated.items():
                if old_field in entity_data:
                    entity_data[new_field] = entity_data.pop(old_field)

        # Set defaults for new fields
        for entity_type, entity_data in migrated.items():
            for new_field, field_info in cls.MIGRATION_RULES.get('added_fields', {}).items():
                entity_data.setdefault(new_field, field_info['default'])

        # Handle type conversions
        for field, type_change in cls.MIGRATION_RULES.get('type_changes', {}).items():
            for entity_type, entity_data in migrated.items():
                if field in entity_data:
                    try:
                        if type_change['old'] == 'int' and type_change['new'] == 'float':
                            entity_data[field] = float(entity_data[field])
                        elif type_change['old'] == 'str' and type_change['new'] == 'int':
                            entity_data[field] = int(entity_data[field])
                        elif type_change['old'] == 'float' and type_change['new'] == 'int':
                            entity_data[field] = int(entity_data[field])
                    except (ValueError, TypeError):
                        entity_data[field] = cls.MIGRATION_RULES['added_fields'].get(field, {}).get('default')

        return migrated

    @staticmethod
    def to_dict(obj) -> Dict[str, Any]:
        return asdict(obj)

    @staticmethod
    def from_dict(data: Dict[str, Any], target_class):
        return target_class(**data)
''')

        (output_dir / "compatibility.py").write_text(template.render(
            version=self.current_version,
            migration_rules=json.loads(json.dumps(self.migration_rules, default=str))
        ), encoding='utf-8')

    def _validate_input(self, owl_path: Path):
        if not owl_path.exists():
            raise FileNotFoundError(f"OWL file not found: {owl_path}")
        if owl_path.suffix != '.owl':
            raise ValueError("Input file must have .owl extension")

    def _parse_owl(self, g: Graph, owl_path: Path):
        try:
            g.parse(owl_path)
        except Exception as e:
            raise ValueError(f"Failed to parse OWL file: {str(e)}")

    def _extract_namespaces(self, g: Graph):
        for prefix, uri in g.namespaces():
            self.ns[prefix] = uri

    def _build_class_hierarchy(self, g: Graph):
        for cls in g.subjects(RDF.type, OWL.Class):
            self.class_hierarchy[str(cls)] = []

        for sub_class, _, super_class in g.triples((None, RDFS.subClassOf, None)):
            if str(sub_class) in self.class_hierarchy:
                self.class_hierarchy[str(sub_class)].append(str(super_class))

    def _extract_classes(self, g: Graph) -> List[Dict]:
        classes = []
        for class_uri in g.subjects(RDF.type, OWL.Class):
            class_name = self._uri_to_name(class_uri)
            classes.append({
                "name": class_name,
                "uri": str(class_uri),
                "parent_classes": [
                    self._uri_to_name(uri)
                    for uri in self.class_hierarchy.get(str(class_uri), [])
                ],
                "comment": self._get_class_comment(g, class_uri)
            })
        return classes

    def _extract_properties(self, g: Graph) -> List[Dict]:
        properties = []
        for prop in g.subjects(RDF.type, OWL.ObjectProperty):
            properties.append(self._process_property(g, prop, "ObjectProperty"))
        for prop in g.subjects(RDF.type, OWL.DatatypeProperty):
            properties.append(self._process_property(g, prop, "DatatypeProperty"))
        return properties

    def _process_property(self, g: Graph, prop: URIRef, prop_type: str) -> Dict:
        prop_name = self._uri_to_name(prop)
        domain = self._get_property_domain(g, prop)
        range_ = self._get_property_range(g, prop, prop_type)

        return {
            "name": prop_name,
            "type": prop_type,
            "domain": domain,
            "range": range_,
            "comment": self._get_property_comment(g, prop)
        }

    def _generate_model_file(self, output_dir: Path, hydra_mode: bool):
        template = Template('''# Auto-generated from OWL ontology
from dataclasses import dataclass, field
from typing import List, Optional, Union
{% if hydra_mode %}
from omegaconf import DictConfig
{% endif %}

{% for cls in classes %}
@dataclass
class {{ cls.name }}{% if cls.parent_classes %}({{ cls.parent_classes|join(', ') }}){% endif %}:
    """{{ cls.comment or cls.name }}"""
    {% for prop in properties if prop.domain == cls.name %}
    {% if cls.name == 'Department' and prop.name == 'name' %}
    name: str = field(default="Unnamed Department")
    {% else %}
    {{ prop.name }}: {% if prop.type == 'ObjectProperty' %}{% if prop.range == cls.name %}List['{{ prop.range }}']{% else %}Optional['{{ prop.range }}']{% endif %}{% else %}{{ prop.range }}{% endif %} = field(
        default={% if prop.range == 'bool' %}False{% elif prop.range == 'str' %}""{% elif prop.range == 'int' %}0{% elif prop.type == 'ObjectProperty' %}None{% else %}None{% endif %},
        metadata={"hydra": {"key": "{{ prop.name }}"}} if {{ hydra_mode }} else {}
    )
    """{{ prop.comment or prop.name }} ({{ prop.type }})"""
    {% endif %}
    {% endfor %}

    @classmethod
    def from_config(cls, cfg{% if hydra_mode %}: DictConfig{% endif %}):
        return cls(
            {% for prop in properties if prop.domain == cls.name %}
            {{ prop.name }}=cfg.{{ prop.name }}{% if not loop.last %},{% endif %}
            {% endfor %}
        )
{% endfor %}
''')

        (output_dir / "ontology_model.py").write_text(template.render(
            classes=self.classes_info,
            properties=self.properties_info,
            hydra_mode=hydra_mode
        ), encoding='utf-8')

    def _generate_hydra_config(self, output_dir: Path):
        config_dir = output_dir / "hydra_config"
        config_dir.mkdir(exist_ok=True)

        for cls in self.classes_info:
            config = {
                cls["name"]: {
                    "name": cls["name"],
                    "version": self.current_version,
                    "properties": {
                        prop["name"]: {
                            "type": prop["type"],
                            "range": prop["range"],
                            "comment": prop.get("comment", "")
                        }
                        for prop in self.properties_info
                        if prop["domain"] == cls["name"]
                    }
                }
            }
            (config_dir / f"{cls['name'].lower()}.yaml").write_text(yaml.dump(config, sort_keys=False),
                                                                    encoding='utf-8')

    def _create_init_file(self, output_dir: Path):
        (output_dir / "__init__.py").write_text(
            "from .ontology_model import *\n"
            "from .compatibility import OntologyAdapter\n"
            "__all__ = ['OntologyAdapter'] + "
            "[name for name in dir() if not name.startswith('_')]",
            encoding='utf-8'
        )

    def _uri_to_name(self, uri: Union[URIRef, str]) -> str:
        uri_str = str(uri)
        return uri_str.split('#')[-1] if '#' in uri_str else uri_str.split('/')[-1]

    def _get_class_comment(self, g: Graph, class_uri: URIRef) -> Optional[str]:
        comment = g.value(class_uri, RDFS.comment)
        return str(comment) if comment else None

    def _get_property_comment(self, g: Graph, prop: URIRef) -> Optional[str]:
        comment = g.value(prop, RDFS.comment)
        return str(comment) if comment else None

    def _get_property_domain(self, g: Graph, prop: URIRef) -> Optional[str]:
        domain = g.value(prop, RDFS.domain)
        return self._uri_to_name(domain) if domain else None

    def _get_property_range(self, g: Graph, prop: URIRef, prop_type: str) -> str:
        if prop_type == "DatatypeProperty":
            range_ = g.value(prop, RDFS.range)
            if str(range_) == str(XSD.string):
                return "str"
            elif str(range_) == str(XSD.integer):
                return "int"
            elif str(range_) == str(XSD.float):
                return "float"
            elif str(range_) == str(XSD.date):
                return "date"
            elif str(range_) == str(XSD.dateTime):
                return "datetime"
            elif str(range_) == str(XSD.boolean):
                return "bool"
            return "str"
        else:
            range_ = g.value(prop, RDFS.range)
            return self._uri_to_name(range_) if range_ else "Any"


def generate_python_classes(owl_file: str, base_output_dir: str = "generated",
                          hydra_mode: bool = False, version: str = None,
                          previous_version: str = None, folder_prefix: str = None) -> str:
    converter = OwlToPythonConverter()
    return converter.convert(
        owl_file=owl_file,
        base_output_dir=base_output_dir,
        hydra_mode=hydra_mode,
        version=version,
        previous_version=previous_version,
        folder_prefix=folder_prefix
    )

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert OWL ontology to Python classes")
    parser.add_argument("owl_file", help="Path to input OWL file")
    parser.add_argument("--output", default="generated", help="Output directory")
    parser.add_argument("--hydra", action="store_true", help="Enable Hydra support")
    parser.add_argument("--version", help="Override ontology version")
    parser.add_argument("--previous", help="Path to previous version OWL file for migration")
    parser.add_argument("--prefix", help="Custom folder name prefix")
    args = parser.parse_args()

    try:
        output_path = generate_python_classes(
            args.owl_file,
            args.output,
            args.hydra,
            args.version,
            args.previous,
            args.prefix
        )
        print(f"Successfully generated code in: {output_path}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)
