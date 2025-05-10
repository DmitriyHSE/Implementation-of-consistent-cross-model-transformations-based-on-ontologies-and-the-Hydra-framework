# Автосгенерированный код из OWL-онтологии
# Источник: C:\Users\my18f\OneDrive\Рабочий стол\HSE\программирование\2 курс курсач\Implementation-of-consistent-cross-model-transformations-based-on-ontologies-and-the-Hydra-framework-main\university.owl
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import date, datetime


@dataclass
class Student:
    """Студент университета"""
    
    
    enrolledIn: Optional['Course'] = None
    """enrolledIn (ObjectProperty)"""
    
    
    
    studentId: str = None
    """studentId (DatatypeProperty)"""
    
    


@dataclass
class Course:
    """Учебный курс"""
    
    
    creditHours: int = None
    """creditHours (DatatypeProperty)"""
    
    



class OntologyModel:
    """Фасад для работы с онтологией"""

    def __init__(self):
        
        self.enrolledIn_relations: Dict[str, List[str]] = {}
        
        self.creditHours_relations: Dict[str, List[str]] = {}
        
        self.studentId_relations: Dict[str, List[str]] = {}
        