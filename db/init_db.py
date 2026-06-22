"""
Crea la base de datos SQLite local a partir de db/schema.sql.
Uso: python db/init_db.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "job_matcher.db")
SCHEMA_PATH = os.path.join(os.path.dirname(__file__), "schema.sql")


def init_db():
    if os.path.exists(DB_PATH):
        print(f"⚠️  La base de datos ya existe en {DB_PATH}. No se ha modificado.")
        print("   Si quieres recrearla desde cero, bórrala antes de ejecutar este script.")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        cursor.executescript(f.read())

    conn.commit()
    conn.close()
    print(f"✅ Base de datos creada en {DB_PATH}")


if __name__ == "__main__":
    init_db()
