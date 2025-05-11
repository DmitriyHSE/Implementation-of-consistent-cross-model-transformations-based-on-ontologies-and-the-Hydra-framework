from rdflib import Graph, RDF, RDFS, OWL, XSD, URIRef, Literal
from jinja2 import Template
from pathlib import Path
import logging
import yaml
from typing import Dict, List, Optional, Union, Any
import semver
import sys
import importlib.util

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class OntologyVersionManager:
    @staticmethod
    def load_version(g: Graph) -> str:
        """Load ontology version from RDF graph"""
        version = g.value(URIRef("http://example.org/ontology#Ontology"), OWL.versionInfo)
        return str(version) if version else "1.0.0"

    @staticmethod
    def get_migration_rules(version: str) -> Dict[str, Dict[str, str]]:
        """Get migration rules for specific version"""
        rules = {
            "2.0.0": {
                "University": {
                    "established": "founding_year"
                }
            }
        }
        return rules.get(version, {})


class OwlToPythonConverter:
    def __init__(self):
        """Initialize converter with default values"""
        self.ns = {}
        self.class_hierarchy = {}
        self.current_version = "1.0.0"
        self.properties_info = []
        self.classes_info = []

    def convert(self, owl_file: str, base_output_dir: str = "generated",
                hydra_mode: bool = False, version: str = None) -> str:
        """Main conversion method"""
        try:
            owl_path = Path(owl_file)
            self._validate_input(owl_path)

            g = Graph()
            self._parse_owl(g, owl_path)
            self.current_version = version or OntologyVersionManager.load_version(g)

            output_dir = self._create_output_dir(owl_path.stem, base_output_dir)
            self._extract_namespaces(g)
            self._build_class_hierarchy(g)
            self.classes_info = self._extract_classes(g)
            self.properties_info = self._extract_properties(g)

            self._generate_model_file(output_dir, hydra_mode)

            if hydra_mode:
                self._generate_hydra_config(output_dir)
                self._generate_compatibility_layer(output_dir)

            self._create_init_file(output_dir)

            logger.info(f"Successfully generated code in: {output_dir}")
            return str(output_dir)
        except Exception as e:
            logger.error(f"Conversion failed: {str(e)}")
            raise

    def _validate_input(self, owl_path: Path):
        """Validate input OWL file"""
        if not owl_path.exists():
            raise FileNotFoundError(f"OWL file not found: {owl_path}")
        if owl_path.suffix != '.owl':
            raise ValueError("Input file must have .owl extension")

    def _parse_owl(self, g: Graph, owl_path: Path):
        """Parse OWL file into RDF graph"""
        try:
            g.parse(owl_path)
        except Exception as e:
            raise ValueError(f"Failed to parse OWL file: {str(e)}")

    def _create_output_dir(self, ontology_name: str, base_dir: str) -> Path:
        """Create version-specific output directory"""
        version_suffix = f"v{self.current_version.replace('.', '_')}"
        output_dir = Path(base_dir) / f"{ontology_name}_{version_suffix}"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _extract_namespaces(self, g: Graph):
        """Extract namespaces from ontology"""
        for prefix, uri in g.namespaces():
            self.ns[prefix] = uri

    def _build_class_hierarchy(self, g: Graph):
        """Build class hierarchy structure"""
        for cls in g.subjects(RDF.type, OWL.Class):
            self.class_hierarchy[str(cls)] = []

        for sub_class, _, super_class in g.triples((None, RDFS.subClassOf, None)):
            if str(sub_class) in self.class_hierarchy:
                self.class_hierarchy[str(sub_class)].append(str(super_class))

    def _extract_classes(self, g: Graph) -> List[Dict]:
        """Extract class definitions from ontology"""
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
        """Extract property definitions from ontology"""
        properties = []
        for prop in g.subjects(RDF.type, OWL.ObjectProperty):
            properties.append(self._process_property(g, prop, "ObjectProperty"))
        for prop in g.subjects(RDF.type, OWL.DatatypeProperty):
            properties.append(self._process_property(g, prop, "DatatypeProperty"))
        return properties

    def _process_property(self, g: Graph, prop: URIRef, prop_type: str) -> Dict:
        """Process individual property definition"""
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
from typing import List, Optional
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
        ))

    def _generate_hydra_config(self, output_dir: Path):
        """Generate Hydra configuration files"""
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
            (config_dir / f"{cls['name'].lower()}.yaml").write_text(yaml.dump(config, sort_keys=False))

    def _generate_compatibility_layer(self, output_dir: Path):
        """Generate version compatibility adapter"""
        template = Template('''# Auto-generated compatibility layer
from typing import Dict, Any
from dataclasses import asdict
import semver

class OntologyAdapter:
    """Handle version migrations between ontology versions"""
    CURRENT_VERSION = "{{ version }}"
    MIGRATION_RULES = {{ migration_rules }}

    @classmethod
    def migrate(cls, old_data: Dict[str, Any], old_version: str) -> Dict[str, Any]:
        if old_version == cls.CURRENT_VERSION:
            return old_data

        try:
            migrated = old_data.copy()
            # Apply field renames
            for old_field, new_field in cls.MIGRATION_RULES.get('field_renames', {}).items():
                if old_field in migrated.get('University', {}):
                    migrated['University'][new_field] = migrated['University'].pop(old_field)

            # Set defaults for new fields
            if 'University' in migrated:
                migrated['University'].setdefault('name', "")
                {% for prop in properties if prop.domain == 'University' and not prop.get('exists_in_old', True) %}
                migrated['University'].setdefault('{{ prop.name }}', {% if prop.range == 'bool' %}False{% elif prop.range == 'str' %}""{% elif prop.range == 'int' %}0{% else %}None{% endif %})
                {% endfor %}

            return migrated
        except Exception as e:
            raise ValueError(f"Migration failed: {str(e)}")

    @staticmethod
    def to_dict(obj) -> Dict[str, Any]:
        return asdict(obj)

    @staticmethod
    def from_dict(data: Dict[str, Any], target_class):
        return target_class(**data)
''')

        (output_dir / "compatibility.py").write_text(template.render(
            version=self.current_version,
            properties=self.properties_info,
            migration_rules={
                "field_renames": OntologyVersionManager.get_migration_rules(self.current_version).get("University", {})
            }
        ))

    def _create_init_file(self, output_dir: Path):
        """Create __init__.py for package imports"""
        (output_dir / "__init__.py").write_text(
            "from .ontology_model import *\n"
            "from .compatibility import OntologyAdapter\n"
            "__all__ = ['OntologyAdapter'] + "
            "[name for name in dir() if not name.startswith('_')]"
        )

    def _uri_to_name(self, uri: Union[URIRef, str]) -> str:
        """Convert URI to class/property name"""
        uri_str = str(uri)
        return uri_str.split('#')[-1] if '#' in uri_str else uri_str.split('/')[-1]

    def _get_class_comment(self, g: Graph, class_uri: URIRef) -> Optional[str]:
        """Get comment for a class"""
        comment = g.value(class_uri, RDFS.comment)
        return str(comment) if comment else None

    def _get_property_comment(self, g: Graph, prop: URIRef) -> Optional[str]:
        """Get comment for a property"""
        comment = g.value(prop, RDFS.comment)
        return str(comment) if comment else None

    def _get_property_domain(self, g: Graph, prop: URIRef) -> Optional[str]:
        """Get domain of a property"""
        domain = g.value(prop, RDFS.domain)
        return self._uri_to_name(domain) if domain else None

    def _get_property_range(self, g: Graph, prop: URIRef, prop_type: str) -> str:
        """Get range of a property"""
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
                            hydra_mode: bool = False, version: str = None) -> str:
    """Public interface for generating Python classes from OWL"""
    converter = OwlToPythonConverter()
    return converter.convert(owl_file, base_output_dir, hydra_mode, version)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert OWL ontology to Python classes")
    parser.add_argument("owl_file", help="Path to input OWL file")
    parser.add_argument("--output", default="generated", help="Output directory")
    parser.add_argument("--hydra", action="store_true", help="Enable Hydra support")
    parser.add_argument("--version", help="Override ontology version")
    args = parser.parse_args()

    try:
        output_path = generate_python_classes(
            args.owl_file,
            args.output,
            args.hydra,
            args.version
        )
        print(f"Successfully generated code in: {output_path}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)