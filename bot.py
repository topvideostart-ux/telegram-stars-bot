"""
🌟 Telegram Stars Bot — Войди в историю!
Книга рекордов Гиннесса: пожелание на самолёте Роналду
"""

import logging
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

# ─── Состояния ConversationHandler ─────────────────────────────────────────
CHOOSE_PLAN, WAITING_WISH, WAITING_INVITE_CHECK = range(3)

# ─── Тарифные планы ────────────────────────────────────────────────────────
PLANS = {
    "plan_300": {
        "stars": 300,
        "invites": 1,
        "title": "⭐ VIP — 300 звёзд",
        "description": "Пригласить 1 человека",
        "emoji": "🥇",
    },
    "plan_200": {
        "stars": 200,
        "invites": 2,
        "title": "⭐ PRO — 200 звёзд",
        "description": "Пригласить 2 человек",
        "emoji": "🥈",
    },
    "plan_100": {
        "stars": 100,
        "invites": 5,
        "title": "⭐ BASIC — 100 звёзд",
        "description": "Пригласить 5 человек",
        "emoji": "🥉",
    },
}

db = Database()

# ═══════════════════════════════════════════════════════════════════════════
#  /start — Приветствие
# ═══════════════════════════════════════════════════════════════════════════
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    logger.info(f"/start от пользователя {user.id} (@{user.username})")

    # Обработка реферальной ссылки
    if context.args:
        ref_id = context.args[0]
        if ref_id.startswith("ref_") and ref_id[4:].isdigit():
            inviter_id = int(ref_id[4:])
            if inviter_id != user.id:
                db.register_referral(inviter_id, user.id)

    db.add_user(user.id, user.username or user.first_name)

    caption = (
        "✈️ *ВОЙДИ В ИСТОРИЮ ПО ЦЕНЕ ЧАШКИ КОФЕ!*\\n\\n"
        "🏆 Мы создаём *запись в Книге рекордов Гиннесса* —\\n"
        "самое масштабное послание за всю историю человечества!\\n\\n"
        "📝 Твоё пожелание будет написано на *самолёте Криштиану Роналду*,\\n"
        "который облетит весь мир 🌍\\n\\n"
        "🎟 *100 участников* выиграют билеты на\\n"
        "⚽ *Чемпионат мира 2026!*\\n\\n"
        "Выбери свой план участия 👇"
    )

    keyboard = [
        [InlineKeyboardButton("🚀 УЧАСТВОВАТЬ!", callback_data="show_plans")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    chat_id = update.effective_chat.id

    await context.bot.send_photo(
        chat_id=chat_id,
        photo=open("images/welcome.jpg", "rb"),
        caption=caption,
        parse_mode="Markdown",
        reply_markup=reply_markup,
    )
    return CHOOSE_PLAN


# ═══════════════════════════════════════════════════════════════════════════
#  Показ планов
# ═══════════════════════════════════════════════════════════════════════════
async def show_plans(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    caption = (
        "💫 *ВЫБЕРИ СВОЙ ПЛАН УЧАСТИЯ*\\n\\n"
        "🥇 *300 ⭐* — пригласи *1 человека*\\n"
        "🥈 *200 ⭐* — пригласи *2 человека*\\n"
        "🥉 *100 ⭐* — пригласи *5 человек*\\n\\n"
        "📌 Чем больше друзей — тем выше шанс выиграть билет!\\n"
        "🎁 После оплаты напишешь своё пожелание на самолёт ✈️"
    )

    keyboard = [
        [InlineKeyboardButton("🥇 300 ⭐ — пригласить 1", callback_data="select_plan_300")],
        [InlineKeyboardButton("🥈 200 ⭐ — пригласить 2", callback_data="select_plan_200")],
        [InlineKeyboardButton("🥉 100 ⭐ — пригласить 5", callback_data="select_plan_100")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_media(
        media=InputMediaPhoto(
            media=open("images/plans.jpg", "rb"),
            caption=caption,
            parse_mode="Markdown",
        ),
        reply_markup=reply_markup,
    )
    return CHOOSE_PLAN


# ═══════════════════════════════════════════════════════════════════════════
#  Выбор плана → экран оплаты
# ═══════════════════════════════════════════════════════════════════════════
async def select_plan(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_key = query.data.replace("select_", "")   # "plan_300" / "plan_200" / "plan_100"
    plan = PLANS[plan_key]
    context.user_data["selected_plan"] = plan_key

    caption = (
        f"💳 *ОПЛАТА — {plan['title']}*\\n\\n"
        f"💰 Стоимость: *{plan['stars']} ⭐ Звёзд*\\n"
        f"👥 Нужно пригласить: *{plan['invites']} {'человека' if plan['invites'] < 5 else 'человек'}*\\n\\n"
        "✅ После успешной оплаты:\\n"
        "1️⃣ Получишь реферальную ссылку\\n"
        "2️⃣ Напишешь своё пожелание ✍️\\n"
        "3️⃣ Участвуешь в розыгрыше 🎟\\n\\n"
        "👇 Нажми кнопку для оплаты!"
    )

    keyboard = [
        [InlineKeyboardButton(f"💫 Оплатить {plan['stars']} ⭐", callback_data=f"pay_{plan_key}")],
        [InlineKeyboardButton("◀️ Назад", callback_data="show_plans")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await query.edit_message_media(
        media=InputMediaPhoto(
            media=open("images/payment.jpg", "rb"),
            caption=caption,
            parse_mode="Markdown",
        ),
        reply_markup=reply_markup,
    )
    return CHOOSE_PLAN


# ═══════════════════════════════════════════════════════════════════════════
#  Отправка инвойса (Telegram Stars)
# ═══════════════════════════════════════════════════════════════════════════
async def send_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    plan_key = query.data.replace("pay_", "")
    plan = PLANS[plan_key]
    context.user_data["selected_plan"] = plan_key

    await context.bot.send_invoice(
        chat_id=query.from_user.id,
        title=f"🌟 {plan['title']}",
        description=(
            f"✈️ Пожелание на самолёте Роналду\\n"
            f"👥 Пригласить {plan['invites']} {'человека' if plan['invites'] < 5 else 'человек'}\\n"
            f"🎟 Шанс выиграть билет на ЧМ-2026"
        ),
        payload=f"{plan_key}:{query.from_user.id}",
        provider_token="",          # пустой токен = оплата Звёздами
        currency="XTR",             # XTR = Telegram Stars
        prices=[LabeledPrice(label=plan["title"], amount=plan["stars"])],
        photo_url="https://i.imgur.com/placeholder_stars.jpg",
        photo_size=800,
        photo_width=800,
        photo_height=450,
        need_name=False,
        need_phone_number=False,
        need_email=False,
    )
    return CHOOSE_PLAN


# ═══════════════════════════════════════════════════════════════════════════
#  Pre-Checkout (обязательно одобрить)
# ═══════════════════════════════════════════════════════════════════════════
async def pre_checkout(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.pre_checkout_query.answer(ok=True)


# ═══════════════════════════════════════════════════════════════════════════
#  Успешная оплата
# ═══════════════════════════════════════════════════════════════════════════
async def successful_payment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    payment = update.message.successful_payment
    payload = payment.invoice_payload          # "plan_300:12345678"
    plan_key = payload.split(":")[0]
    plan = PLANS[plan_key]

    db.set_user_plan(user.id, plan_key, plan["stars"], plan["invites"])

    ref_link = f"https://t.me/{context.bot.username}?start=ref_{user.id}"
    context.user_data["selected_plan"] = plan_key

    caption = (
        "🎉 *ОПЛАТА ПРОШЛА УСПЕШНО!*\\n\\n"
        f"✅ Твой план: *{plan['title']}*\\n\\n"
        "🔗 *Твоя реферальная ссылка:*\\n"
        f"`{ref_link}`\\n\\n"
        f"👥 Тебе нужно пригласить *{plan['invites']} {'человека' if plan['invites'] < 5 else 'человек'}*\\n\\n"
        "📝 Теперь напиши своё *пожелание* — оно появится на самолёте Роналду!\\n"
        "✍️ _Введи текст ниже (до 500 символов):_"
    )

    await update.message.reply_photo(
        photo=open("images/success.jpg", "rb"),
        caption=caption,
        parse_mode="Markdown",
    )
    return WAITING_WISH


# ═══════════════════════════════════════════════════════════════════════════
#  Получение пожелания
# ═══════════════════════════════════════════════════════════════════════════
async def receive_wish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user

# ═══════════════════════════════════════════════════════════════════════════
async def receive_wish(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
