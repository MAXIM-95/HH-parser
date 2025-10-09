from datetime import timedelta

#-------------------------------------------
# Константы
#--------------------------------------------
SEARCH_URL = "https://hh.ru/search/vacancy"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; HHParserBot/1.0; +https://example.com/bot)",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
}

DEFAULT_CACHE_NAME = ".cache/http_cache_bs"
DEFAULT_CACHE_TTL_MIN = 60
DEFAULT_DB_URL = "sqlite:///hh_bs.sqlite3"
DEFAULT_PER_PAGE = 50

