from telegram import Update
from telegram.ext import ContextTypes
from helpers.locale import get_text

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_text("start"))

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(get_text("help"))
