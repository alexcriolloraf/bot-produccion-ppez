from telegram import Update
from telegram.ext import ContextTypes
from database.connection import get_user, get_connection
from services.classifier import extract_weight_from_text
from services.sheets_service import append_bodega_record
from datetime import datetime
import pytz
import re

ECUADOR_TZ = pytz.timezone("America/Guayaquil")

def get_root_code(code: str) -> str:
    return re.sub(r'(-C\d+)+$', '', code)

def get_record_by_code(code: str) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM bodega_records WHERE record_code = %s", (code,))
            return cur.fetchone()

def get_latest_active_record(root_code: str) -> dict:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT * FROM bodega_records 
                WHERE (record_code = %s OR record_code LIKE %s)
                AND status != 'corregido'
                ORDER BY created_at DESC
                LIMIT 1
            """, (root_code, f"{root_code}-C%"))
            return cur.fetchone()

def create_correction(active_record: dict, root_code: str, new_data: dict, corrected_by: int):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE bodega_records 
                SET is_corrected = TRUE, status = 'corregido'
                WHERE id = %s
                RETURNING *
            """, (active_record['id'],))
            original = cur.fetchone()

            cur.execute("""
                SELECT COUNT(*) as cnt FROM bodega_records 
                WHERE record_code LIKE %s
            """, (f"{root_code}-C%",))
            count = cur.fetchone()['cnt']
            correction_code = f"{root_code}-C{count + 1}"

            cur.execute("""
                INSERT INTO bodega_records (
                    record_code, telegram_user_id, record_type,
                    product, weight_kg, unit, supplier_name,
                    file_id, notes, status,
                    correction_of, correction_reason
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING *
            """, (
                correction_code,
                corrected_by,
                active_record['record_type'],
                new_data.get('product') or active_record['product'],
                new_data.get('weight_kg') or active_record['weight_kg'],
                new_data.get('unit') or active_record['unit'],
                active_record["supplier_name"],
                new_data.get('file_id') or active_record['file_id'],
                new_data.get('notes', ''),
                'activo',
                active_record['id'],
                new_data.get('reason', 'Correccion de registro')
            ))
            correction = cur.fetchone()
            conn.commit()
            return original, correction

async def handle_correction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        return

    text = update.message.text.strip()
    text_lower = text.lower()

    if 'corregir' not in text_lower:
        return

    clean_text = re.sub(r'corregir', '', text_lower).strip()

    code = None
    code_match = re.search(r'([A-Z]{2,3}-\d{4}(?:-C\d+)*)', text.upper())
    if code_match:
        code = code_match.group(1)

    if not code:
        reply = update.message.reply_to_message
        if reply:
            reply_text = reply.text or reply.caption or ''
            code_match = re.search(r'([A-Z]{2,3}-\d{4}(?:-C\d+)*)', reply_text.upper())
            if code_match:
                code = code_match.group(1)

    if not code:
        await update.message.reply_text(
            "No encontre el codigo.\n"
            "Ejemplo: corregir POR-0001 45kg"
        )
        return

    root_code = get_root_code(code)
    active_record = get_latest_active_record(root_code)

    if not active_record:
        await update.message.reply_text(f"No encontre registros activos para {root_code}.")
        return

    new_data = {}
    peso_info = extract_weight_from_text(clean_text)
    if peso_info:
        new_data['weight_kg'] = peso_info['valor']
        new_data['unit'] = peso_info['unidad']
        new_data['reason'] = (
            f"Peso corregido: {active_record['weight_kg']} "
            f"{active_record['unit']} a "
            f"{peso_info['valor']} {peso_info['unidad']}"
        )

    if update.message.photo:
        new_data['file_id'] = update.message.photo[-1].file_id

    if not new_data:
        await update.message.reply_text(
            "No detecte que corregir.\n"
            "Ejemplo: corregir POR-0001 45kg"
        )
        return

    new_data['notes'] = clean_text
    original, correction = create_correction(
        active_record=active_record,
        root_code=root_code,
        new_data=new_data,
        corrected_by=user_id
    )

    append_bodega_record(correction, user['name'])

    now = datetime.now(ECUADOR_TZ)
    ahora = now.strftime('%H:%M')
    fecha = now.strftime('%d/%m/%Y')

    respuesta = (
        f"CORRECCION REGISTRADA\n"
        f"------------------------\n"
        f"Corregido: {original['record_code']}\n"
        f"  Peso anterior: {original['weight_kg']} {original['unit'] or ''}\n"
        f"  Estado: CORREGIDO\n\n"
        f"Nuevo activo: {correction['record_code']}\n"
        f"  Peso nuevo: {correction['weight_kg']} {correction['unit'] or ''}\n"
        f"  Estado: ACTIVO\n\n"
        f"Por: {user['name']}\n"
        f"Hora: {ahora} - {fecha}\n"
        f"------------------------\n"
        f"Auditoria actualizada"
    )

    await update.message.reply_text(respuesta)
