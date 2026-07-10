from database.connection import get_connection
from datetime import datetime

def search_suppliers(query: str) -> list[dict]:
    if not query or not query.strip():
        return []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM suppliers
                WHERE active = true
                AND (
                    name ILIKE %s
                    OR %s = ANY(aliases)
                    OR code ILIKE %s
                )
                ORDER BY name
                LIMIT 10
            """, (f'%{query}%', query.lower(), f'%{query}%'))
            return cur.fetchall()

def get_supplier_by_name(name: str) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM suppliers
                WHERE active = true
                AND name ILIKE %s
                LIMIT 1
            """, (name.strip(),))
            return cur.fetchone()

def get_supplier_by_code(code: str) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM suppliers
                WHERE code = %s AND active = true
            """, (code.upper().strip(),))
            return cur.fetchone()

def get_supplier_by_id(supplier_id: int) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM suppliers WHERE id = %s
            """, (supplier_id,))
            return cur.fetchone()

def create_supplier(name: str, created_by: int) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nextval('suppliers_seq')")
            seq = cur.fetchone()['nextval']
            code = f"PRO-{seq:04d}"
            cur.execute("""
                INSERT INTO suppliers (code, name, created_by)
                VALUES (%s, %s, %s)
                RETURNING *
            """, (code, name.strip(), created_by))
            conn.commit()
            return cur.fetchone()

def update_supplier(supplier_id: int, data: dict) -> dict:
    allowed = ['name', 'aliases', 'contact_name', 'phone']
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return None
    sets = ", ".join(f"{k} = %s" for k in updates)
    values = list(updates.values()) + [supplier_id]
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(f"""
                UPDATE suppliers
                SET {sets}
                WHERE id = %s
                RETURNING *
            """, values)
            conn.commit()
            return cur.fetchone()

def fuzzy_search_suppliers(query: str) -> list[dict]:
    if not query or not query.strip():
        return []
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT *, similarity(name, %s) as sim
                FROM suppliers
                WHERE active = true
                AND (
                    name ILIKE %s
                    OR similarity(name, %s) > 0.2
                    OR %s = ANY(aliases)
                )
                ORDER BY sim DESC, name
                LIMIT 5
            """, (query, f'%{query}%', query, query.lower()))
            return cur.fetchall()
