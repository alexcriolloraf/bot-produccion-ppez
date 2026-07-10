from telegram import Update
from telegram.ext import ContextTypes
from database.connection import get_user, add_user, remove_user, list_users

SUPERADMIN_ID = 216920595

async def check_access(update: Update) -> bool:
    user_id = update.effective_user.id
    user = get_user(user_id)
    if not user:
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await check_access(update):
        return
    user = get_user(update.effective_user.id)
    await update.message.reply_text(
        f"✅ Bienvenido {user['name']}\n"
        f"Rol: {user['role']}\n"
        f"Bot Pepe Pez activo."
    )

async def add_user_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != SUPERADMIN_ID:
        return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("Uso: /adduser ID nombre rol")
        return
    telegram_id = int(args[0])
    name = args[1]
    role = args[2] if len(args) > 2 else 'staff'
    add_user(telegram_id, name, role)
    await update.message.reply_text(f"✅ {name} agregado con rol {role}")

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
        await update.message.reply_text(f"✅ Usuario {telegram_id} eliminado.")
    else:
        await update.message.reply_text(f"⚠️ Usuario {telegram_id} no encontrado.")

async def list_users_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != SUPERADMIN_ID:
        return
    users = list_users()
    if not users:
        await update.message.reply_text("No hay usuarios registrados.")
        return
    text = "👥 USUARIOS AUTORIZADOS\n━━━━━━━━━━━━━━━━━━━\n"
    for u in users:
        text += f"• {u['name']} — {u['role']} — ID: {u['telegram_id']}\n"
    await update.message.reply_text(text)
