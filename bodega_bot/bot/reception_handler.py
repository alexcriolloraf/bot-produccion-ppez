from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from database.connection import get_user
from database.supplier_repo import (
    search_suppliers, get_supplier_by_name, get_supplier_by_code,
    get_supplier_by_id, create_supplier, fuzzy_search_suppliers
)
from database.product_repo import get_or_create_product
from database.reception_repo import (
    create_reception, add_reception_items, get_open_receptions,
    get_reception_by_id, get_pending_items, get_weighed_items,
    get_item_by_id, weigh_item, check_all_items_weighed,
    close_reception, get_reception_summary
)
from services.lot_service import generate_reception_lot_code
from services.classifier import extract_weight_from_text
from datetime import datetime
import pytz
import re

ECUADOR_TZ = pytz.timezone("America/Guayaquil")

ST_SUPPLIER_NAME = 'WAITING_SUPPLIER_NAME'
ST_CONFIRM_REGISTER = 'WAITING_CONFIRM_REGISTER'
ST_CORRECT_NAME = 'WAITING_CORRECT_NAME'
ST_PRODUCTS = 'WAITING_PRODUCTS'
ST_HAS_LOT = 'WAITING_HAS_LOT'
ST_LOTS = 'WAITING_LOTS'
ST_WEIGHT_UNIT = 'WAITING_WEIGHT_UNIT'
ST_SELECT_RECEPTION = 'WAITING_SELECT_RECEPTION'
ST_SELECT_PRODUCT = 'WAITING_SELECT_PRODUCT'

async def start_reception(update: Update, context: ContextTypes.DEFAULT_TYPE, file_id: str, caption: str = None):
    user = get_user(update.effective_user.id)
    if not user:
        return

    context.user_data['reception_file_id'] = file_id
    context.user_data['reception_state'] = None
    context.user_data['reception_supplier'] = None

    if caption and caption.strip():
        suppliers = fuzzy_search_suppliers(caption.strip())
        if suppliers:
            if len(suppliers) == 1:
                context.user_data['reception_supplier'] = dict(suppliers[0])
                context.user_data['reception_state'] = ST_PRODUCTS
                await update.message.reply_text(
                    f"Proveedor encontrado: {suppliers[0]['name']} ({suppliers[0]['code']})\n\n"
                    "Que productos va a entregar? (separados por coma)\n"
                    "Ej: camaron, aguacate, pollo"
                )
            else:
                keyboard = []
                row = []
                for i, s in enumerate(suppliers):
                    label = f"{s['name']} ({s['code']})"
                    row.append(InlineKeyboardButton(label[:40], callback_data=f"supp_{s['id']}"))
                    if len(row) == 1:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                keyboard.append([InlineKeyboardButton("Ninguno, es nuevo", callback_data="supp_none")])
                context.user_data['reception_search_text'] = caption.strip()
                context.user_data['reception_state'] = ST_CONFIRM_REGISTER
                await update.message.reply_text(
                    "Seleccione el proveedor:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            context.user_data['reception_search_text'] = caption.strip()
            context.user_data['reception_state'] = ST_CONFIRM_REGISTER
            keyboard = [
                [InlineKeyboardButton("Si, registrar", callback_data="reg_yes")],
                [InlineKeyboardButton("No, corregir nombre", callback_data="reg_no")]
            ]
            await update.message.reply_text(
                f"'{caption.strip()}' no esta registrado. Desea registrarlo?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
    else:
        context.user_data['reception_state'] = ST_SUPPLIER_NAME
        await update.message.reply_text(
            "Cual es el nombre del proveedor?"
        )

async def handle_reception_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        return

    state = context.user_data.get('reception_state')
    if not state:
        peso_info = extract_weight_from_text(update.message.text)
        if peso_info:
            await handle_weight_flow(update, context, peso_info)
        return

    text = update.message.text.strip()

    if state == ST_SUPPLIER_NAME:
        suppliers = fuzzy_search_suppliers(text)
        if suppliers:
            if len(suppliers) == 1:
                context.user_data['reception_supplier'] = dict(suppliers[0])
                context.user_data['reception_state'] = ST_PRODUCTS
                await update.message.reply_text(
                    f"Proveedor encontrado: {suppliers[0]['name']} ({suppliers[0]['code']})\n\n"
                    "Que productos va a entregar? (separados por coma)\n"
                    "Ej: camaron, aguacate, pollo"
                )
            else:
                keyboard = []
                row = []
                for s in suppliers:
                    row.append(InlineKeyboardButton(f"{s['name']} ({s['code']})"[:40], callback_data=f"supp_{s['id']}"))
                    if len(row) == 1:
                        keyboard.append(row)
                        row = []
                if row:
                    keyboard.append(row)
                keyboard.append([InlineKeyboardButton("Ninguno, es nuevo", callback_data="supp_none")])
                context.user_data['reception_search_text'] = text
                context.user_data['reception_state'] = ST_CONFIRM_REGISTER
                await update.message.reply_text(
                    "Seleccione el proveedor:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            context.user_data['reception_search_text'] = text
            context.user_data['reception_state'] = ST_CONFIRM_REGISTER
            keyboard = [
                [InlineKeyboardButton("Si, registrar", callback_data="reg_yes")],
                [InlineKeyboardButton("No, corregir nombre", callback_data="reg_no")]
            ]
            await update.message.reply_text(
                f"'{text}' no esta registrado. Desea registrarlo?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    if state == ST_CORRECT_NAME:
        suppliers = fuzzy_search_suppliers(text)
        if suppliers:
            if len(suppliers) == 1:
                context.user_data['reception_supplier'] = dict(suppliers[0])
                context.user_data['reception_state'] = ST_PRODUCTS
                await update.message.reply_text(
                    f"Proveedor encontrado: {suppliers[0]['name']} ({suppliers[0]['code']})\n\n"
                    "Que productos va a entregar? (separados por coma)\n"
                    "Ej: camaron, aguacate, pollo"
                )
            else:
                keyboard = []
                for s in suppliers:
                    keyboard.append([InlineKeyboardButton(f"{s['name']} ({s['code']})"[:40], callback_data=f"supp_{s['id']}")])
                keyboard.append([InlineKeyboardButton("Ninguno, es nuevo", callback_data="supp_none")])
                context.user_data['reception_search_text'] = text
                context.user_data['reception_state'] = ST_CONFIRM_REGISTER
                await update.message.reply_text(
                    "Seleccione el proveedor:",
                    reply_markup=InlineKeyboardMarkup(keyboard)
                )
        else:
            context.user_data['reception_search_text'] = text
            context.user_data['reception_state'] = ST_CONFIRM_REGISTER
            keyboard = [
                [InlineKeyboardButton("Si, registrar", callback_data="reg_yes")],
                [InlineKeyboardButton("No, corregir nombre", callback_data="reg_no")]
            ]
            await update.message.reply_text(
                f"'{text}' no esta registrado. Desea registrarlo?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return

    if state == ST_PRODUCTS:
        products = [p.strip() for p in text.split(',') if p.strip()]
        if not products:
            await update.message.reply_text("Debe escribir al menos un producto. Ej: camaron, aguacate, pollo")
            return
        context.user_data['reception_products'] = products
        context.user_data['reception_state'] = ST_HAS_LOT
        keyboard = [
            [InlineKeyboardButton("Si", callback_data="lot_yes")],
            [InlineKeyboardButton("No", callback_data="lot_no")]
        ]
        await update.message.reply_text(
            "Algun producto tiene lote propio?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if state == ST_LOTS:
        parts = [p.strip() for p in text.split(',')]
        products = context.user_data.get('reception_products', [])
        if len(parts) != len(products):
            await update.message.reply_text(
                f"Debe ingresar {len(products)} valores (uno por producto). "
                "Use N/A si no tiene lote. Ej: LOTE-001, N/A, LOTE-003"
            )
            return
        lots = []
        for i, product in enumerate(products):
            product_data = get_or_create_product(product)
            prefix = product_data['prefix'] if product_data and product_data.get('prefix') else product[:3].upper()
            supplier_lot = parts[i] if parts[i].upper() != 'N/A' and parts[i] != '' else None
            lot_code = generate_reception_lot_code(prefix)
            lots.append({
                'product_name': product_data['name'] if product_data else product,
                'product_prefix': prefix if product_data and product_data.get('prefix') else None,
                'lot_code': lot_code,
                'supplier_lot': supplier_lot,
            })
        context.user_data['reception_lots'] = lots
        await finalize_reception(update, context)
        return

    peso_info = extract_weight_from_text(text)
    if peso_info:
        await handle_weight_flow(update, context, peso_info)

async def handle_reception_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    user = get_user(query.from_user.id)
    if not user:
        return

    data = query.data

    if data == 'reg_yes':
        search_text = context.user_data.get('reception_search_text', '')
        if not search_text:
            await query.edit_message_text("Error: no hay texto para registrar. Envie la foto de nuevo.")
            context.user_data.clear()
            return
        supplier = create_supplier(search_text, query.from_user.id)
        context.user_data['reception_supplier'] = dict(supplier)
        context.user_data['reception_state'] = ST_PRODUCTS
        await query.edit_message_text(
            f"Nuevo proveedor registrado: {supplier['name']} ({supplier['code']})\n\n"
            "Que productos va a entregar? (separados por coma)\n"
            "Ej: camaron, aguacate, pollo"
        )
        return

    if data == 'reg_no':
        context.user_data['reception_state'] = ST_CORRECT_NAME
        await query.edit_message_text("Escriba el nombre correcto del proveedor:")
        return

    if data.startswith('supp_'):
        supplier_id = int(data.split('_')[1])
        supplier = get_supplier_by_id(supplier_id)
        if supplier:
            context.user_data['reception_supplier'] = dict(supplier)
            context.user_data['reception_state'] = ST_PRODUCTS
            await query.edit_message_text(
                f"Proveedor seleccionado: {supplier['name']} ({supplier['code']})\n\n"
                "Que productos va a entregar? (separados por coma)\n"
                "Ej: camaron, aguacate, pollo"
            )
        else:
            await query.edit_message_text("Error: proveedor no encontrado.")
            context.user_data.clear()
        return

    if data == 'supp_none':
        search_text = context.user_data.get('reception_search_text', '')
        if not search_text:
            context.user_data['reception_state'] = ST_SUPPLIER_NAME
            await query.edit_message_text("Cual es el nombre del proveedor?")
            return
        context.user_data['reception_state'] = ST_CONFIRM_REGISTER
        keyboard = [
            [InlineKeyboardButton("Si, registrar", callback_data="reg_yes")],
            [InlineKeyboardButton("No, corregir nombre", callback_data="reg_no")]
        ]
        await query.edit_message_text(
            f"'{search_text}' no esta registrado. Desea registrarlo?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    if data == 'lot_yes':
        products = context.user_data.get('reception_products', [])
        context.user_data['reception_state'] = ST_LOTS
        await query.edit_message_text(
            f"Ingrese los lotes en el MISMO ORDEN, separados por coma.\n"
            f"Si un producto NO tiene lote, escriba N/A.\n\n"
            f"Productos ({len(products)}):\n" +
            "\n".join(f"{i+1}. {p}" for i, p in enumerate(products)) +
            "\n\nEj: LOTE-001, N/A, LOTE-003"
        )
        return

    if data == 'lot_no':
        products = context.user_data.get('reception_products', [])
        lots = []
        for product in products:
            product_data = get_or_create_product(product)
            prefix = product_data['prefix'] if product_data and product_data.get('prefix') else product[:3].upper()
            lot_code = generate_reception_lot_code(prefix)
            lots.append({
                'product_name': product_data['name'] if product_data else product,
                'product_prefix': prefix if product_data and product_data.get('prefix') else None,
                'lot_code': lot_code,
                'supplier_lot': None,
            })
        context.user_data['reception_lots'] = lots
        await finalize_reception(update, context)
        return

    if data.startswith('unit_'):
        unit = data.split('_')[1]
        pending_weight = context.user_data.get('pending_weight_value')
        if pending_weight is not None:
            await process_weight_with_unit(update, context, pending_weight, unit)
        return

    if data.startswith('rcp_'):
        reception_id = int(data.split('_')[1])
        context.user_data['weight_reception_id'] = reception_id
        pending_weight = context.user_data.get('pending_weight_value')
        pending_unit = context.user_data.get('pending_weight_unit')
        await process_weight_for_reception(update, context, reception_id, pending_weight, pending_unit)
        return

    if data.startswith('item_'):
        item_id = int(data.split('_')[1])
        pending_weight = context.user_data.get('pending_weight_value')
        pending_unit = context.user_data.get('pending_weight_unit')
        await process_weight_for_item(update, context, item_id, pending_weight, pending_unit)

async def handle_weight_flow(update: Update, context: ContextTypes.DEFAULT_TYPE, peso_info: dict):
    user = get_user(update.effective_user.id)
    if not user:
        return

    weight = peso_info['valor']
    unit = peso_info.get('unidad')

    if not unit:
        context.user_data['pending_weight_value'] = weight
        context.user_data['pending_weight_unit'] = None
        context.user_data['reception_state'] = ST_WEIGHT_UNIT
        keyboard = [
            [
                InlineKeyboardButton("kg", callback_data="unit_kg"),
                InlineKeyboardButton("lb", callback_data="unit_lb"),
                InlineKeyboardButton("und", callback_data="unit_und"),
            ]
        ]
        await update.message.reply_text(
            f"{weight} es en kg, lb o und?",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    context.user_data['pending_weight_value'] = weight
    context.user_data['pending_weight_unit'] = unit
    await process_weight_after_unit(update, context, weight, unit)

async def process_weight_with_unit(update: Update, context: ContextTypes.DEFAULT_TYPE, weight: float, unit: str):
    context.user_data['pending_weight_value'] = weight
    context.user_data['pending_weight_unit'] = unit
    await process_weight_after_unit(update, context, weight, unit)

async def process_weight_after_unit(update: Update, context: ContextTypes.DEFAULT_TYPE, weight: float, unit: str):
    receipts = get_open_receptions()
    if not receipts:
        await update.message.reply_text("No hay recepciones pendientes de peso.")
        context.user_data.clear()
        return

    if len(receipts) == 1:
        context.user_data['weight_reception_id'] = receipts[0]['id']
        await process_weight_for_reception(update, context, receipts[0]['id'], weight, unit)
    else:
        keyboard = []
        row = []
        for i, r in enumerate(receipts):
            label = f"{r['supplier_name']} ({r['reception_code']})"
            row.append(InlineKeyboardButton(label[:40], callback_data=f"rcp_{r['id']}"))
            if len(row) == 1:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        context.user_data['pending_weight_value'] = weight
        context.user_data['pending_weight_unit'] = unit
        context.user_data['reception_state'] = ST_SELECT_RECEPTION
        await update.message.reply_text(
            "Seleccione la recepcion:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def process_weight_for_reception(update: Update, context: ContextTypes.DEFAULT_TYPE, reception_id: int, weight: float, unit: str):
    pending = get_pending_items(reception_id)
    if not pending:
        await update.message.reply_text("No hay items pendientes en esta recepcion.")
        context.user_data.clear()
        return

    if len(pending) == 1:
        await process_weight_for_item(update, context, pending[0]['id'], weight, unit)
    else:
        keyboard = []
        row = []
        for i, item in enumerate(pending):
            label = f"{item['product_name']} - Lote: {item['lot_code']}"
            if item.get('supplier_lot'):
                label += f" (prov: {item['supplier_lot']})"
            row.append(InlineKeyboardButton(label[:40], callback_data=f"item_{item['id']}"))
            if len(row) == 1:
                keyboard.append(row)
                row = []
        if row:
            keyboard.append(row)
        context.user_data['pending_weight_value'] = weight
        context.user_data['pending_weight_unit'] = unit
        context.user_data['reception_state'] = ST_SELECT_PRODUCT
        await update.message.reply_text(
            "Seleccione el producto a etiquetar:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )

async def process_weight_for_item(update: Update, context: ContextTypes.DEFAULT_TYPE, item_id: int, weight: float, unit: str):
    user = get_user(update.effective_user.id)
    if not user:
        return

    item = get_item_by_id(item_id)
    if not item:
        await update.message.reply_text("Error: item no encontrado.")
        context.user_data.clear()
        return

    if item['status'] != 'pendiente':
        await update.message.reply_text(f"El producto {item['product_name']} ya fue pesado.")
        context.user_data.clear()
        return

    weighed = weigh_item(item_id, weight, unit, update.effective_user.id)
    if not weighed:
        await update.message.reply_text("Error al registrar el peso.")
        context.user_data.clear()
        return

    reception_id = item['reception_id']
    reception = get_reception_by_id(reception_id)
    supplier_name = reception['supplier_name'] if reception else '?'

    lot_info = f"Lote: {weighed['lot_code']}"
    if weighed.get('supplier_lot'):
        lot_info += f" (proveedor: {weighed['supplier_lot']})"

    await update.message.reply_text(
        f"Producto pesado: {weighed['product_name']}\n"
        f"Peso: {weight} {unit}\n"
        f"{lot_info}\n"
        f"Pesado por: {user['name']}"
    )

    all_done = check_all_items_weighed(reception_id)
    if all_done:
        closed = close_reception(reception_id)
        if closed:
            weighed_items = get_weighed_items(reception_id)
            summary_lines = []
            for wi in weighed_items:
                lot_line = f"Lote: {wi['lot_code']}"
                if wi.get('supplier_lot'):
                    lot_line += f" (prov: {wi['supplier_lot']})"
                summary_lines.append(f"  {wi['product_name']} — {wi['weight_kg']} {wi['unit']} — {lot_line}")

            await update.message.reply_text(
                f"RECEPCION COMPLETADA — {closed['reception_code']}\n"
                f"Proveedor: {supplier_name}\n"
                f"-----------------------------\n" +
                "\n".join(summary_lines) +
                f"\n-----------------------------\n"
                f"Todos los productos pesados"
            )
    else:
        remaining = get_pending_items(reception_id)
        remaining_list = "\n".join(f"  {r['product_name']} — Lote: {r['lot_code']}" for r in remaining)
        await update.message.reply_text(
            f"Quedan pendientes:\n{remaining_list}"
        )

    context.user_data.clear()

async def finalize_reception(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        return

    supplier = context.user_data.get('reception_supplier')
    file_id = context.user_data.get('reception_file_id')
    lots = context.user_data.get('reception_lots', [])

    if not supplier or not lots:
        if hasattr(update, 'message') and update.message:
            await update.message.reply_text("Error: datos incompletos. Envie la foto de nuevo.")
        else:
            query = update.callback_query
            if query:
                await query.edit_message_text("Error: datos incompletos. Envie la foto de nuevo.")
        context.user_data.clear()
        return

    reception = create_reception(
        supplier_id=supplier['id'],
        supplier_name=supplier['name'],
        file_id=file_id,
        created_by=user_id
    )

    items = add_reception_items(reception['id'], lots)

    product_lines = []
    for item in items:
        lot_line = f"Lote proveedor: {item['supplier_lot']}" if item.get('supplier_lot') else f"Lote sistema: {item['lot_code']}"
        product_lines.append(f"  {item['product_name']}\n      {lot_line}")

    now = datetime.now(ECUADOR_TZ)
    hora = now.strftime('%H:%M')
    fecha = now.strftime('%d/%m/%Y')

    message = (
        f"RECEPCION ABIERTA — {reception['reception_code']}\n"
        f"Proveedor: {supplier['name']} ({supplier['code']})\n"
        f"------------------------\n"
        f"Pendientes de peso:\n" +
        "\n".join(f"  {i+1}. {p['product_name']}" for i, p in enumerate(items)) +
        f"\n------------------------\n"
        f"Colaborador: {user['name']}\n"
        f"Hora: {hora} — {fecha}\n"
        f"Bodega: recepcion abierta para pesaje"
    )

    if hasattr(update, 'message') and update.message:
        await update.message.reply_text(message)
    else:
        query = update.callback_query
        if query:
            await query.edit_message_text(message)

    context.user_data.clear()

async def pendientes_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        return

    receipts = get_open_receptions()
    if not receipts:
        await update.message.reply_text("No hay recepciones abiertas.")
        return

    lines = []
    for r in receipts:
        lines.append(f"{r['reception_code']} — {r['supplier_name']} — {r['pending_count']}/{r['total_count']} pendientes")

    text = "RECEPCIONES ABIERTAS\n" + "\n".join(f"  {l}" for l in lines)
    await update.message.reply_text(text)
