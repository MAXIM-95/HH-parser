from __future__ import annotations
import re
from datetime import datetime, timedelta, timezone
from typing import Optional, List
from bs4 import BeautifulSoup
from .schemas import VacancyBrief, VacancyDetail

#-------------------------------------HTML-парсинг----------------------------------------------
VACANCY_ID_RE = re.compile(r"/vacancy/(\d+)") #регулярное выражение, с помощью которого парсер извлекает ID вакансии из ссылки
SALARY_RE = re.compile(r"(\d[\d\s\u00A0]*)", re.UNICODE) #регулярное выражение для извлечения чисел из текста з/п

#принимает объект BS и возвращает его текстовое содержимое, иначе None
def text_or_none(node): 
    return node.get_text(strip=True) if node else None

#превращает текст з/п из html hh в структурированные поля 
def parse_salary(s):
    if not s: return None, None, None
    cur = "RUR" if "руб" in s else None
    nums = [int(re.sub(r"\D+", "", m)) for m in SALARY_RE.findall(s)] #все числа с учетом пробелов и неразрывных пробелов
    if "от" in s and nums: 
        return nums[0], None, cur
    if "до" in s and nums: 
        return None, nums[0], cur
    if len(nums) >= 2: 
        return nums[0], nums[1], cur
    return nums[0], nums[0], cur if nums else (None, None, cur)

#преобразовывает текст даты публикации вакансии из html в datetime с врем. зоной utc
def parse_published_at(s):
    if not s: return datetime.now(timezone.utc) #проверяем есть ли вход
    lower = s.lower()
    now = datetime.now(timezone.utc)
    if "сегодня" in lower: return now #возвращаем сегодняшнюю дату
    if "вчера" in lower: return now - timedelta(days=1) #возвращаем вчерашнюю дату
    m = re.search(r"(\d{1,2})\s+([а-яё]+)\s+(\d{4})?", lower)
    months = {"января":1, "февраля":2, "марта":3, "апреля":4, "мая":5, "июня":6, "июля":7, "августа":8, "сентября":9, "октября":10, "ноября":11, "декабря":12}
    if m: #ищем шаблон день+месяц+(опционально год)
        day, mon = int(m.group(1)), months.get(m.group(2))
        year = int(m.group(3)) if m.group(3) else now.year
        if mon: return datetime(year, mon, day, tzinfo=timezone.utc) #возвращает дату в utc
    return now #возвращаем текущую дату


#парсит html в BS (вытаскивает краткие карточки и превращает их в список VacancyBrief)
def parse_list_page(html: str)->List[VacancyBrief]:
    soup = BeautifulSoup(html, "html.parser")
    #используем несколько селекторов сразу, чтобы пережить изменения в верстке
    cards = soup.select('div.serp-item, div.vacancy-serp-item, div[data-qa="vacancy-serp__vacancy"]') 
    out = []
    for card in cards: #в каждой карточке ищем заголовок и ссылку
        title = card.select_one('a[data-qa="serp-item__title"]') #заголовок
        if not title:
            continue
        url = title["href"].split("?")[0] #из ссылки берем чистый url
        m = VACANCY_ID_RE.search(url) #извлекаем id вакансии
        if not m: #если не удалось вытащить id - пропускаем карточку
            continue
        v_id = int(m.group(1)) 
        #вытаскиваем доп. поля. Берем через text_or_none, чтобы не падать, если нет узла
        emp = text_or_none(card.select_one('[data-qa="vacancy-serp__vacancy-employer"]'))
        area = text_or_none(card.select_one('[data-qa="vacancy-serp__vacancy-address"]'))
        pub = text_or_none(card.select_one('[data-qa="vacancy-serp__vacancy-date"]'))
        #складываем все данные в VacancyBrief и возвроащаем список таких объектов
        out.append(VacancyBrief(v_id, title.text.strip(), url, emp, area, pub))
        
    return out


#преобразует html страницу конкретной вакансии в объект VacancyDetail
def parse_vacancy_detail(html: str, url: str, brief: VacancyBrief)->VacancyDetail:
    soup = BeautifulSoup(html, "html.parser") #парсим html
    #Основные поля (название, работодатель, город) берем селекторами со страницы, 
    #если ничего нет - подставляем значения из VacancyBrief
    name = text_or_none(soup.select_one('h1[data-qa="vacancy-title"]')) or brief.name
    emp = text_or_none(soup.select_one('[data-qa="vacancy-company-name"]')) or brief.employer_name
    area = text_or_none(soup.select_one('[data-qa="vacancy-view-location"]')) or brief.area_name
   
    salary_text = text_or_none(soup.select_one('[data-qa="vacancy-salary"], [data-qa="vacancy-view-salary"]'))  #блок зарплаты 
    s_from, s_to, s_cur = parse_salary(salary_text) #передаем блок зп в parse_salary
    
    #опыт, занятость и график вытаскиваем из соответствующих элементов.
    experience = text_or_none(soup.select_one('[data-qa="vacancy-experience"]'))
    employment = text_or_none(soup.select_one('[data-qa="vacancy-view-employment-mode"]'))
    schedule = text_or_none(soup.select_one('[data-qa="vacancy-schedule"]'))
    #навыки (собираем все элементы в список строк)
    skills = [t.text.strip() for t in soup.select('[data-qa="skills-element"]')]
    #дата публикации. Берем ее из карточки, если нет - текст из списка
    pub = text_or_none(soup.select_one('[data-qa="vacancy-view-creation-time"]')) or brief.published_at_text
    published_at = parse_published_at(pub) #приводим дату к datetime utc

    m = VACANCY_ID_RE.search(url) #вытаскиваем id вакансии
    v_id = int(m.group(1)) if m else brief.vacancy_id

    #возвроащаем полностью заполненный VacancyDetail, который дальше сохраним в БД
    return VacancyDetail(v_id, name, url, emp, area, published_at, s_from, s_to, s_cur, schedule, employment, experience, skills)


