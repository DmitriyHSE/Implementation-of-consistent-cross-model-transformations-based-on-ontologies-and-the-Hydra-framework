# Auto-generated from OWL ontology
from dataclasses import dataclass, field
from typing import List, Optional, Union

from omegaconf import DictConfig



@dataclass
class University:
    """Высшее учебное заведение"""
    
    
    name: str = field(
        default="",
        metadata={"hydra": {"key": "name"}} if True else {}
    )
    """Название университета (DatatypeProperty)"""
    
    
    
    established: str = field(
        default="",
        metadata={"hydra": {"key": "established"}} if True else {}
    )
    """Год основания (DatatypeProperty)"""
    
    

    @classmethod
    def from_config(cls, cfg: DictConfig):
        return cls(
            
            name=cfg.name,
            
            established=cfg.established
            
        )
