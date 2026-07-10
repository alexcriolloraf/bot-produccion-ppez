import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def get_user(telegram_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE telegram_id = %s AND active = true",
                (telegram_id,)
            )
            return cur.fetchone()

def get_all_locations():
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM locations WHERE active = true ORDER BY name")
            return cur.fetchall()

def get_location_by_code(code: str):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM locations WHERE code = %s", (code,))
            return cur.fetchone()

def add_user(telegram_id: int, name: str, role: str = 'staff'):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (telegram_id, name, role, active)
                VALUES (%s, %s, %s, true)
                ON CONFLICT (telegram_id) DO UPDATE
                SET active = true, removed_at = NULL
                RETURNING *
            """, (telegram_id, name, role))
            conn.commit()
            return cur.fetchone()

def remove_user(telegram_id: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users 
                SET active = false, removed_at = NOW()
                WHERE telegram_id = %s
            """, (telegram_id,))
            conn.commit()
            return cur.rowcount > 0
