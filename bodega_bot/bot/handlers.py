from telegram import Update
from telegram.ext import ContextTypes
from database.connection import get_user, add_user, remove_user
import os

SUPERADMIN_ID = int(os.getenv("SUPERADMIN_ID", "216920595"))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        return
    await update.message.reply_text(
        f"Bienvenido {user['name']}\n"
        f"Bot Bodega Pepe Pez activo.\n\n"
        f"Envia foto + descripcion para registrar.\n"
        f"Ejemplos:\n"
        f"  Ingresa pollo Pronaca 45kg\n"
        f"  Despacho aceite Mall del Sol 12lt\n"
        f"  Inventario camaron 25kg"
    )

async def add_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != SUPERADMIN_ID:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /adduser ID nombre [rol]")
        return
    telegram_id = int(args[0])
    name = args[1]
    role = args[2] if len(args) > 2 else 'staff'
    add_user(telegram_id, name, role)
    await update.message.reply_text(f"Usuario {name} agregado con rol {role}")

async def remove_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != SUPERADMIN_ID:
        return
    args = context.args
    if not args:
        await update.message.reply_text("Uso: /removeuser ID")
        return
    telegram_id = int(args[0])
    success = remove_user(telegram_id)
    if success:
        await update.message.reply_text(f"Usuario {telegram_id} eliminado.")
    else:
        await update.message.reply_text(f"Usuario {telegram_id} no encontrado.")

async def foto_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        return
    if not context.args:
        await update.message.reply_text("Uso: /foto ING-0001")
        return
    code = context.args[0].upper()
    from services.bodega_service import get_record_by_code
    record = get_record_by_code(code)
    if not record:
        await update.message.reply_text(f"No encontre el registro {code}")
        return
    if not record['file_id']:
        await update.message.reply_text(f"El registro {code} no tiene foto.")
        return
    await update.message.reply_photo(
        photo=record['file_id'],
        caption=(
            f"Codigo: {record['record_code']}\n"
            f"Tipo: {record['record_type'].upper()}\n"
            f"Producto: {record['product']}\n"
            f"Peso: {record['weight_kg']} {record['unit'] or ''}\n"
            f"Proveedor: {record['supplier_name'] or '-'}\n"
            f"Destino: {record['location_name'] or '-'}\n"
            f"Fecha: {record['created_at'].strftime('%d/%m/%Y %H:%M')}"
        )
    )
