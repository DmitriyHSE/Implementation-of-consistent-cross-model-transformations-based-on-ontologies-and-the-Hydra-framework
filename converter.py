from rdflib import Graph, URIRef, Namespace, RDF, OWL, RDFS, XSD, Literal
from pathlib import Path
import yaml
import json
import xml.etree.ElementTree as ET
from typing import Dict, Any

class OntologyConverter:
    def __init__(self):
        self.graph = Graph()
        self.base_ns = Namespace("http://example.org/ontology#")
        self._init_namespaces()

    def _init_namespaces(self):
        self.graph.bind("", self.base_ns)
        self.graph.bind("owl", OWL)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("xsd", XSD)
        self.graph.add((self.base_ns["Ontology"], RDF.type, OWL.Ontology))
        self.graph.add((self.base_ns["Ontology"], OWL.versionInfo, Literal("1.0.0")))

    def convert(self, input_file: str, output_owl: str, version: str = "1.0.0") -> None:
        path = Path(input_file)
        self.graph = Graph()
        self._init_namespaces()
        self.graph.set((self.base_ns["Ontology"], OWL.versionInfo, Literal(version)))

        if not path.exists():
            raise FileNotFoundError(f"File not found: {input_file}")

        if path.suffix == '.xml':
            self._from_xml(path)
        elif path.suffix in ('.yaml', '.yml'):
            self._from_yaml(path)
        elif path.suffix == '.json':
            self._from_json(path)
        else:
            raise ValueError(f"Unsupported format: {path.suffix}")

        self._serialize(output_owl)

    def _serialize(self, output_path: str):
        try:
            self.graph.serialize(
                destination=output_path,
                format='pretty-xml',
                encoding='utf-8'
            )
        except Exception as e:
            raise IOError(f"Error saving OWL: {str(e)}")

    def _from_xml(self, file_path: Path):
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            for cls in root.findall('.//class'):
                self._process_class(cls)

        except ET.ParseError as e:
            raise ValueError(f"XML parsing error: {str(e)}")

    def _from_yaml(self, file_path: Path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self._process_dict(data)
        except yaml.YAMLError as e:
            raise ValueError(f"YAML parsing error: {str(e)}")

    def _from_json(self, file_path: Path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._process_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"JSON parsing error: {str(e)}")

    def _process_dict(self, data: Dict[str, Any]):
        if not isinstance(data, dict):
            raise ValueError("Expected dictionary at document root")

        for class_name, class_data in data.get('classes', {}).items():
            class_uri = self.base_ns[class_name]
            self.graph.add((class_uri, RDF.type, OWL.Class))

            if 'parent' in class_data:
                parent_uri = self.base_ns[class_data['parent']]
                self.graph.add((class_uri, RDFS.subClassOf, parent_uri))

            if isinstance(class_data, dict):
                if 'comment' in class_data:
                    self._add_comment(class_uri, class_data['comment'])

                for prop_name, prop_data in class_data.get('properties', {}).items():
                    self._process_property(prop_name, prop_data, class_uri)

    def _process_class(self, cls_element):
        class_name = cls_element.get('name')
        if not class_name:
            raise ValueError("Class missing name attribute")

        class_uri = self.base_ns[class_name]
        self.graph.add((class_uri, RDF.type, OWL.Class))

        if 'parent' in cls_element.attrib:
            parent_uri = self.base_ns[cls_element.get('parent')]
            self.graph.add((class_uri, RDFS.subClassOf, parent_uri))

        if 'comment' in cls_element.attrib:
            self._add_comment(class_uri, cls_element.get('comment'))

        for prop in cls_element.findall('.//property'):
            self._process_xml_property(prop, class_uri)

    def _process_property(self, prop_name: str, prop_data: Any, domain_uri: URIRef):
        if isinstance(prop_data, dict):
            self._process_structured_property(prop_name, prop_data, domain_uri)
        elif isinstance(prop_data, str):
            self._add_object_property(prop_name, domain_uri, prop_data)

    def _process_structured_property(self, prop_name: str, prop_data: Dict, domain_uri: URIRef):
        prop_type = prop_data.get('type', 'object')

        if prop_type == 'object':
            self._add_object_property(
                prop_name,
                domain_uri,
                prop_data.get('range'),
                prop_data.get('comment')
            )
        else:
            self._add_datatype_property(
                prop_name,
                domain_uri,
                prop_data.get('range', 'string'),
                prop_data.get('comment')
            )

    def _process_xml_property(self, prop_element, domain_uri: URIRef):
        prop_name = prop_element.get('name')
        if not prop_name:
            raise ValueError("Property missing name attribute")

        prop_type = prop_element.get('type', 'object')
        range_val = prop_element.get('range')

        if prop_type == 'object':
            self._add_object_property(
                prop_name,
                domain_uri,
                range_val,
                prop_element.get('comment')
            )
        else:
            self._add_datatype_property(
                prop_name,
                domain_uri,
                prop_element.get('range', 'string'),
                prop_element.get('comment')
            )

    def _add_object_property(self, prop_name: str, domain_uri: URIRef,
                           range_val: str = None, comment: str = None):
        prop_uri = self.base_ns[prop_name]
        self.graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
        self.graph.add((prop_uri, RDFS.domain, domain_uri))

        if range_val:
            self.graph.add((prop_uri, RDFS.range, self.base_ns[range_val]))

        if comment:
            self._add_comment(prop_uri, comment)

    def _add_datatype_property(self, prop_name: str, domain_uri: URIRef,
                             range_type: str = 'string', comment: str = None):
        prop_uri = self.base_ns[prop_name]
        self.graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
        self.graph.add((prop_uri, RDFS.domain, domain_uri))
        self.graph.add((prop_uri, RDFS.range, self._get_xsd_type(range_type)))

        if comment:
            self._add_comment(prop_uri, comment)

    def _add_comment(self, subject: URIRef, comment: str):
        self.graph.add((subject, RDFS.comment, Literal(comment, lang='en')))

    def _get_xsd_type(self, type_name: str) -> URIRef:
        type_map = {
            'string': XSD.string,
            'int': XSD.integer,
            'integer': XSD.integer,
            'float': XSD.float,
            'double': XSD.double,
            'date': XSD.date,
            'datetime': XSD.dateTime,
            'boolean': XSD.boolean
        }
        return type_map.get(type_name.lower(), XSD.string)


if __name__ == "__main__":
    pass