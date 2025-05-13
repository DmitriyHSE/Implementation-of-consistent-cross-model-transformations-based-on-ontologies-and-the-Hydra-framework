from .ontology_model import *
from .compatibility import OntologyAdapter
__all__ = ['OntologyAdapter'] + [name for name in dir() if not name.startswith('_')]