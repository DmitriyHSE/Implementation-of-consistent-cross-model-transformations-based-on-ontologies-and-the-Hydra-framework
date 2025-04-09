from rdflib import Graph, RDF, OWL, RDFS


def compare_owl(old_owl: str, new_owl: str) -> dict:
    """Сравнивает две версии OWL-файлов и возвращает изменения"""
    old_g = Graph().parse(old_owl)
    new_g = Graph().parse(new_owl)

    changes = {
        'added_classes': set(),
        'removed_classes': set(),
        'added_properties': set(),
        'removed_properties': set(),
        'modified_properties': set()
    }

    # Сравнение классов
    old_classes = set(old_g.subjects(RDF.type, OWL.Class))
    new_classes = set(new_g.subjects(RDF.type, OWL.Class))
    changes['added_classes'] = new_classes - old_classes
    changes['removed_classes'] = old_classes - new_classes

    # Сравнение свойств
    old_props = set(old_g.subjects(RDF.type, OWL.ObjectProperty))
    new_props = set(new_g.subjects(RDF.type, OWL.ObjectProperty))

    changes['added_properties'] = new_props - old_props
    changes['removed_properties'] = old_props - new_props

    # Проверка изменений в существующих свойствах
    common_props = new_props & old_props
    for prop in common_props:
        old_domain = set(old_g.objects(prop, RDFS.domain))
        new_domain = set(new_g.objects(prop, RDFS.domain))
        old_range = set(old_g.objects(prop, RDFS.range))
        new_range = set(new_g.objects(prop, RDFS.range))

        if old_domain != new_domain or old_range != new_range:
            changes['modified_properties'].add(prop)

    return changes