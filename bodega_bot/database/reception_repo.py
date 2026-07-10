from database.connection import get_connection
from services.lot_service import generate_reception_code, generate_reception_lot_code
from datetime import datetime
import pytz

ECUADOR_TZ = pytz.timezone("America/Guayaquil")

def create_reception(supplier_id: int, supplier_name: str, file_id: str, created_by: int) -> dict:
    code = generate_reception_code()
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO receptions (reception_code, supplier_id, supplier_name, file_id, created_by)
                VALUES (%s, %s, %s, %s, %s)
                RETURNING *
            """, (code, supplier_id, supplier_name, file_id, created_by))
            conn.commit()
            return cur.fetchone()

def add_reception_items(reception_id: int, items_data: list[dict]) -> list[dict]:
    created = []
    with get_connection() as conn:
        with conn.cursor() as cur:
            for item in items_data:
                cur.execute("""
                    INSERT INTO reception_items
                        (reception_id, product_name, product_prefix, lot_code, supplier_lot)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING *
                """, (
                    reception_id,
                    item['product_name'],
                    item.get('product_prefix'),
                    item['lot_code'],
                    item.get('supplier_lot'),
                ))
                created.append(cur.fetchone())
            conn.commit()
    return created

def get_open_receptions() -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.*,
                    (SELECT COUNT(*) FROM reception_items WHERE reception_id = r.id AND status = 'pendiente') as pending_count,
                    (SELECT COUNT(*) FROM reception_items WHERE reception_id = r.id) as total_count
                FROM receptions r
                WHERE r.status = 'abierto'
                ORDER BY r.created_at ASC
            """)
            return cur.fetchall()

def get_reception_by_id(reception_id: int) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT r.*,
                    (SELECT COUNT(*) FROM reception_items WHERE reception_id = r.id AND status = 'pendiente') as pending_count,
                    (SELECT COUNT(*) FROM reception_items WHERE reception_id = r.id) as total_count
                FROM receptions r
                WHERE r.id = %s
            """, (reception_id,))
            return cur.fetchone()

def get_pending_items(reception_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM reception_items
                WHERE reception_id = %s AND status = 'pendiente'
                ORDER BY id ASC
            """, (reception_id,))
            return cur.fetchall()

def get_weighed_items(reception_id: int) -> list[dict]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM reception_items
                WHERE reception_id = %s AND status = 'pesado'
                ORDER BY id ASC
            """, (reception_id,))
            return cur.fetchall()

def get_item_by_id(item_id: int) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM reception_items WHERE id = %s", (item_id,))
            return cur.fetchone()

def weigh_item(item_id: int, weight_kg: float, unit: str, weighed_by: int) -> dict:
    now = datetime.now(ECUADOR_TZ)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE reception_items
                SET weight_kg = %s, unit = %s, status = 'pesado',
                    weighed_by = %s, weighed_at = %s
                WHERE id = %s AND status = 'pendiente'
                RETURNING *
            """, (weight_kg, unit, weighed_by, now, item_id))
            conn.commit()
            return cur.fetchone()

def check_all_items_weighed(reception_id: int) -> bool:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as pending FROM reception_items
                WHERE reception_id = %s AND status = 'pendiente'
            """, (reception_id,))
            result = cur.fetchone()
            return result['pending'] == 0

def close_reception(reception_id: int) -> dict:
    now = datetime.now(ECUADOR_TZ)
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE receptions
                SET status = 'completado', closed_at = %s
                WHERE id = %s AND status = 'abierto'
                RETURNING *
            """, (now, reception_id))
            conn.commit()
            return cur.fetchone()

def get_reception_summary(reception_id: int) -> dict:
    reception = get_reception_by_id(reception_id)
    if not reception:
        return None
    pending = get_pending_items(reception_id)
    weighed = get_weighed_items(reception_id)
    return {
        'reception': reception,
        'pending': pending,
        'weighed': weighed,
    }
