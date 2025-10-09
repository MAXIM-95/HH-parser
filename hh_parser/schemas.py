from __future__ import annotations
from dataclasses import dataclass #для упрощенного написания классов (чтобы не писать __init__ и тд)
from datetime import datetime
from typing import Optional, List

#--------------------------------Дата-классы --------------------------------------

@dataclass
#данный класс контейнер данных, который описывает короткую карточку вакансии из общего списка на hh
class VacancyBrief:
    vacancy_id: int #уникальный id вакансии
    name: str #название вакансии
    url: str #прямая ссылка на страницу вакансии
    employer_name: Optional[str] #название работодателя
    area_name: Optional[str] #название региона
    published_at_text: Optional[str] #текст даты публикации

@dataclass
#данный класс представляет полное описание вакансии, получаемое с внутренней страницы вакансии
#https://hh.ru/vacancy/<id>
class VacancyDetail:
    vacancy_id: int
    name: str
    url: str
    employer_name: Optional[str]
    area_name: Optional[str]
    published_at: datetime
    salary_from: Optional[int] #нижняя граница з/п
    salary_to: Optional[int] #верхняя граница з/п
    salary_currency: Optional[str] #RUR, руб
    schedule: Optional[str] #формат работы (полный, удален. и тд)
    employment: Optional[str] #тип занятости (полная, частичная)
    experience: Optional[str] #опыт
    skills: List[str] #список ключевых навыков
