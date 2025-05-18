from rdflib import Graph, RDF, RDFS, OWL, XSD, URIRef, Literal
from jinja2 import Template
from pathlib import Path
import logging
import yaml
from typing import Dict, List, Optional, Union, Any, Set
import semver
import sys
import json
from owl_to_python import OntologyDiff, OntologyVersionManager

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


class OwlToJavaConverter:
    def __init__(self):
        self.ns = {}
        self.class_hierarchy = {}
        self.current_version = "1.0.0"
        self.properties_info = []
        self.classes_info = []
        self.previous_version = None
        self.migration_rules = {}
        self.package_name = "generated"

    def _create_output_dir(self, ontology_name: str, base_dir: str, folder_prefix: Optional[str] = None) -> Path:
        version_suffix = f"v{self.current_version.replace('.', '_')}"
        dir_name = f"{folder_prefix or ontology_name}_{version_suffix}"
        output_dir = Path(base_dir) / dir_name / "src/main/java" / self.package_name.replace(".", "/")
        output_dir.mkdir(parents=True, exist_ok=True)
        return output_dir

    def convert(self, owl_file: str, base_output_dir: str = "generated",
                package_name: str = "generated", version: str = None,
                previous_version: str = None, folder_prefix: str = None) -> str:
        try:
            owl_path = Path(owl_file)
            self._validate_input(owl_path)
            self.package_name = package_name

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

            self._generate_java_classes(output_dir)
            self._generate_pom_file(output_dir.parent.parent.parent)
            self._generate_changelog(output_dir.parent.parent.parent)

            logger.info(f"Successfully generated Java code in: {output_dir}")
            return str(output_dir.parent.parent.parent)
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

    def _generate_java_classes(self, output_dir: Path):
        for cls in self.classes_info:
            template = Template('''package {{ package_name }};

{% if cls.comment %}/** {{ cls.comment }} */{% endif %}
public class {{ cls.name }}{% if cls.parent_classes %} extends {{ cls.parent_classes[0] }}{% endif %} {
    {% for prop in properties if prop.domain == cls.name %}
    {% if prop.comment %}/** {{ prop.comment }} */{% endif %}
    private {{ prop.range }} {{ prop.name }};
    {% endfor %}

    public {{ cls.name }}() {
        {% for prop in properties if prop.domain == cls.name %}
        this.{{ prop.name }} = {% if prop.range == 'String' %}""{% elif prop.range == 'int' %}0{% elif prop.range == 'double' %}0.0{% elif prop.range == 'boolean' %}false{% else %}null{% endif %};
        {% endfor %}
    }

    {% for prop in properties if prop.domain == cls.name %}
    public {{ prop.range }} get{{ prop.name|capitalize }}() {
        return this.{{ prop.name }};
    }

    public void set{{ prop.name|capitalize }}({{ prop.range }} {{ prop.name }}) {
        this.{{ prop.name }} = {{ prop.name }};
    }
    {% endfor %}

    @Override
    public String toString() {
        return "{{ cls.name }}{" +
            {% for prop in properties if prop.domain == cls.name %}
            "{{ prop.name }}=" + {{ prop.name }} + {% if not loop.last %}", " + {% else %}""{% endif %}{% endfor %} +
            '}';
    }
}
''')
            class_file = output_dir / f"{cls['name']}.java"
            class_file.write_text(template.render(
                cls=cls,
                properties=self.properties_info,
                package_name=self.package_name
            ), encoding='utf-8')

    def _generate_pom_file(self, output_dir: Path):
        template = Template('''<project xmlns="http://maven.apache.org/POM/4.0.0"
         xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
         xsi:schemaLocation="http://maven.apache.org/POM/4.0.0 http://maven.apache.org/xsd/maven-4.0.0.xsd">
    <modelVersion>4.0.0</modelVersion>

    <groupId>{{ package_name }}</groupId>
    <artifactId>{{ artifact_id }}</artifactId>
    <version>{{ version }}</version>

    <properties>
        <maven.compiler.source>11</maven.compiler.source>
        <maven.compiler.target>11</maven.compiler.target>
    </properties>
</project>
''')
        artifact_id = output_dir.name.split('_')[0]
        pom_file = output_dir / "pom.xml"
        pom_file.write_text(template.render(
            package_name=self.package_name,
            artifact_id=artifact_id,
            version=self.current_version
        ), encoding='utf-8')

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
                return "String"
            elif str(range_) == str(XSD.integer):
                return "int"
            elif str(range_) == str(XSD.float):
                return "double"
            elif str(range_) == str(XSD.date):
                return "java.time.LocalDate"
            elif str(range_) == str(XSD.dateTime):
                return "java.time.LocalDateTime"
            elif str(range_) == str(XSD.boolean):
                return "boolean"
            return "String"
        else:
            range_ = g.value(prop, RDFS.range)
            return self._uri_to_name(range_) if range_ else "Object"


def generate_java_classes(owl_file: str, base_output_dir: str = "generated",
                          package_name: str = "generated", version: str = None,
                          previous_version: str = None, folder_prefix: str = None) -> str:
    converter = OwlToJavaConverter()
    return converter.convert(
        owl_file=owl_file,
        base_output_dir=base_output_dir,
        package_name=package_name,
        version=version,
        previous_version=previous_version,
        folder_prefix=folder_prefix
    )


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Convert OWL ontology to Java classes")
    parser.add_argument("owl_file", help="Path to input OWL file")
    parser.add_argument("--output", default="generated", help="Output directory")
    parser.add_argument("--package", default="generated", help="Java package name")
    parser.add_argument("--version", help="Override ontology version")
    parser.add_argument("--previous", help="Path to previous version OWL file for migration")
    parser.add_argument("--prefix", help="Custom folder name prefix")
    args = parser.parse_args()

    try:
        output_path = generate_java_classes(
            args.owl_file,
            args.output,
            args.package,
            args.version,
            args.previous,
            args.prefix
        )
        print(f"Successfully generated Java code in: {output_path}")
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.exit(1)