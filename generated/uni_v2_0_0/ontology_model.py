# Auto-generated from OWL ontology
from dataclasses import dataclass, field
from typing import List, Optional, Union

from omegaconf import DictConfig



@dataclass
class Classroom:
    """Аудитория"""
    
    
    hasProjector: bool = field(
        default=False,
        metadata={"hydra": {"key": "hasProjector"}} if True else {}
    )
    """hasProjector (DatatypeProperty)"""
    
    
    
    capacity: int = field(
        default=0,
        metadata={"hydra": {"key": "capacity"}} if True else {}
    )
    """capacity (DatatypeProperty)"""
    
    
    
    number: str = field(
        default="",
        metadata={"hydra": {"key": "number"}} if True else {}
    )
    """number (DatatypeProperty)"""
    
    

    @classmethod
    def from_config(cls, cfg: DictConfig):
        return cls(
            
            hasProjector=cfg.hasProjector,
            
            capacity=cfg.capacity,
            
            number=cfg.number
            
        )

@dataclass
class Professor(Person):
    """Преподаватель"""
    
    
    teaches: Optional['Course'] = field(
        default=None,
        metadata={"hydra": {"key": "teaches"}} if True else {}
    )
    """teaches (ObjectProperty)"""
    
    
    
    department: str = field(
        default="",
        metadata={"hydra": {"key": "department"}} if True else {}
    )
    """department (DatatypeProperty)"""
    
    

    @classmethod
    def from_config(cls, cfg: DictConfig):
        return cls(
            
            teaches=cfg.teaches,
            
            department=cfg.department
            
        )

@dataclass
class Course:
    """Учебный курс"""
    
    
    schedule: Optional['Schedule'] = field(
        default=None,
        metadata={"hydra": {"key": "schedule"}} if True else {}
    )
    """schedule (ObjectProperty)"""
    
    
    
    code: str = field(
        default="",
        metadata={"hydra": {"key": "code"}} if True else {}
    )
    """code (DatatypeProperty)"""
    
    
    
    title: str = field(
        default="",
        metadata={"hydra": {"key": "title"}} if True else {}
    )
    """title (DatatypeProperty)"""
    
    
    
    credits: int = field(
        default=0,
        metadata={"hydra": {"key": "credits"}} if True else {}
    )
    """credits (DatatypeProperty)"""
    
    

    @classmethod
    def from_config(cls, cfg: DictConfig):
        return cls(
            
            schedule=cfg.schedule,
            
            code=cfg.code,
            
            title=cfg.title,
            
            credits=cfg.credits
            
        )

@dataclass
class Person:
    """Базовый класс для всех людей"""
    
    
    birthDate: date = field(
        default=None,
        metadata={"hydra": {"key": "birthDate"}} if True else {}
    )
    """birthDate (DatatypeProperty)"""
    
    
    
    name: str = field(
        default="",
        metadata={"hydra": {"key": "name"}} if True else {}
    )
    """Полное имя (DatatypeProperty)"""
    
    

    @classmethod
    def from_config(cls, cfg: DictConfig):
        return cls(
            
            birthDate=cfg.birthDate,
            
            name=cfg.name
            
        )

@dataclass
class Schedule:
    """Расписание занятий"""
    
    
    room: Optional['Classroom'] = field(
        default=None,
        metadata={"hydra": {"key": "room"}} if True else {}
    )
    """room (ObjectProperty)"""
    
    
    
    weekday: str = field(
        default="",
        metadata={"hydra": {"key": "weekday"}} if True else {}
    )
    """weekday (DatatypeProperty)"""
    
    
    
    startTime: str = field(
        default="",
        metadata={"hydra": {"key": "startTime"}} if True else {}
    )
    """startTime (DatatypeProperty)"""
    
    

    @classmethod
    def from_config(cls, cfg: DictConfig):
        return cls(
            
            room=cfg.room,
            
            weekday=cfg.weekday,
            
            startTime=cfg.startTime
            
        )

@dataclass
class Student(Person):
    """Студент университета"""
    
    
    enrolledIn: Optional['Course'] = field(
        default=None,
        metadata={"hydra": {"key": "enrolledIn"}} if True else {}
    )
    """enrolledIn (ObjectProperty)"""
    
    
    
    advisor: Optional['Professor'] = field(
        default=None,
        metadata={"hydra": {"key": "advisor"}} if True else {}
    )
    """advisor (ObjectProperty)"""
    
    
    
    studentId: str = field(
        default="",
        metadata={"hydra": {"key": "studentId"}} if True else {}
    )
    """studentId (DatatypeProperty)"""
    
    

    @classmethod
    def from_config(cls, cfg: DictConfig):
        return cls(
            
            enrolledIn=cfg.enrolledIn,
            
            advisor=cfg.advisor,
            
            studentId=cfg.studentId
            
        )
