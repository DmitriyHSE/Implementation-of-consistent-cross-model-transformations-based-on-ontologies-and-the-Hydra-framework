from rdflib import Graph, RDF, RDFS, OWL, XSD, URIRef
from jinja2 import Template
from pathlib import Path
from typing import Dict, List, Optional, Union

class OwlToCppConverter:
    def __init__(self):
        self.ns = {}
        self.class_hierarchy = {}

    def convert(self, owl_file: str, output_dir: str = "generated_cpp") -> None:
        owl_path = Path(owl_file).absolute()
        if not owl_path.exists():
            raise FileNotFoundError(f"OWL файл не найден: {owl_path}")

        g = Graph()
        g.parse(owl_path)
        self._extract_namespaces(g)
        self._build_class_hierarchy(g)

        classes_info = self._extract_classes(g)
        properties_info = self._extract_properties(g)

        template = Template('// Автосгенерированный C++ код из OWL\n#pragma once\n#include <string>\n#include <vector>\n\n{% for cls in classes %}\nclass {{ cls.name }} {\npublic:\n    {{ cls.name }}() = default;\n    ~{{ cls.name }}() = default;\n\n    {% for prop in properties if prop.domain == cls.name %}\n    {% if prop.type == "ObjectProperty" %}\n    std::vector<{{ prop.range }}> {{ prop.name }};  // {{ prop.comment or prop.name }}\n    {% else %}\n    {{ "int" if prop.range == "int" else "std::string" }} {{ prop.name }};  // {{ prop.comment or prop.name }}\n    {% endif %}\n    {% endfor %}\n};\n{% endfor %}\n')
        output_path = Path(output_dir) / "ontology_model.hpp"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(template.render(classes=classes_info, properties=properties_info))

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
        return {
            "name": self._uri_to_name(prop),
            "type": prop_type,
            "domain": self._get_property_domain(g, prop),
            "range": self._get_property_range(g, prop, prop_type),
            "comment": self._get_property_comment(g, prop)
        }

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
        range_ = g.value(prop, RDFS.range)
        if prop_type == "DatatypeProperty":
            if str(range_) == str(XSD.integer):
                return "int"
            return "std::string"
        return self._uri_to_name(range_) if range_ else "std::string"

def generate_cpp_classes(owl_file: str, output_dir: str = "generated_cpp") -> None:
    OwlToCppConverter().convert(owl_file, output_dir)
