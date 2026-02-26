""""""  

import logging
import asyncio
import os
from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup,
    LabeledPrice, InputMediaPhoto
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, PreCheckoutQueryHandler, ContextTypes,
    ConversationHandler, filters
)
from config import BOT_TOKEN, ADMIN_IDS
from database import Database

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# ---- Состояния ConversationHandler ----
CHOOSE_PLAN, WAITING_WISH, WAITING_INVITE_CHECK = range(3)

# ---- Тарифные планы ----
PLANS = {
    "plan_300": {
        "stars": 300,
        "invites": 1,
        "title": "🌟 VIP – 300 звёзд",
        "description": "Ваше имя в книге рекордов Гиннесса",
        "payload": "plan_300"
    },
    "plan_500": {
        "stars": 500,
        "invites": 2,
        "title": "💎 PREMIUM – 500 звёзд",
        "description": "Ваше имя в книге рекордов Гиннесса. Именной подарочный сертификат",
        "payload": "plan_500"
    },
    "plan_1000": {
        "stars": 1000,
        "invites": 5,
        "title": "👑 PLATINUM – 1000 звёзд",
        "description": "Ваше имя в книге рекордов Гиннесса. Именной подарочный сертификат. Участие в розыгрыше билетов на FIFA World Cup 2026",
        "payload": "plan_1000"
    }
}


class BotHandlers:
    def __init__(self, db: Database):
        self.db = db

    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user = update.effective_user
        logger.info(f"User {user.id} ({user.username}) started the bot")
        
        args = context.args
        referrer_id = None
        if args and args[0].startswith("ref_"):
            referrer_id = int(args[0].split("ref_")[1])
            logger.info(f"New user {user.id} referred by {referrer_id}")

        self.db.add_user(user.id, user.username, referrer_id)

        text = (
            f"Привет, {user.first_name}! 🎉\n\n"
            "📢 Создаём подарок! Самое большое послание в Мире!:\n"
            "✨ Внеси своё имя в Книгу Рекордов Гиннесса! Оставь пожелание на самолёте Роналду!\n\n"
            "👇  Разыграем билет на FIFA World Cup 2026 :"
        )

        keyboard = []
        for plan_id, plan in PLANS.items():
            button_text = f"{plan['title']} – {plan['invites']} билет(а)"
            keyboard.append([
                InlineKeyboardButton(button_text, callback_data=f"buy_{plan_id}")
            ])

        keyboard.append([InlineKeyboardButton("🎟 Мои билеты", callback_data="my_tickets")])
        keyboard.append([InlineKeyboardButton("🔗 Пригласить друга", callback_data="invite_friend")])

        reply_markup = InlineKeyboardMarkup(keyboard)

        if update.message:
            # Отправка GIF-изображения
            try:
                    gif_path = os.path.join(os.path.dirname(__file__), 'images', 'welcome.gif')
                    with open(gif_path, 'rb') as gif:
                        await update.message.reply_animation(animation=gif, caption="")            except Exception as e:
                logger.error(f"Failed to send GIF: {e}")
            await update.message.reply_text(text, reply_markup=reply_markup)
        else:
            await update.callback_query.message.reply_text(text, reply_markup=reply_markup)

        return CHOOSE_PLAN

    async def buy_plan(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        plan_id = query.data.split("buy_")[1]
        context.user_data["selected_plan"] = plan_id
        plan = PLANS[plan_id]

        price = LabeledPrice(label=plan["title"], amount=plan["stars"])

        await context.bot.send_invoice(
            chat_id=query.from_user.id,
            title=plan["title"],
            description=plan["description"],
            payload=plan["payload"],
            provider_token="",
            currency="XTR",
            prices=[price]
        )

        return CHOOSE_PLAN

    async def precheckout_callback(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.pre_checkout_query
        await query.answer(ok=True)
        return CHOOSE_PLAN

    async def successful_payment(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        payload = update.message.successful_payment.payload

        plan = None
        for p_id, p_data in PLANS.items():
            if p_data["payload"] == payload:
                plan = p_data
                break

        if not plan:
            await update.message.reply_text("❌ Ошибка при обработке платежа.")
            return ConversationHandler.END

        num_tickets = plan["invites"]
        self.db.add_tickets(user_id, num_tickets)

        text = (
            f"✅ Оплата прошла успешно!\n"
            f"Вы получили {num_tickets} билет(а).\n\n"
            "Теперь напишите своё пожелание для Роналду 🙏"
        )
        await update.message.reply_text(text)

        return WAITING_WISH

    async def receive_wish(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        wish_text = update.message.text

        self.db.add_wish(user_id, wish_text)

        text = (
            "💌 Ваше пожелание принято!\n\n"
            "🎟 Хочешь больше билетов?\n"
            "👉 Пригласи друзей и получи бонус!"
        )

        keyboard = [
            [InlineKeyboardButton("🔗 Пригласить друга", callback_data="invite_friend")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await update.message.reply_text(text, reply_markup=reply_markup)
        return ConversationHandler.END

    async def my_tickets(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        tickets = self.db.get_user_tickets(user_id)
        invites = self.db.get_user_invites(user_id)

        text = (
            f"🎟 У вас {tickets} билет(ов)\n"
            f"👥 Приглашённых друзей: {invites}\n\n"
            "Пригласи больше друзей, чтобы получить дополнительные билеты!"
        )

        keyboard = [
            [InlineKeyboardButton("🔗 Пригласить друга", callback_data="invite_friend")],
            [InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup)
        return CHOOSE_PLAN

    async def invite_friend(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()

        user_id = query.from_user.id
        bot_username = (await context.bot.get_me()).username
        invite_link = f"https://t.me/{bot_username}?start=ref_{user_id}"

        text = (
            "🔗 Твоя реферальная ссылка:\n"
            f"{invite_link}\n\n"
            "Отправь её друзьям! За каждого друга, который купит тариф, "
            "ты получишь +1 билет! 🎫"
        )

        keyboard = [[InlineKeyboardButton("🏠 Главное меню", callback_data="main_menu")]]
        reply_markup = InlineKeyboardMarkup(keyboard)

        await query.edit_message_text(text, reply_markup=reply_markup)
        return CHOOSE_PLAN

    async def main_menu(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        query = update.callback_query
        await query.answer()
        context.user_data.clear()
        return await self.start(update, context)

    async def admin_stats(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ У вас нет прав доступа.")
            return

        stats = self.db.get_stats()
        text = (
            "📊 Статистика бота:\n\n"
            f"👥 Всего пользователей: {stats['total_users']}\n"
            f"🎟 Всего билетов выдано: {stats['total_tickets']}\n"
            f"💌 Всего пожеланий: {stats['total_wishes']}"
        )
        await update.message.reply_text(text)

    async def admin_draw(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_id = update.effective_user.id
        if user_id not in ADMIN_IDS:
            await update.message.reply_text("❌ У вас нет прав доступа.")
            return

        winner_id = self.db.draw_winner()
        if not winner_id:
            await update.message.reply_text("❌ Нет участников для розыгрыша.")
            return

        winner_info = self.db.get_user_info(winner_id)
        text = (
            f"🎉 Победитель розыгрыша:\n"
            f"ID: {winner_id}\n"
            f"Username: @{winner_info['username'] if winner_info['username'] else 'N/A'}\n"
            f"Билетов: {winner_info['tickets']}"
        )
        await update.message.reply_text(text)

        try:
            await context.bot.send_message(
                chat_id=winner_id,
                text="🎉 Поздравляем! Вы выиграли в розыгрыше! Администратор свяжется с вами."
            )
        except Exception as e:
            logger.error(f"Failed to notify winner {winner_id}: {e}")

    async def cancel(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        await update.message.reply_text("❌ Действие отменено.")
        context.user_data.clear()
        return ConversationHandler.END


def main():
    db = Database("bot_data.db")
    handlers = BotHandlers(db)

    application = Application.builder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", handlers.start)],
        states={
            CHOOSE_PLAN: [
                CallbackQueryHandler(handlers.buy_plan, pattern="^buy_"),
                CallbackQueryHandler(handlers.my_tickets, pattern="^my_tickets$"),
                CallbackQueryHandler(handlers.invite_friend, pattern="^invite_friend$"),
                CallbackQueryHandler(handlers.main_menu, pattern="^main_menu$"),
            ],
            WAITING_WISH: [
                MessageHandler(filters.TEXT & ~filters.COMMAND, handlers.receive_wish)
            ],
        },
        fallbacks=[CommandHandler("cancel", handlers.cancel)],
    )

    application.add_handler(conv_handler)
    application.add_handler(PreCheckoutQueryHandler(handlers.precheckout_callback))
    application.add_handler(
        MessageHandler(filters.SUCCESSFUL_PAYMENT, handlers.successful_payment)
    )
    application.add_handler(CommandHandler("stats", handlers.admin_stats))
    application.add_handler(CommandHandler("draw", handlers.admin_draw))

    logger.info("Bot is starting...")
    application.run_polling()


if __name__ == "__main__":
    main()
