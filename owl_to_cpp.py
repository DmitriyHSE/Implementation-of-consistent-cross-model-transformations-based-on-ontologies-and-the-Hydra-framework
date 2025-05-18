from rdflib import Graph, RDF, RDFS, OWL, XSD, URIRef
from jinja2 import Template
from pathlib import Path
import logging
from typing import Dict, List, Optional, Union
from owl_to_python import OntologyVersionManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class OwlToCppConverter:
    def __init__(self):
        self.ns = {}
        self.class_hierarchy = {}
        self.current_version = "1.0.0"
        self.properties_info = []
        self.classes_info = []
        self.previous_version = None
        self.migration_rules = {}
        self.output_dir: Optional[Path] = None

    def convert(self, owl_file: str, base_output_dir: str = "generated",
                version: Optional[str] = None, previous_version: Optional[str] = None,
                folder_prefix: Optional[str] = None) -> str:
        owl_path = Path(owl_file)
        self._validate_input(owl_path)

        g = Graph()
        g.parse(owl_path)

        self.current_version = version or OntologyVersionManager.load_version(g)

        if previous_version:
            self._load_previous_version(previous_version, g)

        self.output_dir = self._create_output_dir(owl_path.stem, base_output_dir, folder_prefix)

        self._extract_namespaces(g)
        self._build_class_hierarchy(g)
        self.classes_info = self._extract_classes(g)
        self.properties_info = self._extract_properties(g)

        self._generate_cpp_classes(self.output_dir)

        logger.info(f"C++ code generated in: {self.output_dir}")
        return str(self.output_dir.parent)

    def _validate_input(self, owl_path: Path):
        if not owl_path.exists():
            raise FileNotFoundError(f"OWL file not found: {owl_path}")
        if owl_path.suffix != ".owl":
            raise ValueError("Input file must have .owl extension")

    def _create_output_dir(self, ontology_name: str, base_dir: str, folder_prefix: Optional[str]) -> Path:
        version_suffix = f"v{self.current_version.replace('.', '_')}"
        dir_name = f"{folder_prefix or ontology_name}_{version_suffix}"
        output_dir = Path(base_dir) / dir_name / "src"
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def _load_previous_version(self, previous_version: str, current_g: Graph):
        prev_path = Path(previous_version)
        if not prev_path.exists():
            logger.warning(f"Previous version not found: {previous_version}")
            return
        prev_g = Graph()
        prev_g.parse(prev_path)
        self.previous_version = OntologyVersionManager.load_version(prev_g)
        self.migration_rules = OntologyVersionManager.generate_migration_rules(prev_g, current_g)

    def _extract_namespaces(self, g: Graph):
        self.ns = {prefix: uri for prefix, uri in g.namespaces()}

    def _build_class_hierarchy(self, g: Graph):
        for cls in g.subjects(RDF.type, OWL.Class):
            self.class_hierarchy[str(cls)] = []

        for subclass, _, superclass in g.triples((None, RDFS.subClassOf, None)):
            if str(subclass) in self.class_hierarchy:
                self.class_hierarchy[str(subclass)].append(str(superclass))

    def _extract_classes(self, g: Graph) -> List[Dict]:
        classes = []
        for class_uri in g.subjects(RDF.type, OWL.Class):
            classes.append({
                "name": self._uri_to_name(class_uri),
                "uri": str(class_uri),
                "parent_classes": [self._uri_to_name(uri) for uri in self.class_hierarchy.get(str(class_uri), [])],
                "comment": self._get_comment(g, class_uri)
            })
        return classes

    def _extract_properties(self, g: Graph) -> List[Dict]:
        props = []
        for prop in g.subjects(RDF.type, OWL.ObjectProperty):
            props.append(self._process_property(g, prop, "ObjectProperty"))
        for prop in g.subjects(RDF.type, OWL.DatatypeProperty):
            props.append(self._process_property(g, prop, "DatatypeProperty"))
        return props

    def _process_property(self, g: Graph, prop: URIRef, prop_type: str) -> Dict:
        name = self._uri_to_name(prop)
        domain = self._get_domain(g, prop)
        range_ = self._get_range(g, prop, prop_type)
        return {
            "name": name,
            "type": prop_type,
            "domain": domain,
            "range": range_,
            "comment": self._get_comment(g, prop)
        }

    def _get_domain(self, g: Graph, prop: URIRef) -> Optional[str]:
        domain = g.value(prop, RDFS.domain)
        return self._uri_to_name(domain) if domain else None

    def _get_range(self, g: Graph, prop: URIRef, prop_type: str) -> str:
        range_ = g.value(prop, RDFS.range)
        if prop_type == "DatatypeProperty":
            if str(range_) == str(XSD.string):
                return "std::string"
            elif str(range_) == str(XSD.integer):
                return "int"
            elif str(range_) == str(XSD.float):
                return "float"
            elif str(range_) == str(XSD.boolean):
                return "bool"
            return "std::string"
        else:
            return self._uri_to_name(range_) if range_ else "void*"

    def _uri_to_name(self, uri: Union[URIRef, str]) -> str:
        uri = str(uri)
        return uri.split("#")[-1] if "#" in uri else uri.split("/")[-1]

    def _get_comment(self, g: Graph, uri: URIRef) -> Optional[str]:
        comment = g.value(uri, RDFS.comment)
        return str(comment) if comment else None

    from jinja2 import Template

    def _generate_cpp_classes(self, output_dir: Path):
        template = Template('''#include <string>
    #include <iostream>

    {% if cls.comment %}// {{ cls.comment }}{% endif %}
    class {{ cls.name }}{% if cls.parent_classes %} : public {{ cls.parent_classes[0] }}{% endif %} {
    public:
        {{ cls.name }}() {
            {% for prop in class_properties %}
            this->{{ prop.name }} = {% if prop.range == 'std::string' %}""{% elif prop.range in ['int', 'float'] %}0{% elif prop.range == 'bool' %}false{% else %}nullptr{% endif %};
            {% endfor %}
        }

        {% for prop in class_properties %}
        {% if prop.comment %}// {{ prop.comment }}{% endif %}
        {{ prop.range }} get{{ prop.name|capitalize }}() const { return {{ prop.name }}; }
        void set{{ prop.name|capitalize }}({{ prop.range }} value) { {{ prop.name }} = value; }
        {% endfor %}

        friend std::ostream& operator<<(std::ostream& os, const {{ cls.name }}& obj) {
            os << "{{ cls.name }} { ";
            {% for prop in class_properties %}
            os << "{{ prop.name }}: " << obj.{{ prop.name }}{% if not loop.last %} << ", "{% endif %};
            {% endfor %}
            os << " }";
            return os;
        }

    private:
        {% for prop in class_properties %}
        {{ prop.range }} {{ prop.name }};
        {% endfor %}
    };
    ''')

        for cls in self.classes_info:
            class_props = [p for p in self.properties_info if p.get("domain") == cls["name"]]
            class_path = output_dir / f"{cls['name']}.cpp"
            class_path.write_text(
                template.render(
                    cls=cls,
                    class_properties=class_props
                ),
                encoding='utf-8'
            )


def _generate_changelog(self, output_dir: Path):
        if not self.migration_rules:
            return

        changelog = [
            "# C++ Ontology Migration",
            f"## From version {self.previous_version} to {self.current_version}",
        ]
        if self.migration_rules.get("field_renames"):
            changelog.append("### Field Renames")
            for old, new in self.migration_rules["field_renames"].items():
                changelog.append(f"- `{old}` → `{new}`")
        if self.migration_rules.get("added_fields"):
            changelog.append("\n### Added Fields")
            for name, info in self.migration_rules["added_fields"].items():
                changelog.append(f"- `{name}` ({info['type']}) default: `{info['default']}`")
        if self.migration_rules.get("removed_fields"):
            changelog.append("\n### Removed Fields")
            for name in self.migration_rules["removed_fields"]:
                changelog.append(f"- `{name}`")
        if self.migration_rules.get("type_changes"):
            changelog.append("\n### Type Changes")
            for field, change in self.migration_rules["type_changes"].items():
                changelog.append(f"- `{field}`: {change['old']} → {change['new']}")

        (output_dir / "CHANGES.md").write_text("\n".join(changelog), encoding="utf-8")


def generate_cpp_from_owl(owl_file: str,
                          base_output_dir: str = "generated",
                          version: Optional[str] = None,
                          previous_version: Optional[str] = None,
                          folder_prefix: Optional[str] = None) -> str:
    converter = OwlToCppConverter()
    return converter.convert(owl_file, base_output_dir, version, previous_version, folder_prefix)
