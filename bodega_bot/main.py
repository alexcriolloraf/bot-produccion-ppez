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
from bot.photo_handler import handle_photo, handle_callback
from bot.correction_handler import handle_correction

async def handle_text_router(update, context):
    """Router — decide si es corrección o texto normal."""
    text = update.message.text or ''
    if 'corregir' in text.lower():
        await handle_correction(update, context)
    else:
        from bot.photo_handler import handle_text
        await handle_text(update, context)

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("adduser", add_user_cmd))
    app.add_handler(CommandHandler("removeuser", remove_user_cmd))
    app.add_handler(CommandHandler("foto", foto_cmd))

    app.add_handler(MessageHandler(
        filters.PHOTO & (filters.ChatType.GROUPS | filters.ChatType.PRIVATE),
        handle_photo
    ))

    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUPS | filters.ChatType.PRIVATE),
        handle_text_router
    ))

    app.add_handler(CallbackQueryHandler(handle_callback))

    print("Bot Bodega Pepe Pez iniciado...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
