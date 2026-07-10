import os
import sys
sys.path.insert(0, '/home/presidencia/bodega_bot')

from dotenv import load_dotenv
load_dotenv()

from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from bot.handlers import start, add_user_cmd, remove_user_cmd, foto_cmd
from bot.photo_handler import handle_photo
from bot.photo_handler import handle_callback as legacy_callback
from bot.correction_handler import handle_correction
from bot.reception_handler import (
    handle_reception_text,
    handle_reception_callback,
    pendientes_command,
)

async def handle_text_router(update, context):
    text = update.message.text or ''
    if 'corregir' in text.lower():
        await handle_correction(update, context)
        return
    user_data = context.user_data
    if user_data.get('reception_state'):
        await handle_reception_text(update, context)
    else:
        from bot.photo_handler import handle_text
        await handle_text(update, context)

async def handle_callback_router(update, context):
    query = update.callback_query
    data = query.data
    if data.startswith(('reg_', 'supp_', 'lot_', 'unit_', 'rcp_', 'item_')):
        await handle_reception_callback(update, context)
    else:
        await legacy_callback(update, context)

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("adduser", add_user_cmd))
    app.add_handler(CommandHandler("removeuser", remove_user_cmd))
    app.add_handler(CommandHandler("foto", foto_cmd))
    app.add_handler(CommandHandler("pendientes", pendientes_command))

    app.add_handler(MessageHandler(
        filters.PHOTO & (filters.ChatType.GROUPS | filters.ChatType.PRIVATE),
        handle_photo
    ))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUPS | filters.ChatType.PRIVATE),
        handle_text_router
    ))

    app.add_handler(CallbackQueryHandler(handle_callback_router))

    print("Bot Bodega Pepe Pez iniciado...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
