import sqlite3
import pandas as pd

#подключаемся к базе данных
conn = sqlite3.connect("hh_bs.sqlite3")

#посмотреть какие таблицы есть
tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table';", conn)
print("Таблицы:\n", tables)

#выводим первые 5 вакансий
#vacancies = pd.read_sql_query("SELECT * FROM vacancies LIMIT 5", conn)
#print(vacancies)

#выводим первые 10 вакансий и их зарплаты
query = """
SELECT name, salary_from, salary_to, salary_currency
FROM vacancies
LIMIT 10
"""
df = pd.read_sql_query(query, conn)
print(df)

conn.close()
