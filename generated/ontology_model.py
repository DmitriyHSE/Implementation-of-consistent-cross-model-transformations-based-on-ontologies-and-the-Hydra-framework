
# Автосгенерированный код из OWL
# Источник: C:\Users\tsiru\PycharmProjects\Coursework\university_ontology_v1.owl
from dataclasses import dataclass
from typing import Dict


@dataclass
class Course:
    """Класс Course из онтологии"""
    pass

@dataclass
class Student:
    """Класс Student из онтологии"""
    pass


class OntologyModel:
    """Модель онтологии со связями"""

    def __init__(self):
        
        self.enrolledIn: Dict[Student, Course] = {}
        """enrolledIn: Student -> Course"""
        