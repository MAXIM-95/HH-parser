import argparse
from .config import DEFAULT_DB_URL, DEFAULT_CACHE_NAME, DEFAULT_CACHE_TTL_MIN, DEFAULT_PER_PAGE
from .pipeline import crawl_and_store

def main():
    parser = argparse.ArgumentParser(description="HTML-парсер вакансий hh.ru (BeautifulSoup)")
    parser.add_argument("--text", required=True, help="Поисковый запрос (например, 'ML Engineer')") #поисковый запрос (обязательное поле)
    parser.add_argument("--area", type=int, help="ID региона (например, 1 - Москва, 2 - СПБ и тд)") #id региона
    parser.add_argument("--pages", type=int, default=1, help="Количество страниц") #кол-во страниц для парсинга
    parser.add_argument("--per-page", type=int, default=DEFAULT_PER_PAGE) #кол-во вакансий на странице
    parser.add_argument("--db", default=DEFAULT_DB_URL) #строка подключения к БД
    parser.add_argument("--cache-ttl", type=int, default=DEFAULT_CACHE_TTL_MIN) #срок жизни кэша запросов (в мин)
    parser.add_argument("--cache-name", default=DEFAULT_CACHE_NAME)
    args = parser.parse_args()

    crawl_and_store(
        db_url = args.db,
        text = args.text,
        pages = args.pages,
        per_page = args.per_page,
        area = args.area,
        cache_ttl = args.cache_ttl,
        cache_name = args.cache_name,
    )

#конструкция ниже нужна для того, чтобы:
#1)если запускаем файл напрямую -> сработает main
#2)если импортируем код, как модуль, то main не выполнится и можно использовать отдельные функции
if __name__ == "__main__": 
    main()

