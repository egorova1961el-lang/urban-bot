import logging
import os
from pathlib import Path

from dotenv import load_dotenv
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ConversationHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

load_dotenv(dotenv_path=Path(__file__).parent / ".env")

BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ADMIN_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not BOT_TOKEN or not ADMIN_CHAT_ID:
    raise RuntimeError("TELEGRAM_BOT_TOKEN и TELEGRAM_CHAT_ID должны быть заданы в .env")

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

STATE_NAME, STATE_ROLE, STATE_NEEDS, STATE_CONTACT = range(4)

WELCOME_TEXT = (
    "Привет! Я бот урбан-туров от Этажи Девелопмент."
    "\n\nЯ помогу вам узнать о формате урбан-туров и собрать заявку на консультацию."
    "\n\nУрбан-тур — это двухдневный практический выезд, где девелоперы и застройщики знакомятся с лучшими городскими проектами, обсуждают продукт, маркетинг, продажи и получают реальные идеи для своих объектов."
)

INFO_TEXT = (
    "Урбан-тур дает:\n"
    "• новые знания и практические инструменты для команды;\n"
    "• свежий взгляд на продукт и среду будущих жителей;\n"
    "• преимущества на рынке и рост ликвидности объекта;\n"
    "• меньше дорогостоящих ошибок в принятии решений.\n\n"
    "Мы показываем успешные проекты, собираем сильные кейсы, организуем диалог с представителями застройщиков и экспертами.\n\n"
    "Тур проходит в разных городах: Новосибирск, Екатеринбург, Санкт-Петербург и другие регионы.\n"
)

ASK_NAME_TEXT = (
    "Отлично! Чтобы отправить заявку, сначала расскажите, пожалуйста, как к вам обращаться."
    " Укажите имя, компанию и должность.\n"
)

ASK_ROLE_TEXT = (
    "Спасибо! А свою роль вы можете описать как: девелопер, застройщик, риелтор или профильное направление?"
)

ASK_NEEDS_TEXT = (
    "Отлично. Что вам важно обсудить? Например: программу тура, выбор города, формат, продукт, продажи или партнёрство."
)

ASK_CONTACT_TEXT = (
    "И последний шаг — оставьте, пожалуйста, контакт для связи."
    " Напишите телефон в формате +7XXXXXXXXXX или email (например: +7 912 345-67-89)."
    " Также можно указать Telegram‑ник (например: @username).\n"
)

CONFIRMATION_TEXT = (
    "Заявка принята!\n\nМенеджер получит сообщение и свяжется с вами в ближайшее время."
)

MENU_KEYBOARD = InlineKeyboardMarkup(
    [
        [InlineKeyboardButton("Узнать об урбан-турах", callback_data="info")],
        [InlineKeyboardButton("Оставить заявку", callback_data="apply")],
    ]
)

ADM_FILE = Path(__file__).parent / "admin_chat.txt"


def load_admin_chat() -> str | None:
    # priority: runtime admin file -> env var
    try:
        if ADM_FILE.exists():
            return ADM_FILE.read_text(encoding="utf-8").strip()
    except Exception:
        pass
    return ADMIN_CHAT_ID


def save_admin_chat(chat_id: str) -> None:
    try:
        ADM_FILE.write_text(str(chat_id), encoding="utf-8")
    except Exception:
        logger.exception("Failed to save admin chat id to file")


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if update.message:
        await update.message.reply_text(WELCOME_TEXT, reply_markup=MENU_KEYBOARD)
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(WELCOME_TEXT, reply_markup=MENU_KEYBOARD)


async def info_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    if query:
        await query.answer()
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Оставить заявку", callback_data="apply")]]
        )
        await query.message.reply_text(INFO_TEXT, reply_markup=keyboard)


async def apply_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text(ASK_NAME_TEXT)
    elif update.message:
        await update.message.reply_text(ASK_NAME_TEXT)
    return STATE_NAME


async def ask_role(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["name_info"] = update.message.text.strip()
    await update.message.reply_text(ASK_ROLE_TEXT)
    return STATE_ROLE


async def ask_needs(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["role_info"] = update.message.text.strip()
    await update.message.reply_text(ASK_NEEDS_TEXT)
    return STATE_NEEDS


async def ask_contact(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["needs_info"] = update.message.text.strip()
    await update.message.reply_text(ASK_CONTACT_TEXT)
    return STATE_CONTACT


async def submit_application(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data["contact_info"] = update.message.text.strip()
    user = update.message.from_user

    name_info = context.user_data.get("name_info", "Не указано")
    role_info = context.user_data.get("role_info", "Не указано")
    needs_info = context.user_data.get("needs_info", "Не указано")
    contact_info = context.user_data.get("contact_info", "Не указано")
    username = f"@{user.username}" if user.username else "<без username>"
    user_link = f"tg://user?id={user.id}"

    admin_text = (
        "📌 Новая заявка на консультацию по урбан-турам:\n"
        f"• Имя / компания / должность: {name_info}\n"
        f"• Роль / профиль: {role_info}\n"
        f"• Что интересно: {needs_info}\n"
        f"• Контакты: {contact_info}\n"
        f"• Пользователь: {username} ({user_link})\n"
    )

    # Try to send to configured admin chat; if it's missing or equals the bot's username,
    # fall back to sending into the current chat (useful for local testing).
    target_chat = ADMIN_CHAT_ID
    try:
        bot_username = context.bot.username
    except Exception:
        bot_username = None

    if not target_chat or target_chat in (bot_username, f"@{bot_username}"):
        target_chat = update.effective_chat.id

    try:
        await context.bot.send_message(chat_id=target_chat, text=admin_text)
    except Exception as e:
        logger.error("Failed to send application to admin chat: %s", e)
        # As a last resort, send confirmation back to the user so they know it was captured
        await update.message.reply_text(
            "Заявка зарегистрирована, но не удалось отправить её в админ‑чат. Мы свяжемся с вами отдельно."
        )
    await update.message.reply_text(CONFIRMATION_TEXT)
    context.user_data.clear()
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    if update.message:
        await update.message.reply_text("Заявка отменена. Если хотите, нажмите /start и начните заново.")
    elif update.callback_query:
        await update.callback_query.answer()
        await update.callback_query.message.reply_text("Заявка отменена. Если хотите, нажмите /start и начните заново.")
    context.user_data.clear()
    return ConversationHandler.END


async def setadmin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    # Save current chat as admin chat — only allow if sender is admin/creator
    chat = update.effective_chat
    user = update.effective_user
    if chat is None or user is None:
        await update.message.reply_text("Не удалось определить чат или пользователя.")
        return

    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        if member.status not in ("administrator", "creator"):
            await update.message.reply_text("Только администратор чата может назначить этот чат как приём заявок.")
            return
    except Exception:
        # If check fails, still allow when command sent in private (owner setting)
        pass

    save_admin_chat(chat.id)
    await update.message.reply_text(f"Этот чат сохранён как админ‑чат (id: {chat.id}).")



async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Извините, я не понял. Используйте /start, чтобы открыть главное меню, или /cancel, чтобы отменить заявку."
    )


def main() -> None:
    application = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(apply_start, pattern="^apply$"),
            MessageHandler(filters.Regex("^(Оставить заявку|оставить заявку|Записаться|заявка)$"), apply_start),
        ],
        states={
            STATE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_role)],
            STATE_ROLE: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_needs)],
            STATE_NEEDS: [MessageHandler(filters.TEXT & ~filters.COMMAND, ask_contact)],
            STATE_CONTACT: [MessageHandler(filters.TEXT & ~filters.COMMAND, submit_application)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CallbackQueryHandler(info_callback, pattern="^info$"))
    application.add_handler(CommandHandler("setadmin", setadmin))
    application.add_handler(conv_handler)
    application.add_handler(CommandHandler("cancel", cancel))
    application.add_handler(MessageHandler(filters.COMMAND, unknown))

    logger.info("Urban Tour bot started")
    application.run_polling()


if __name__ == "__main__":
    main()
