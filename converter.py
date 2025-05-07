from rdflib import Graph, URIRef, Namespace, RDF, OWL, RDFS, XSD
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
        """Инициализация стандартных неймспейсов"""
        self.graph.bind("", self.base_ns)
        self.graph.bind("owl", OWL)
        self.graph.bind("rdfs", RDFS)
        self.graph.bind("xsd", XSD)

    def convert(self, input_file: str, output_owl: str) -> None:
        """Основной метод конвертации"""
        path = Path(input_file)
        self.graph = Graph()  # Очищаем граф перед новой конвертацией
        self._init_namespaces()

        if not path.exists():
            raise FileNotFoundError(f"Файл не найден: {input_file}")

        if path.suffix == '.xml':
            self._from_xml(path)
        elif path.suffix in ('.yaml', '.yml'):
            self._from_yaml(path)
        elif path.suffix == '.json':
            self._from_json(path)
        else:
            raise ValueError(f"Неподдерживаемый формат: {path.suffix}")

        self._serialize(output_owl)

    def _serialize(self, output_path: str):
        """Сериализация в файл с обработкой ошибок"""
        try:
            self.graph.serialize(
                destination=output_path,
                format='pretty-xml',
                encoding='utf-8'
            )
        except Exception as e:
            raise IOError(f"Ошибка сохранения OWL: {str(e)}")

    def _from_xml(self, file_path: Path):
        """Конвертация XML в OWL"""
        try:
            tree = ET.parse(file_path)
            root = tree.getroot()

            for cls in root.findall('.//class'):
                self._process_class(cls)

        except ET.ParseError as e:
            raise ValueError(f"Ошибка парсинга XML: {str(e)}")

    def _from_yaml(self, file_path: Path):
        """Конвертация YAML в OWL"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)
                self._process_dict(data)
        except yaml.YAMLError as e:
            raise ValueError(f"Ошибка парсинга YAML: {str(e)}")

    def _from_json(self, file_path: Path):
        """Конвертация JSON в OWL"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self._process_dict(data)
        except json.JSONDecodeError as e:
            raise ValueError(f"Ошибка парсинга JSON: {str(e)}")

    def _process_dict(self, data: Dict[str, Any]):
        """Обработка словарной структуры (YAML/JSON)"""
        if not isinstance(data, dict):
            raise ValueError("Ожидается словарь в корне документа")

        for class_name, class_data in data.get('classes', {}).items():
            class_uri = self.base_ns[class_name]
            self.graph.add((class_uri, RDF.type, OWL.Class))

            if isinstance(class_data, dict):
                if 'comment' in class_data:
                    self._add_comment(class_uri, class_data['comment'])

                for prop_name, prop_data in class_data.get('properties', {}).items():
                    self._process_property(prop_name, prop_data, class_uri)

    def _process_class(self, cls_element):
        """Обработка класса из XML"""
        class_name = cls_element.get('name')
        if not class_name:
            raise ValueError("Класс без атрибута name")

        class_uri = self.base_ns[class_name]
        self.graph.add((class_uri, RDF.type, OWL.Class))

        if 'comment' in cls_element.attrib:
            self._add_comment(class_uri, cls_element.get('comment'))

        for prop in cls_element.findall('.//property'):
            self._process_xml_property(prop, class_uri)

    def _process_property(self, prop_name: str, prop_data: Any, domain_uri: URIRef):
        """Обработка свойства из словаря"""
        if isinstance(prop_data, dict):
            self._process_structured_property(prop_name, prop_data, domain_uri)
        elif isinstance(prop_data, str):
            self._add_object_property(prop_name, domain_uri, prop_data)

    def _process_structured_property(self, prop_name: str, prop_data: Dict, domain_uri: URIRef):
        """Обработка свойства с дополнительными атрибутами"""
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
        """Обработка свойства из XML"""
        prop_name = prop_element.get('name')
        if not prop_name:
            raise ValueError("Свойство без атрибута name")

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

    def _add_object_property(self, prop_name: str, domain_uri: URIRef, range_val: str = None, comment: str = None):
        """Добавление объектного свойства"""
        prop_uri = self.base_ns[prop_name]
        self.graph.add((prop_uri, RDF.type, OWL.ObjectProperty))
        self.graph.add((prop_uri, RDFS.domain, domain_uri))

        if range_val:
            self.graph.add((prop_uri, RDFS.range, self.base_ns[range_val]))

        if comment:
            self._add_comment(prop_uri, comment)

    def _add_datatype_property(self, prop_name: str, domain_uri: URIRef, range_type: str = 'string',
                               comment: str = None):
        """Добавление свойства данных"""
        prop_uri = self.base_ns[prop_name]
        self.graph.add((prop_uri, RDF.type, OWL.DatatypeProperty))
        self.graph.add((prop_uri, RDFS.domain, domain_uri))
        self.graph.add((prop_uri, RDFS.range, self._get_xsd_type(range_type)))

        if comment:
            self._add_comment(prop_uri, comment)

    def _add_comment(self, subject: URIRef, comment: str):
        """Добавление комментария"""
        from rdflib import Literal
        self.graph.add((subject, RDFS.comment, Literal(comment, lang='ru')))

    def _get_xsd_type(self, type_name: str) -> URIRef:
        """Получение XSD типа для свойства данных"""
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