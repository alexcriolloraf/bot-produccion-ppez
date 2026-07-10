from database.connection import get_connection
from datetime import datetime
import pytz

ECUADOR_TZ = pytz.timezone("America/Guayaquil")

def generate_lot_code(product_prefix: str) -> str:
    """
    Genera código de lote: PREFIX-DDMMYY-NN
    Ejemplo: YUC-070726-01, COR-070726-02
    """
    now = datetime.now(ECUADOR_TZ)
    date_part = now.strftime('%d%m%y')
    
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT COUNT(*) as cnt FROM lots 
                WHERE product_prefix = %s 
                AND lot_code LIKE %s
            """, (product_prefix, f"{product_prefix}-{date_part}-%"))
            count = cur.fetchone()['cnt']
            return f"{product_prefix}-{date_part}-{count + 1:02d}"

def create_lot(
    lot_code: str,
    product_prefix: str,
    product_name: str,
    initial_weight: float,
    initial_unit: str,
    created_by: int,
    lot_source: str = 'generado',
    supplier_name: str = None
) -> dict:
    """Crea un nuevo lote ACTIVO."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO lots (
                    lot_code, product_prefix, product_name,
                    lot_source, initial_weight, initial_unit,
                    current_weight, supplier_name, status, created_by
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 'activo', %s)
                RETURNING *
            """, (
                lot_code, product_prefix, product_name,
                lot_source, initial_weight, initial_unit,
                initial_weight, supplier_name, created_by
            ))
            conn.commit()
            return cur.fetchone()

def get_active_lots_by_product(product_prefix: str) -> list:
    """Retorna todos los lotes activos de un producto."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM lots 
                WHERE product_prefix = %s 
                AND status = 'activo'
                ORDER BY created_at DESC
            """, (product_prefix,))
            return cur.fetchall()

def get_lot_by_code(lot_code: str) -> dict:
    """Busca un lote por su código."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM lots WHERE lot_code = %s",
                (lot_code,)
            )
            return cur.fetchone()

def close_lot(lot_code: str, closed_by: int) -> dict:
    """Cierra un lote — ya no aparece en botones."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE lots 
                SET status = 'cerrado',
                    closed_at = NOW(),
                    closed_by = %s
                WHERE lot_code = %s
                RETURNING *
            """, (closed_by, lot_code))
            conn.commit()
            return cur.fetchone()

def update_lot_weight(lot_id: int, weight_used: float) -> dict:
    """Descuenta peso del lote (cuando producción usa parte)."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE lots 
                SET current_weight = current_weight - %s
                WHERE id = %s
                RETURNING *
            """, (weight_used, lot_id))
            conn.commit()
            return cur.fetchone()

def check_media_group(media_group_id: str) -> dict:
    """Verifica si ya se procesó un álbum."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM media_groups WHERE media_group_id = %s",
                (media_group_id,)
            )
            return cur.fetchone()

def register_media_group(media_group_id: str, record_id: int, record_table: str) -> dict:
    """Registra que un álbum ya fue procesado."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO media_groups (media_group_id, record_id, record_table)
                VALUES (%s, %s, %s)
                ON CONFLICT (media_group_id) DO NOTHING
                RETURNING *
            """, (media_group_id, record_id, record_table))
            conn.commit()
            return cur.fetchone()

def add_photo_to_record(record_id: int, record_table: str, file_id: str):
    """Agrega una foto adicional a un registro existente."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO record_photos (record_id, record_table, file_id)
                VALUES (%s, %s, %s)
            """, (record_id, record_table, file_id))
            conn.commit()
