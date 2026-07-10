import os
import sys
sys.path.insert(0, '/home/presidencia/pepepez_bot')

from dotenv import load_dotenv
load_dotenv()

from telegram.ext import (
    ApplicationBuilder, CommandHandler,
    MessageHandler, CallbackQueryHandler, filters
)
from bot.handlers import start, add_user_cmd, remove_user_cmd, list_users_cmd
from bot.photo_handler import handle_photo, handle_text, handle_callback
from bot.foto_handler import handle_foto, handle_fotos
from bot.correction_handler import handle_correction

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    app = ApplicationBuilder().token(token).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("adduser", add_user_cmd))
    app.add_handler(CommandHandler("removeuser", remove_user_cmd))
    app.add_handler(CommandHandler("users", list_users_cmd))
    app.add_handler(CommandHandler("foto", handle_foto))
    app.add_handler(CommandHandler("fotos", handle_fotos))

    # Handler de correcciones — respuestas con palabra "corregir"
    app.add_handler(MessageHandler(
        filters.TEXT & filters.REPLY & ~filters.COMMAND,
        handle_correction
    ))

    # Handler de fotos
    app.add_handler(MessageHandler(
        filters.PHOTO & (filters.ChatType.GROUPS | filters.ChatType.PRIVATE),
        handle_photo
    ))

    # Handler de texto normal
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUPS | filters.ChatType.PRIVATE),
        handle_text
    ))

    app.add_handler(CallbackQueryHandler(handle_callback, pattern="^tipo_"))

    print("Bot Pepe Pez iniciado...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
