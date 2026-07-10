from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.connection import get_user
from services.classifier import classify, RECORD_CODES, extract_weight_from_text, extract_proveedor
from services.record_service import generate_code, save_record, save_ticket
from services.sheets_service import append_record, append_ticket, init_headers
from datetime import datetime
import pytz
ECUADOR_TZ = pytz.timezone("America/Guayaquil")

# Inicializar headers del Sheet
init_headers()

TIPO_EMOJIS = {
    'ingreso_mp':      'PRD',
    'porcionado':      'POR',
    'coccion':         'COC',
    'apanado':         'APN',
    'merma':           'MRM',
    'devolucion':      'DEV',
    'despacho':        'DSP',
    'novedad_calidad': 'NOV',
    'apertura':        'APE',
    'cierre':          'CIE',
    'limpieza':        'LMP',
    'inventario':      'INV',
    'mantenimiento':   'MNT',
    'mp_utilizada':    'MPU',
}

TIPO_NOMBRES = {
    'ingreso_mp':      'INGRESO MP',
    'porcionado':      'PORCIONADO',
    'coccion':         'COCCION',
    'apanado':         'APANADO',
    'merma':           'MERMA',
    'devolucion':      'DEVOLUCION/BAJA',
    'despacho':        'DESPACHO',
    'novedad_calidad': 'NOVEDAD DE CALIDAD',
    'apertura':        'APERTURA',
    'cierre':          'CIERRE',
    'limpieza':        'LIMPIEZA',
    'inventario':      'INVENTARIO',
    'mantenimiento':   'MANTENIMIENTO',
    'mp_utilizada':    'MP UTILIZADA',
}

REQUIERE_PESO = [
    'ingreso_mp', 'porcionado', 'coccion', 'apanado',
    'merma', 'devolucion', 'despacho', 'mp_utilizada', 'inventario'
]

def build_response(tipo, caption, user, code, weight_kg, unit):
    nombre_tipo = TIPO_NOMBRES.get(tipo, tipo.upper())
    now = datetime.now(ECUADOR_TZ)
    ahora = now.strftime('%H:%M')
    fecha = now.strftime('%d/%m/%Y')
    respuesta = (
        f"REGISTRADO: {nombre_tipo}\n"
        f"------------------------\n"
        f"{caption.strip()}\n"
    )
    if weight_kg:
        respuesta += f"Peso: {weight_kg} {unit}\n"
    respuesta += (
        f"Colaborador: {user['name']}\n"
        f"Hora: {ahora}\n"
        f"Fecha: {fecha}\n"
        f"Codigo: {code}\n"
        f"------------------------\n"
        f"Guardado en bitacora"
    )
    return respuesta

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        return

    caption = update.message.caption
    file_id = update.message.photo[-1].file_id

    if not caption:
        context.user_data['pending_file_id'] = file_id
        await update.message.reply_text(
            "Foto recibida. Falta el texto.\n"
            "Escribe el producto y peso:\n"
            "Ejemplo: Camaron para porcionar 11.50lb"
        )
        return

    resultado = classify(caption)
    tipo = resultado['tipo']

    if not tipo or resultado['confianza'] == 'baja':
        context.user_data['pending_file_id'] = file_id
        context.user_data['pending_caption'] = caption
        keyboard = [
            [
                InlineKeyboardButton("Ingreso MP", callback_data="tipo_ingreso_mp"),
                InlineKeyboardButton("Merma", callback_data="tipo_merma"),
            ],
            [
                InlineKeyboardButton("Porcionado", callback_data="tipo_porcionado"),
                InlineKeyboardButton("Coccion", callback_data="tipo_coccion"),
            ],
            [
                InlineKeyboardButton("Apanado", callback_data="tipo_apanado"),
                InlineKeyboardButton("MP Utilizada", callback_data="tipo_mp_utilizada"),
            ],
            [
                InlineKeyboardButton("Despacho", callback_data="tipo_despacho"),
                InlineKeyboardButton("Novedad", callback_data="tipo_novedad_calidad"),
            ],
            [
                InlineKeyboardButton("Apertura", callback_data="tipo_apertura"),
                InlineKeyboardButton("Cierre", callback_data="tipo_cierre"),
            ],
            [
                InlineKeyboardButton("Devolucion", callback_data="tipo_devolucion"),
                InlineKeyboardButton("Limpieza", callback_data="tipo_limpieza"),
            ],
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(
            "No reconoci el tipo. Cual es?",
            reply_markup=reply_markup
        )
        return

    peso_info = extract_weight_from_text(caption)
    weight_kg = peso_info['valor'] if peso_info else None
    unit = peso_info['unidad'] if peso_info else None

    if tipo in REQUIERE_PESO and not weight_kg:
        context.user_data['pending_file_id'] = file_id
        context.user_data['pending_caption'] = caption
        context.user_data['pending_tipo'] = tipo
        await update.message.reply_text(
            "Cual es el peso?\n"
            "Ejemplo: 11.50lb o 15.389kg o 500gr"
        )
        return

    proveedor = resultado.get('proveedor') or extract_proveedor(caption.lower())
    code = generate_code(RECORD_CODES.get(tipo, 'REG'))

    record = save_record(
        telegram_user_id=user['telegram_id'],
        record_type=tipo,
        record_code=code,
        product=caption.strip(),
        weight_kg=weight_kg,
        unit=unit,
        supplier=proveedor,
        file_id=file_id,
        notes=caption
    )

    # Guardar en Google Sheets
    append_record(record, user['name'])

    respuesta = build_response(tipo, caption, user, code, weight_kg, unit)
    await update.message.reply_text(respuesta)

    if resultado['es_novedad']:
        ticket = save_ticket(
            record_id=record['id'],
            ticket_type='calidad',
            description=caption,
            reported_by=user_id,
            supplier=proveedor
        )
        append_ticket(ticket, user['name'])
        await update.message.reply_text(
            f"NOVEDAD REGISTRADA\n"
            f"Ticket: {ticket['ticket_code']}\n"
            f"Estado: ABIERTO\n"
            f"Administracion notificada"
        )

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        return

    pending_tipo = context.user_data.get('pending_tipo')
    pending_file_id = context.user_data.get('pending_file_id')
    pending_caption = context.user_data.get('pending_caption', '')

    if not pending_tipo or not pending_file_id:
        return

    texto = update.message.text.strip()
    peso_info = extract_weight_from_text(texto)

    if not peso_info:
        await update.message.reply_text(
            "No reconoci el peso.\n"
            "Ejemplo: 11.50lb o 15.389kg o 500gr"
        )
        return

    weight_kg = peso_info['valor']
    unit = peso_info['unidad']
    tipo = pending_tipo
    proveedor = extract_proveedor(pending_caption.lower())
    code = generate_code(RECORD_CODES.get(tipo, 'REG'))

    record = save_record(
        telegram_user_id=user['telegram_id'],
        record_type=tipo,
        record_code=code,
        product=pending_caption.strip(),
        weight_kg=weight_kg,
        unit=unit,
        supplier=proveedor,
        file_id=pending_file_id,
        notes=pending_caption
    )

    append_record(record, user['name'])
    respuesta = build_response(tipo, pending_caption, user, code, weight_kg, unit)
    await update.message.reply_text(respuesta)

    context.user_data.pop('pending_tipo', None)
    context.user_data.pop('pending_file_id', None)
    context.user_data.pop('pending_caption', None)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = get_user(user_id)
    if not user:
        return

    tipo = query.data.replace("tipo_", "")
    file_id = context.user_data.get('pending_file_id')
    caption = context.user_data.get('pending_caption', '')

    if not file_id:
        await query.edit_message_text("No encontre la foto. Enviala de nuevo.")
        return

    peso_info = extract_weight_from_text(caption)
    weight_kg = peso_info['valor'] if peso_info else None
    unit = peso_info['unidad'] if peso_info else None

    if tipo in REQUIERE_PESO and not weight_kg:
        context.user_data['pending_tipo'] = tipo
        await query.edit_message_text(
            "Cual es el peso?\n"
            "Ejemplo: 11.50lb o 15.389kg o 500gr"
        )
        return

    proveedor = extract_proveedor(caption.lower())
    code = generate_code(RECORD_CODES.get(tipo, 'REG'))

    record = save_record(
        telegram_user_id=user['telegram_id'],
        record_type=tipo,
        record_code=code,
        product=caption.strip(),
        weight_kg=weight_kg,
        unit=unit,
        supplier=proveedor,
        file_id=file_id,
        notes=caption
    )

    append_record(record, user['name'])
    respuesta = build_response(tipo, caption, user, code, weight_kg, unit)
    await query.edit_message_text(respuesta)

    context.user_data.pop('pending_file_id', None)
    context.user_data.pop('pending_caption', None)
    context.user_data.pop('pending_tipo', None)
