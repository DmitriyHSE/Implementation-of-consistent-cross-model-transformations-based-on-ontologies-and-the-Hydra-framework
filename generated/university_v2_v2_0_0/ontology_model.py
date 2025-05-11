# Auto-generated from OWL ontology
from dataclasses import dataclass, field
from typing import List, Optional

from omegaconf import DictConfig



@dataclass
class University:
    """Educational institution v2"""
    
    
    departments: Optional['Department'] = field(
        default=None,
        metadata={"hydra": {"key": "departments"}} if True else {}
    )
    """departments (ObjectProperty)"""
    
    
    
    name: str = field(
        default="",
        metadata={"hydra": {"key": "name"}} if True else {}
    )
    """name (DatatypeProperty)"""
    
    
    
    founding_year: int = field(
        default=0,
        metadata={"hydra": {"key": "founding_year"}} if True else {}
    )
    """Renamed from established (DatatypeProperty)"""
    
    

    @classmethod
    def from_config(cls, cfg: DictConfig):
        return cls(
            
            departments=cfg.departments,
            
            name=cfg.name,
            
            founding_year=cfg.founding_year
            
        )

@dataclass
class Department:
    """Department"""
    

    @classmethod
    def from_config(cls, cfg: DictConfig):
        return cls(
            
        )
