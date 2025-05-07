from rdflib import Graph, RDF, RDFS, OWL, XSD, URIRef  # Добавлен URIRef
from jinja2 import Template
from pathlib import Path
import logging
from typing import Dict, List, Optional, Union  # Добавлен Union


class OwlToPythonConverter:
    def __init__(self):
        self.ns = {}
        self.class_hierarchy = {}

    def convert(self, owl_file: str, output_dir: str = "generated") -> None:
        owl_path = Path(owl_file).absolute()
        self._validate_input(owl_path)

        g = Graph()
        self._parse_owl(g, owl_path)
        self._extract_namespaces(g)
        self._build_class_hierarchy(g)

        classes_info = self._extract_classes(g)
        properties_info = self._extract_properties(g)

        self._generate_code(
            owl_path=owl_path,
            classes=classes_info,
            properties=properties_info,
            output_dir=output_dir
        )

    def _validate_input(self, owl_path: Path):
        if not owl_path.exists():
            raise FileNotFoundError(f"OWL файл не найден: {owl_path}")
        if not owl_path.suffix == '.owl':
            raise ValueError("Требуется файл с расширением .owl")

    def _parse_owl(self, g: Graph, owl_path: Path):
        try:
            g.parse(owl_path)
            logging.info(f"Загружена онтология: {owl_path}")
        except Exception as e:
            raise ValueError(f"Ошибка парсинга OWL: {str(e)}")

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

    def _generate_code(self, owl_path: Path, classes: List[Dict],
                       properties: List[Dict], output_dir: str):
        template = Template('''\
# Автосгенерированный код из OWL-онтологии
# Источник: {{ owl_file }}
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import date, datetime

{% for cls in classes %}
@dataclass
class {{ cls.name }}{% if cls.parent_classes %}({{ cls.parent_classes|join(', ') }}){% endif %}:
    """{{ cls.comment or cls.name }}"""
    {% for prop in properties if prop.domain == cls.name %}
    {% if prop.type == 'ObjectProperty' %}
    {{ prop.name }}: {% if prop.range == cls.name %}List['{{ prop.range }}']{% else %}Optional['{{ prop.range }}']{% endif %} = None
    """{{ prop.comment or prop.name }} ({{ prop.type }})"""
    {% else %}
    {{ prop.name }}: {{ prop.range }} = None
    """{{ prop.comment or prop.name }} ({{ prop.type }})"""
    {% endif %}
    {% endfor %}

{% endfor %}

class OntologyModel:
    """Фасад для работы с онтологией"""

    def __init__(self):
        {% for prop in properties %}
        self.{{ prop.name }}_relations: Dict[str, List[str]] = {}
        {% endfor %}
''')

        output_path = Path(output_dir) / "ontology_model.py"
        output_path.parent.mkdir(exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template.render(
                owl_file=str(owl_path),
                classes=classes,
                properties=properties
            ))
        logging.info(f"Сгенерирован Python-код: {output_path}")

    def _uri_to_name(self, uri: Union[URIRef, str]) -> str:
        return str(uri).split('#')[-1].split('/')[-1]

    def _get_class_comment(self, g: Graph, class_uri: URIRef) -> Optional[str]:
        return str(g.value(class_uri, RDFS.comment)) if g.value(class_uri, RDFS.comment) else None

    def _get_property_comment(self, g: Graph, prop: URIRef) -> Optional[str]:
        return str(g.value(prop, RDFS.comment)) if g.value(prop, RDFS.comment) else None

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
            elif str(range_) == str(XSD.date):
                return "date"
            return "str"  # fallback
        else:
            range_ = g.value(prop, RDFS.range)
            return self._uri_to_name(range_) if range_ else "str"


def generate_python_classes(owl_file: str, output_dir: str = "generated") -> None:
    converter = OwlToPythonConverter()
    converter.convert(owl_file, output_dir)


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        generate_python_classes(sys.argv[1])
    else:
        print("Укажите путь к OWL-файлу")
