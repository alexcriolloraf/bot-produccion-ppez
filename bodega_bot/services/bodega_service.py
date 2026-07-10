from database.connection import get_connection
import pytz
from datetime import datetime

ECUADOR_TZ = pytz.timezone("America/Guayaquil")

RECORD_CODES = {
    'ingreso':      'ING',
    'despacho':     'DSP',
    'devolucion':   'DEV',
    'inventario':   'INV',
    'novedad':      'NOV',
    'mantenimiento':'MNT',
    'apertura':     'APE',
    'cierre':       'CIE',
    'requerimiento':'REQ',
}

def generate_code(prefix: str) -> str:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nextval('bodega_seq')")
            seq = cur.fetchone()['nextval']
            return f"{prefix}-{seq:04d}"

def generate_req_code() -> str:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nextval('req_seq')")
            seq = cur.fetchone()['nextval']
            return f"REQ-{seq:04d}"

def save_bodega_record(
    telegram_user_id: int,
    record_type: str,
    product: str = None,
    weight_kg: float = None,
    unit: str = None,
    supplier_name: str = None,
    location_name: str = None,
    location_id: int = None,
    file_id: str = None,
    notes: str = None
) -> dict:
    prefix = RECORD_CODES.get(record_type, 'BOD')
    code = generate_code(prefix)

    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO bodega_records (
                    record_code, telegram_user_id, record_type,
                    product, weight_kg, unit,
                    supplier_name, location_id, location_name,
                    file_id, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                code, telegram_user_id, record_type,
                product, weight_kg, unit,
                supplier_name, location_id, location_name,
                file_id, notes
            ))
            conn.commit()
            return cur.fetchone()

def get_record_by_code(code: str) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM bodega_records WHERE record_code = %s",
                (code,)
            )
            return cur.fetchone()
