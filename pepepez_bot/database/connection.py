import psycopg2
from psycopg2.extras import RealDictCursor
import os
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

def get_connection():
    return psycopg2.connect(DATABASE_URL, cursor_factory=RealDictCursor)

def get_user(telegram_id: int):
    """Verifica si un usuario está autorizado."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM users WHERE telegram_id = %s AND active = true",
                (telegram_id,)
            )
            return cur.fetchone()

def add_user(telegram_id: int, name: str, role: str = 'staff', area: str = None, local: str = None):
    """Agrega un usuario a la lista blanca."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (telegram_id, name, role, area, local)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (telegram_id) DO UPDATE
                SET active = true, removed_at = NULL
                RETURNING *
            """, (telegram_id, name, role, area, local))
            conn.commit()
            return cur.fetchone()

def remove_user(telegram_id: int):
    """Desactiva un usuario — silencio total desde ese momento."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users 
                SET active = false, removed_at = NOW()
                WHERE telegram_id = %s
            """, (telegram_id,))
            conn.commit()
            return cur.rowcount > 0

def list_users():
    """Lista todos los usuarios activos."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT telegram_id, name, role, area, local, created_at
                FROM users WHERE active = true
                ORDER BY role, name
            """)
            return cur.fetchall()
