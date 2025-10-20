#async_pipeline.py
from __future__ import annotations
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from .config import SEARCH_URL
from .models import Base
from .parsing import parse_list_page
from .schemas import VacancyBrief
from .upsert import upsert_vacancy
from .parsing import parse_vacancy_detail
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, AsyncRetrying

import requests
from typing import Optional, List

import asyncio
from .async_http import get_http_session_async, http_get_async

#асинхронное пролистывание страниц. Грузит страницы из списка последовательно, 
#но детали вакансий - параллельно с лимитом на одновременные запросы
async def fetch_vacancy_detail_async(session, brief: VacancyBrief)->tuple[VacancyBrief, str]:
    html = await http_get_async(session, brief.url)
    return (brief, html)

#сюда внесены изменения (теперь передаем файл с куки)
async def crawl_and_store_async(
    db_url: str, #
    text: str, #поисковая строка
    pages: int = 1, #сколько страниц пройти (у hh нумерация с 0)
    per_page: int = 50, #сколько вакансий на странице (обычно от 10 до 100)
    area: Optional[int] = None, #необязательный id региона
    cache_ttl: int = 60, #время жизни кэша запросов в минутах
    cache_name: str = ".cache/http_cache_bs_async.sqlite", #путь к файлу кэша
    cookies_file: Optional[str] = None, #путь к файлу с куки
    concurrency: int = 8, #максимум одновременных запросов к сайту
):
    http = await get_http_session_async(cache_name, cache_ttl, cookies_file) #создаем асинхронную http-сессия с кэшем
    engine = create_engine(db_url, future = True) #подключаемся к БД
    Base.metadata.create_all(engine) #создаем таблицы при первом запуске
    
    total = 0
    sem = asyncio.Semaphore(concurrency) #ограничиваем число одновременных запросов
    
    async with http: #открываем транзакцию
        for p in range(pages): #цикл по страницам
            #1) страница списка
            list_html = await http_get_async(http, SEARCH_URL, {
                "text": text, "page": p, "items_on_page": per_page, "area": area
            }) #извлекаем html текущей страницы поиска

            briefs = parse_list_page(list_html) #парсим список карточек вакансий
            if not briefs: #если пусто выходим
                break

            #2) асинхронная загрузка деталей вакансии
            async def fetch(brief: VacancyBrief):
                async with sem:
                    return await fetch_vacancy_detail_async(http, brief)

            #для каждой вакансии создаем asyncio.Task, которая скачивает ее детальную страницу   
            tasks = [asyncio.create_task(fetch(br)) for br in briefs]
            #отбираем результаты (если какая-то страница не загрузилась, программа не падает - ошибки сохраняются в result в виде Exception)
            results = await asyncio.gather(*tasks, return_exceptions = True)

            #3) запись в БД (синхронно)
            with Session(engine) as sess:
                for res in results:
                    if isinstance(res, Exception):
                        continue
                    brief, html = res
                    det = parse_vacancy_detail(html, brief.url, brief) #детальный парсинг каждой вакансии
                    upsert_vacancy(sess, det)  #сохраняем (обновляем) в БД, включая работодателя, регион, навыки
                    total += 1
                sess.commit() #фиксация изменения

        print(f"Сохранено вакансий (async HTTP): {total}")


