import psycopg2
from database.connection import get_connection

def generate_code(prefix: str) -> str:
    """Genera código único: PRD-0001, MRM-0042, etc."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nextval('record_seq')")
            seq = cur.fetchone()['nextval']
            return f"{prefix}-{seq:04d}"

def save_record(
    telegram_user_id: int,
    record_type: str,
    record_code: str,
    product: str = None,
    weight_kg: float = None,
    unit: str = None,
    quantity: int = None,
    destination: str = None,
    supplier: str = None,
    file_id: str = None,
    notes: str = None
) -> dict:
    """Guarda un registro en la base de datos."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO records (
                    record_code, telegram_user_id, record_type,
                    product, weight_kg, unit, quantity,
                    destination, supplier, file_id, notes
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                record_code, telegram_user_id, record_type,
                product, weight_kg, unit, quantity,
                destination, supplier, file_id, notes
            ))
            conn.commit()
            return cur.fetchone()

def save_ticket(
    record_id: int,
    ticket_type: str,
    description: str,
    reported_by: int,
    supplier: str = None
) -> dict:
    """Crea un ticket de novedad o mantenimiento."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT nextval('ticket_seq')")
            seq = cur.fetchone()['nextval']
            ticket_code = f"NOV-{seq:04d}"

            cur.execute("""
                INSERT INTO tickets (
                    ticket_code, record_id, ticket_type,
                    description, reported_by, supplier
                ) VALUES (%s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                ticket_code, record_id, ticket_type,
                description, reported_by, supplier
            ))
            conn.commit()
            return cur.fetchone()
