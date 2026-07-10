from telegram import Update
from telegram.ext import ContextTypes
from database.connection import get_user, get_connection

async def send_foto(update, code):
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM records WHERE record_code = %s", (code,))
            record = cur.fetchone()
    if not record:
        await update.message.reply_text(f"No encontre: {code}")
        return False
    if not record['file_id']:
        await update.message.reply_text(f"Sin foto: {code}")
        return False
    await update.message.reply_photo(
        photo=record['file_id'],
        caption=(
            f"Codigo: {record['record_code']}\n"
            f"Tipo: {record['record_type'].upper()}\n"
            f"Descripcion: {record['product']}\n"
            f"Peso: {record['weight_kg']} {record['unit'] or ''}\n"
            f"Fecha: {record['created_at'].strftime('%d/%m/%Y %H:%M')}"
        )
    )
    return True

async def handle_foto(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        return
    if not context.args:
        await update.message.reply_text("Uso: /foto POR-0001")
        return
    await send_foto(update, context.args[0].upper())

async def handle_fotos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = get_user(update.effective_user.id)
    if not user:
        return
    if not context.args:
        await update.message.reply_text("Uso: /fotos POR-0001 POR-0002 MRM-0003")
        return
    total = len(context.args)
    await update.message.reply_text(f"Buscando {total} registros...")
    encontrados = 0
    no_encontrados = []
    for code in context.args:
        resultado = await send_foto(update, code.upper())
        if resultado:
            encontrados += 1
        else:
            no_encontrados.append(code.upper())
    resumen = f"Completado: {encontrados}/{total} fotos enviadas."
    if no_encontrados:
        resumen += f"\nNo encontrados: {', '.join(no_encontrados)}"
    await update.message.reply_text(resumen)
