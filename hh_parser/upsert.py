from __future__ import annotations
from sqlalchemy import select
from sqlalchemy.orm import Session

from .models import Employer, Area, Skill, Vacancy, VacancySkill
from .schemas import VacancyDetail

#=============================================================================================
#Операции записи в БД
#функции ниже фактически выполняют "найди или создай" запись, предотвращают создание дублей
#если запись есть, то возвращают существующий объект
#если нет - создают новый и возвращают его
#=============================================================================================

#сохраняет навыки в базу
def upsert_skill(sess: Session, name: str)->Skill:
    #строим sql-запрос, который проверяет есть ли навык
    s = sess.execute(select(Skill).where(Skill.name == name)).scalar_one_or_none()

    if s: #если найден возвращаем skill
        return s
    s = Skill(name=name) #иначе создаем новый объект
    sess.add(s) #добавляем в текущую транзакцию
    sess.flush() #по факту выполняет SQL INSERT, чтобы получить id из БД

    return s

#сохраняет работодателя в базу
def upsert_employer(sess: Session, name: str | None):
    if not name: #проверяем передано ли имя
        return None
    e = sess.get(Employer, name) #пытаемся найти работодателя в базе
    if e:
        return e
    e = Employer(id=name, name=name) #если не нашли создаем нового
    sess.add(e) #добавляем новый объект в сессию, но не коммитим (коммит будет позже при sess.commit())

    return e

#сохраняет город/регион в базу
def upsert_area(sess: Session, name: str | None):
    if not name:
        return None
    a = sess.execute(select(Area).where(Area.name == name)).scalar_one_or_none()
    if a:
        return a
    #если не нашли создаем новый объект
    #тут используется конструкция для генерации уникального числового id на основе хэша имени
    a = Area(id=abs(hash(name)) % (10**9), name=name) 
    sess.add(a)

    return a

#сохраняет запись вакансии и связанные сущности (работодатель, регион, навыки) в базу 
def upsert_vacancy(sess: Session, d: VacancyDetail):
    #делаем upsert зависимостей (эти объекты потом прикрепятся к вакансии)
    e = upsert_employer(sess, d.employer_name)
    a = upsert_area(sess, d.area_name)
    #поиск существующей вакансии по уникальному id
    v = sess.execute(select(Vacancy).where(Vacancy.vacancy_id == d.vacancy_id)).scalar_one_or_none()

    if v: #если нашли, то обновляем все простые поля и FK-ссылки
        v.name, v.published_at, v.salary_from, v.salary_to, v.salary_currency = (
            d.name, d.published_at, d.salary_from, d.salary_to, d.salary_currency
        )
        v.schedule, v.employment, v.experience, v.url, v.employer, v.area = (
            d.schedule, d.employment, d.experience, d.url, e, a
        )
        #навыки пересобираем с нуля, благодаря cascade="all, delete-orphan" старые связи удаляются безопасно и создаются актуальные
        v.skills.clear()
        for s in d.skills:
            v.skills.append(VacancySkill(skill=upsert_skill(sess, s)))
        return v

    #если не нашли - создаем новую Vacancy
    v = Vacancy(
        vacancy_id = d.vacancy_id,
        name = d.name,
        published_at = d.published_at,
        salary_from = d.salary_from,
        salary_to = d.salary_to,
        salary_currency = d.salary_currency,
        schedule = d.schedule,
        employment = d.employment,
        experience = d.experience,
        url = d.url,
        employer = e,
        area = a
    )
    for s in d.skills:
        v.skills.append(VacancySkill(skill=upsert_skill(sess, s)))
    sess.add(v) #добавляем новый объект (commit выполнится снаружи)

    return v


