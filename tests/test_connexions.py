"""Verifie que Python atteint PostgreSQL et MySQL."""
import os
import psycopg2
import pymysql
from dotenv import load_dotenv

load_dotenv("config/.env")


def test_postgres():
    for base in ("dwh_elevage", "src_cheptel"):
        conn = psycopg2.connect(
            host=os.getenv("PG_HOST"), port=os.getenv("PG_PORT"),
            dbname=base, user=os.getenv("PG_USER"),
            password=os.getenv("PG_PASSWORD"),
        )
        cur = conn.cursor()
        cur.execute("SHOW server_encoding;")
        print(f"PostgreSQL OK : {base} (encodage {cur.fetchone()[0]})")
        if base == "dwh_elevage":
            cur.execute(
                "SELECT string_agg(schema_name, ', ' ORDER BY schema_name) "
                "FROM information_schema.schemata "
                "WHERE schema_name IN ('staging','dwh','audit','ml','bi');"
            )
            print("  schemas :", cur.fetchone()[0])
        conn.close()


def test_mysql():
    conn = pymysql.connect(
        host=os.getenv("MYSQL_HOST"), port=int(os.getenv("MYSQL_PORT")),
        user=os.getenv("MYSQL_USER"), password=os.getenv("MYSQL_PASSWORD"),
        database=os.getenv("MYSQL_DB"),
    )
    cur = conn.cursor()
    cur.execute("SELECT @@character_set_database;")
    print(f"MySQL OK : {os.getenv('MYSQL_DB')} (encodage {cur.fetchone()[0]})")
    conn.close()


if __name__ == "__main__":
    test_postgres()
    test_mysql()
