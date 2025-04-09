
# Автосгенерированный код из OWL
from dataclasses import dataclass


@dataclass
class Course:
    pass

@dataclass
class Student:
    pass


# Связи между классами
class UniversityModel:
    def __init__(self):
        
        self.enrolledIn = {}  # Student -> Course
        
    