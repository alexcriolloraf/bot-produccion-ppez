from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.connection import get_user, get_all_locations
from services.classifier import classify, extract_weight_from_text, extract_destino
from services.bodega_service import RECORD_CODES
from services.sheets_service import append_bodega_record
from services.bodega_service import save_bodega_record
from datetime import datetime
import pytz

ECUADOR_TZ = pytz.timezone("America/Guayaquil")

TIPO_NOMBRES = {
    'ingreso':      'INGRESO MP',
    'despacho':     'DESPACHO',
    'devolucion':   'DEVOLUCION',
    'inventario':   'INVENTARIO',
    'novedad':      'NOVEDAD',
    'mantenimiento':'MANTENIMIENTO',
    'apertura':     'APERTURA',
    'cierre':       'CIERRE',
    'requerimiento':'REQUERIMIENTO',
}

def build_response(tipo, caption, user, record):
    nombre_tipo = TIPO_NOMBRES.get(tipo, tipo.upper())
    now = datetime.now(ECUADOR_TZ)
    ahora = now.strftime('%H:%M')
    fecha = now.strftime('%d/%m/%Y')

    respuesta = (
        f"REGISTRADO: {nombre_tipo}\n"
        f"------------------------\n"
        f"{caption.strip()}\n"
    )
    if record.get('weight_kg'):
        respuesta += f"Peso: {record['weight_kg']} {record['unit'] or ''}\n"
    if record.get('supplier_name'):
        respuesta += f"Proveedor: {record['supplier_name']}\n"
    if record.get('location_name'):
        respuesta += f"Destino: {record['location_name']}\n"
    respuesta += (
        f"Colaborador: {user['name']}\n"
        f"Hora: {ahora}\n"
        f"Fecha: {fecha}\n"
        f"Codigo: {record['record_code']}\n"
        f"------------------------\n"
        f"Guardado en bitacora"
    )
    return respuesta

def get_location_keyboard():
    locations = get_all_locations()
    keyboard = []
    row = []
    for i, loc in enumerate(locations):
        row.append(InlineKeyboardButton(
            loc['name'],
            callback_data=f"loc_{loc['code']}_{loc['name']}"
        ))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row:
        keyboard.append(row)
    return InlineKeyboardMarkup(keyboard)

async def handle_photo(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        return

    caption = update.message.caption
    file_id = update.message.photo[-1].file_id

    from bot.reception_handler import start_reception
    await start_reception(update, context, file_id, caption)

async def handle_photo_legacy(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
            "Ejemplo: Ingresa pollo Pronaca 45kg\n"
            "Ejemplo: Despacho aceite Mall del Sol 12lt"
        )
        return

    resultado = classify(caption)
    tipo = resultado['tipo']

    if not tipo or resultado['confianza'] == 'baja':
        context.user_data['pending_file_id'] = file_id
        context.user_data['pending_caption'] = caption
        keyboard = [
            [
                InlineKeyboardButton("Ingreso MP", callback_data="tipo_ingreso"),
                InlineKeyboardButton("Despacho", callback_data="tipo_despacho"),
            ],
            [
                InlineKeyboardButton("Devolucion", callback_data="tipo_devolucion"),
                InlineKeyboardButton("Inventario", callback_data="tipo_inventario"),
            ],
            [
                InlineKeyboardButton("Novedad", callback_data="tipo_novedad"),
                InlineKeyboardButton("Mantenimiento", callback_data="tipo_mantenimiento"),
            ],
            [
                InlineKeyboardButton("Apertura", callback_data="tipo_apertura"),
                InlineKeyboardButton("Cierre", callback_data="tipo_cierre"),
            ],
        ]
        await update.message.reply_text(
            "No reconoci el tipo. Cual es?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    peso_info = extract_weight_from_text(caption)
    weight_kg = peso_info['valor'] if peso_info else None
    unit = peso_info['unidad'] if peso_info else None

    # Si requiere peso y no lo tiene
    if resultado['requiere_peso'] and not weight_kg:
        context.user_data['pending_file_id'] = file_id
        context.user_data['pending_caption'] = caption
        context.user_data['pending_tipo'] = tipo
        await update.message.reply_text(
            "Cual es el peso o cantidad?\n"
            "Ejemplo: 45kg / 12lt / 100und"
        )
        return

    # Si es despacho y no tiene destino
    if resultado['requiere_destino'] and not resultado['destino']:
        context.user_data['pending_file_id'] = file_id
        context.user_data['pending_caption'] = caption
        context.user_data['pending_tipo'] = tipo
        context.user_data['pending_weight'] = weight_kg
        context.user_data['pending_unit'] = unit
        await update.message.reply_text(
            "A que local va el despacho?",
            reply_markup=get_location_keyboard()
        )
        return

    # Si es ingreso y no tiene proveedor
    if resultado['requiere_proveedor'] and not resultado['proveedor']:
        context.user_data['pending_file_id'] = file_id
        context.user_data['pending_caption'] = caption
        context.user_data['pending_tipo'] = tipo
        context.user_data['pending_weight'] = weight_kg
        context.user_data['pending_unit'] = unit
        await update.message.reply_text(
            "Cual es el proveedor?\n"
            "Escribe el nombre del proveedor."
        )
        return

    # Registrar
    record = save_bodega_record(
        telegram_user_id=user_id,
        record_type=tipo,
        product=caption.strip(),
        weight_kg=weight_kg,
        unit=unit,
        supplier_name=resultado.get('proveedor'),
        location_name=resultado.get('destino'),
        file_id=file_id,
        notes=caption
    )

    append_bodega_record(record, user['name'])
    respuesta = build_response(tipo, caption, user, record)
    await update.message.reply_text(respuesta)

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

    # Si estaba esperando peso
    peso_info = extract_weight_from_text(texto)
    if peso_info:
        context.user_data['pending_weight'] = peso_info['valor']
        context.user_data['pending_unit'] = peso_info['unidad']

        resultado = classify(pending_caption)

        # Si es despacho necesita destino
        if resultado['requiere_destino'] and not resultado['destino']:
            await update.message.reply_text(
                "A que local va el despacho?",
                reply_markup=get_location_keyboard()
            )
            return

        # Si es ingreso necesita proveedor
        if resultado['requiere_proveedor'] and not resultado['proveedor']:
            await update.message.reply_text("Cual es el proveedor?")
            return

        # Registrar
        record = save_bodega_record(
            telegram_user_id=user_id,
            record_type=pending_tipo,
            product=pending_caption.strip(),
            weight_kg=peso_info['valor'],
            unit=peso_info['unidad'],
            file_id=pending_file_id,
            notes=pending_caption
        )
        append_bodega_record(record, user['name'])
        respuesta = build_response(pending_tipo, pending_caption, user, record)
        await update.message.reply_text(respuesta)
        context.user_data.clear()
        return

    # Si estaba esperando proveedor
    if context.user_data.get('pending_weight') is not None:
        record = save_bodega_record(
            telegram_user_id=user_id,
            record_type=pending_tipo,
            product=pending_caption.strip(),
            weight_kg=context.user_data.get('pending_weight'),
            unit=context.user_data.get('pending_unit'),
            supplier_name=texto,
            file_id=pending_file_id,
            notes=pending_caption
        )
        append_bodega_record(record, user['name'])
        respuesta = build_response(pending_tipo, pending_caption, user, record)
        await update.message.reply_text(respuesta)
        context.user_data.clear()
        return

    await update.message.reply_text(
        "No entendi. Escribe el peso o cantidad:\n"
        "Ejemplo: 45kg / 12lt / 100und"
    )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user_id = query.from_user.id
    user = get_user(user_id)
    if not user:
        return

    data = query.data

    # Selección de tipo
    if data.startswith("tipo_"):
        tipo = data.replace("tipo_", "")
        context.user_data['pending_tipo'] = tipo
        file_id = context.user_data.get('pending_file_id')
        caption = context.user_data.get('pending_caption', '')

        if not file_id:
            await query.edit_message_text("No encontre la foto. Enviala de nuevo.")
            return

        resultado = classify(caption)

        if tipo in ['despacho']:
            await query.edit_message_text(
                "A que local va el despacho?",
                reply_markup=get_location_keyboard()
            )
            return

        if tipo in ['ingreso']:
            await query.edit_message_text("Cual es el proveedor?")
            return

        record = save_bodega_record(
            telegram_user_id=user_id,
            record_type=tipo,
            product=caption.strip(),
            file_id=file_id,
            notes=caption
        )
        respuesta = build_response(tipo, caption, user, record)
        await query.edit_message_text(respuesta)
        context.user_data.clear()
        return

    # Selección de local
    if data.startswith("loc_"):
        parts = data.split("_", 2)
        loc_code = parts[1]
        loc_name = parts[2]

        pending_tipo = context.user_data.get('pending_tipo', 'despacho')
        pending_file_id = context.user_data.get('pending_file_id')
        pending_caption = context.user_data.get('pending_caption', '')
        weight_kg = context.user_data.get('pending_weight')
        unit = context.user_data.get('pending_unit')

        record = save_bodega_record(
            telegram_user_id=user_id,
            record_type=pending_tipo,
            product=pending_caption.strip(),
            weight_kg=weight_kg,
            unit=unit,
            location_name=loc_name,
            file_id=pending_file_id,
            notes=pending_caption
        )
        respuesta = build_response(pending_tipo, pending_caption, user, record)
        await query.edit_message_text(respuesta)
        context.user_data.clear()
