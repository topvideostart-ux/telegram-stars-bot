import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging

# Load environment variables
load_dotenv()
BOT_TOKEN = os.getenv('BOT_TOKEN')
ADMIN_ID = int(os.getenv('ADMIN_ID', 0))

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Start command handler"""
    await update.message.reply_text(
        'Welcome to Telegram Stars Bot!\n'
        'Use /buy to purchase tickets with stars\n'
        'Use /status to check lottery status'
    )

async def buy(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Buy command handler"""
    await update.message.reply_text('Coming soon - ticket purchase functionality')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Status command handler"""
    await update.message.reply_text('Lottery is active! Good luck!')

def main() -> None:
    """Start the bot"""
    # Create the Application
    application = Application.builder().token(BOT_TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('buy', buy))
    application.add_handler(CommandHandler('status', status))

    logger.info('Bot started successfully!')
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
