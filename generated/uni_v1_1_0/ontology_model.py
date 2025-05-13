# Auto-generated from OWL ontology
from dataclasses import dataclass, field
from typing import List, Optional, Union

from omegaconf import DictConfig



@dataclass
class Department:
    """Факультет"""
    

    @classmethod
    def from_config(cls, cfg: DictConfig):
        return cls(
            
        )

@dataclass
class University:
    """Высшее учебное заведение"""
    
    
    departments: Optional['Department'] = field(
        default=None,
        metadata={"hydra": {"key": "departments"}} if True else {}
    )
    """Факультеты университета (ObjectProperty)"""
    
    
    
    name: str = field(
        default="",
        metadata={"hydra": {"key": "name"}} if True else {}
    )
    """Название университета (DatatypeProperty)"""
    
    
    
    founding_year: str = field(
        default="",
        metadata={"hydra": {"key": "founding_year"}} if True else {}
    )
    """Год основания (DatatypeProperty)"""
    
    

    @classmethod
    def from_config(cls, cfg: DictConfig):
        return cls(
            
            departments=cfg.departments,
            
            name=cfg.name,
            
            founding_year=cfg.founding_year
            
        )
