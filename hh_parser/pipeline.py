from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .config import SEARCH_URL
from .http import get_http_session, http_get, safe_sleep
from .models import Base
from .parsing import parse_list_page
from .schemas import VacancyBrief
from .upsert import upsert_vacancy
from .parsing import parse_vacancy_detail
from tenacity import retry, stop_after_attempt, wait_exponential_jitter

import requests

#данная функция отвечает за загрузку html-страницы конкретной вакансии с hh и ее разбор через parse_vacancy_detail
@retry(wait=wait_exponential_jitter(initial=0.5, max=4), stop=stop_after_attempt(5))
def fetch_vacancy_detail(session: requests.Session, url: str, brief: VacancyBrief):
    r = session.get(url, timeout=30) #берем html конкретной страницы (с кэшем, если включен)
    r.raise_for_status() #проверка статуса (выбрасываем исключение, если сервер вернул ошибку)
    safe_sleep(r) #пауза между запросами
    return parse_vacancy_detail(r.text, url, brief) #разбираем html и возвращаем VacancyDetail

#данная функция ходит по страницам поиска, грузит карточки вакансий, извлекает детали и сохраняет в БД
def crawl_and_store(
    db_url: str, #
    text: str, #поисковая строка
    pages: int = 1, #сколько страниц пройти (у hh нумерация с 0)
    per_page: int = 50, #сколько вакансий на странице (обычно от 10 до 100)
    area: int | None = None, #необязательный id региона
    cache_ttl: int = 60, #время жизни кэша запросов в минутах
    cache_name: str = ".cache/http_cache_bs", #путь к файлу кэша
):
    http = get_http_session(cache_name, cache_ttl) #http-сессия с кэшем
    engine = create_engine(db_url, future = True) #подключаемся к БД
    Base.metadata.create_all(engine) #создаем таблицы при первом запуске
    total = 0
    
    with Session(engine) as sess: #открываем транзакцию
        for p in range(pages): #цикл по страницам
            html = http_get(http, SEARCH_URL, {"text": text, "page": p, "items_on_page": per_page, "area": area}).text #извлекаем html страницы поиска
            briefs = parse_list_page(html) #парсим список карточек вакансий
            if not briefs: #если пусто выходим
                break;

            for br in briefs: #цикл по карточкам вакансий
                det = fetch_vacancy_detail(http, br.url, br) #для каждой вакансии грузим детальную страницу
                upsert_vacancy(sess, det)  #сохраняем (обновляем) в БД, включая работодателя, регион, навыки
                total += 1
            sess.commit() #фиксация изменения

        print(f"Сохранено вакансий: {total}")