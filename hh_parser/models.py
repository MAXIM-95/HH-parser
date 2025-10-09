from __future__ import annotations
from datetime import datetime
from typing import Optional, List


from sqlalchemy import (
    String, Integer, DateTime, ForeignKey, UniqueConstraint, func 
)

from sqlalchemy.orm import(
    DeclarativeBase,
    Mapped,
    mapped_column,
    relationship
)

#---------------------------------------------БД-модель-------------------------------------------------------
class Base(DeclarativeBase): #базовый класс
    pass

#таблица с данными о работодателях
class Employer(Base): 
    __tablename__ = "employers"
    id: Mapped[str] = mapped_column(String(32), primary_key=True) #уникальный id работодателя
    name: Mapped[str] = mapped_column(String(512), index=True) #название компании
    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="employer") #список связанных вакансий (двухсторонняя связь с таблицей вакансий)
    
#таблица с регионами
class Area(Base): 
    __tablename__ = "areas"
    id: Mapped[int] = mapped_column(Integer, primary_key=True) #id региона в API HH.ru
    name: Mapped[str] = mapped_column(String(256)) #название региона
    vacancies: Mapped[List["Vacancy"]] = relationship(back_populates="area") #у каждой вакансии есть ссылка на area_id (связь один ко многим)

#таблица с навыками
class Skill(Base): 
    __tablename__ = "skills"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True) #уникальный id навыка
    name: Mapped[str] = mapped_column(String(256)) #название навыка
    vacancy_links: Mapped[List["VacancySkill"]] = relationship(back_populates="skill") #связь многие ко многим через таблицу VacancySkill


#центральная таблица, через которую связаны все остальные
class Vacancy(Base): 
    __tablename__ = "vacancies"
    __table_args__ = (UniqueConstraint("vacancy_id", name = "uq_vacancy_id"),) #не даем добавить дубликаты

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True) 
    vacancy_id: Mapped[int] = mapped_column(Integer, index=True) #уникальный id вакансии, который содержится в ее URL
    name: Mapped[str] = mapped_column(String(512), index=True) #название вакансии
    published_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), index=True) #дата публикации
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default = func.now()) #время записи в БД
    
    salary_from: Mapped[Optional[int]] = mapped_column(Integer, nullable=True) #диапазон з/п
    salary_to: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    salary_currency: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)

    schedule: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) #тип занятости (удаленная, офис, гибрид)
    employment: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) #формат занятости (полная, частичная и тд)
    experience: Mapped[Optional[str]] = mapped_column(String(64), nullable=True) #требуемый опыт

    url: Mapped[str] = mapped_column(String(1024)) #здесь хранится адрес вакансии на hh

    employer_id: Mapped[Optional[str]] = mapped_column(String(32), ForeignKey("employers.id"), nullable=True) #ссылка на работодателя
    area_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("areas.id"), nullable=True, index=True) #ссылка на регион

    employer: Mapped[Optional["Employer"]] = relationship(back_populates="vacancies")
    area: Mapped[Optional["Area"]] = relationship(back_populates="vacancies") 
    skills: Mapped[List["VacancySkill"]] = relationship(back_populates="vacancy", cascade="all, delete-orphan") #связь многие ко многим через VacancySkill


#соединяет таблицы Vacancy и Skill (реализует связь многие ко многим)
class VacancySkill(Base): 
    __tablename__ = "vacancy_skills"
    __table_args__ = (UniqueConstraint("vacancy_db_id", "skill_id", name="uq_vacancy_skill"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True) 
    vacancy_db_id: Mapped[int] = mapped_column(Integer, ForeignKey("vacancies.id")) #внешний ключ на таблицу вакансий
    skill_id: Mapped[int] = mapped_column(Integer, ForeignKey("skills.id")) #внешний ключ на таблицу навыков

    vacancy: Mapped["Vacancy"] = relationship(back_populates = "skills") #объектная ссылка на вакансию
    skill: Mapped["Skill"] = relationship(back_populates = "vacancy_links") #объектная ссылка на навыки


    

