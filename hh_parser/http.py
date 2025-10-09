from datetime import timedelta
import time
import requests
import requests_cache
#tenacity нужно для добавления повторных попыток при выполнении http-запроса (т.к. операция не стабильная)
from tenacity import retry, stop_after_attempt, wait_exponential_jitter 
from .config import HEADERS

#данная функция создает и настраивает http-сессию с кэшем.Без кэша
#каждый раз при парсинге скрипт отправляет запросы на сайт. Если страниц много, то
#это нагружает сервер, замедляет работу, может привести к блокировке по ip
#в данном случае делается один реальный запрос, а далее читаются данные из локального кэша.
#Следовательно эконмится трафик и ускоряется обработка
def get_http_session(cache_name: str = ".cache/http_cache", cache_ttl_minutes: int = 60)->requests.Session:
    """
    Возвращает request Session с кэшированием (requests_cache)
    cache_ttl_minutes - время жизни кэша
    """
    requests_cache.install_cache(cache_name = cache_name, expire_after = timedelta(minutes=cache_ttl_minutes)) #создаем файл кэша
    #создаем http-сессию (этот объект хранит cookie, заголовки и настройки между запросами, а также переиспользует соединение)
    s = requests.Session() 
    #добавляем стандартные заголовки
    s.headers.update(HEADERS)

    return s

#отвечает за паузу между запросами
def safe_sleep(resp):
    #проверяем, если данные из кэша, то паузу не делаем, если запрос реальный - то пауза 0.4 сек
    if not getattr(resp, "from_cache", False): time.sleep(0.4)  

#отвечает за выполнение http-запроса
#этот декоратор для безопасных повторов. Делает до 5 попыток, если запрос завершился с ошибкой
@retry(wait=wait_exponential_jitter(initial=0.5, max=4), stop=stop_after_attempt(5)) 
def http_get(session: requests.Session, url: str, params: dict | None = None)->requests.Response:
    resp = session.get(url, params=params, timeout=30) #выполнение запроса с таймаутом 30 сек
    #проверка кода ответа.
    #если статус не 200, то выбрасываем исключение и декоратор @retry автоматически сделает новую попытку
    resp.raise_for_status()
    #пауза, если ответ не из кэша
    safe_sleep(resp)
    
    return resp