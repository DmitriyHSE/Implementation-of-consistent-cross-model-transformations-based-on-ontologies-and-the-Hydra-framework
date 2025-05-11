# Auto-generated from OWL ontology
from dataclasses import dataclass, field
from typing import List, Optional

from omegaconf import DictConfig



@dataclass
class University:
    """Educational institution"""
    
    
    name: str = field(
        default="",
        metadata={"hydra": {"key": "name"}} if True else {}
    )
    """name (DatatypeProperty)"""
    
    
    
    established: int = field(
        default=0,
        metadata={"hydra": {"key": "established"}} if True else {}
    )
    """established (DatatypeProperty)"""
    
    

    @classmethod
    def from_config(cls, cfg: DictConfig):
        return cls(
            
            name=cfg.name,
            
            established=cfg.established
            
        )
