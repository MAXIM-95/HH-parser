#Делаем только асинхронный http-запрос, но базу оставляем обычной
#создаем новый файл async_http.py

from __future__ import annotations
import asyncio
from datetime import timedelta
#tenacity нужно для добавления повторных попыток при выполнении http-запроса (т.к. операция не стабильная)
from tenacity import retry, stop_after_attempt, wait_exponential_jitter, AsyncRetrying
from .config import HEADERS
from typing import Optional, Dict
import http.cookiejar as cookiejar
from pathlib import Path
import aiohttp
from aiohttp_client_cache import CachedSession, SQLiteBackend
import json
from yarl import URL

def load_cookies_from_file_async(
    path: str,
    default_domain: str = ".hh.ru",
    default_scheme: str = "https",
)->aiohttp.CookieJar:
    """
    Загружает cookies из файла (поддерживает:
    1) JSON-масиив [{name, value, domain. path, secure, ....}]
    2) Netscape cookies.txt)
    Возвращает aiohttp.CookieJar, готовый к использованию в aiohttp/CachedSession
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(f"Cookies file not found: {path}")

    text = p.read_text(encoding="utf-8", errors="ignore").lstrip()

    jar = aiohttp.CookieJar()
    added = 0

    #----------JSON формат------------------
    if text.startswith("["):
        data = json.loads(text)
        if not isinstance(data, list):
            raise ValueError("JSON cookies must be a list of cookies objects")

        for c in data:
            name = c.get("name")
            value = c.get("value", "")
            domain = c.get("domain") or default_domain
            #нормализуем домен: добавим ведущую точку, если нужно
            if not domain.startswith(".") and domain.count(".") >= 1:
                domain = "." + domain
            path = c.get("path", "/")
            secure = bool(c.get("secure", False))

            #для aiohttp важен response_url, чтобы понять, куда класть cookies
            scheme = "https" if secure else default_scheme
            response_url = URL(f"{scheme}://{domain.lstrip('.')}{path}")
            jar.update_cookies({name: value}, response_url = response_url)
            added += 1
            
        print(f"Загружено {added} cookies в формате JSON: {path}")
    
        return jar
    
        try:
            cj = cookiejar.MozillaCookieJar()
            cj.load(str(p), ignore_expires=True, ignore_discard=True)

            for c in cj:
                domain = c.domain or default_domain
                if not domain.startswith(".") and domain.count(".") >= 1:
                    domain = "." + domain
                scheme = "https" if c.secure else default_scheme
                path = c.path or "/"
                response_url = URL(f"{scheme}://{domain.lstrip('.')}{path}")
                jar.update_cookies({c.name: c.value}, responce_url = response_url)
                added += 1
                
            print(f"Загружено {added} cookies в формате Netscape: {path}")

            return jar
            
        except cookiejar.LoadError:
            raise ValueError("Файл с куки отсутствует")

#обновленный get_http_session (создает и настраивает асинхронную http-сессию 
#c кэшированием, пользовательскими заголовками и куками (авторизацией), если указаны cookies.txt)
async def get_http_session_async(
    cache_name: str = ".cache/http_cache_by_async.sqlite", 
    cache_ttl_minutes: int = 60,
    cookies_file: str | None = None,
)->CachedSession:
    """
    Возвращает aiohttp_client_cache.Cachedsession - это аналог request.Session, но асинхронный
    cache_ttl_minutes - время жизни кэша
    """
    backend = SQLiteBackend( #создаем файл кэша для сохранения http ответов
        cache_name, expire_after = timedelta(minutes=cache_ttl_minutes)
    )

    #создаем контейнер для кук
    if cookies_file:
        #если указан путь к файлу с куки, то загруждаем авторизационные 
        #куки, чтобы парсер работал в залогиненном состоянии
        jar = load_cookies_from_file_async(cookies_file) 
    else:
        jar = aiohttp.CookieJar() #иначе создаем пустой контейнер

    #создаем асинхронную сессию с кэшированием (аналог request.Session)
    s = CachedSession(
        cache = backend, #хранилище кэша
        headers = HEADERS, #заголовки (User-Agent и тд)
        cookies_jar = jar, #куки для авторизации
    )

    return s

#асинхронная безопасная пауза между запросами. Не блокирует другие запросы - она просто "усыпляет" только одну конкретную задачу
#например, если скачивается 10 вакансий одновременно и из них часть страниц уже есть в кэше, то они обработаются мгновенно, 
#а остальные с паузой между запросами 0.4 сек
async def safe_sleep_async(from_cache: bool, delay: float = 0.4):
    if not from_cache:
        await asyncio.sleep(delay)

#асинхронно получает html-страницу с помощью aiohttp + кэширования + повторов
async def http_get_async(session: CachedSession, #объект из get_http_session_async
                         url: str, #адрес страницы 
                         params: dict | None = None)->str: #словарь параметров запроса
    #повторяем запрос при временных сбоях до 5 раз
    async for attempt in AsyncRetrying(
        wait = wait_exponential_jitter(initial=0.5, max = 4), #между попытками экспоненциальная пауза + небольшой случайный разброс
        stop = stop_after_attempt(5), #максимум 5 попыток
        reraise = True,
    ):
        with attempt:
            async with session.get(url, params = params, timeout = 30) as resp: #отправляет get-запрос
                resp.raise_for_status() #проверка успешного выполнения (выбросит исключение, если статус 4хх/5хх)
                html = await resp.text() #асинхронно читает тело ответа как текст, затем это передается в BeautifulSoup
                await safe_sleep_async(getattr(resp, "from_cache", False)) #пауза
                return html #возвращаем строку для парсинга





