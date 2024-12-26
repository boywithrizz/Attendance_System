import logging
from telegram import Update, Bot, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackContext, MessageHandler, filters
from pymongo import MongoClient
from config import BOT_TOKEN, MONGO_URI
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

# Set up logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

# Set up MongoDB client
client = MongoClient(MONGO_URI)
db = client['attendance_bot']
attendance_collection = db['attendance']

# Define the custom keyboard
def get_main_menu_keyboard():
    keyboard = [
        ['/mark_attendance', '/check_leaves'],
        ['/attendance_summary']
    ]
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        'Welcome to the Attendance Bot!',
        reply_markup=get_main_menu_keyboard()
    )

async def mark_attendance(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    date = datetime.now().strftime('%Y-%m-%d')
    attendance_collection.update_one(
        {'user_id': user_id, 'date': date},
        {'$set': {'attended': True}},
        upsert=True
    )
    await update.message.reply_text('Attendance marked for today!')

async def check_leaves(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    total_days = attendance_collection.count_documents({'user_id': user_id})
    attended_days = attendance_collection.count_documents({'user_id': user_id, 'attended': True})
    remaining_leaves = int(total_days * 0.25) - (total_days - attended_days)
    await update.message.reply_text(f'You can take {remaining_leaves} more leaves before the next exam.')

async def attendance_summary(update: Update, context: CallbackContext) -> None:
    user_id = update.message.from_user.id
    total_days = attendance_collection.count_documents({'user_id': user_id})
    attended_days = attendance_collection.count_documents({'user_id': user_id, 'attended': True})
    await update.message.reply_text(f'You have attended {attended_days} out of {total_days} days.')

async def send_daily_reminder(context: CallbackContext) -> None:
    chat_id = context.job.context
    await context.bot.send_message(chat_id=chat_id, text="Don't forget to mark your attendance today!")

def main() -> None:
    # Create the Bot and Application
    bot = Bot(token=BOT_TOKEN)
    application = Application.builder().token(BOT_TOKEN).build()
    
    # Register command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^/mark_attendance$'), mark_attendance))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^/check_leaves$'), check_leaves))
    application.add_handler(MessageHandler(filters.TEXT & filters.Regex('^/attendance_summary$'), attendance_summary))

    # Set up the scheduler
    scheduler = BackgroundScheduler()
    scheduler.add_job(send_daily_reminder, 'cron', hour=9, args=[application.bot])
    scheduler.start()

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main()