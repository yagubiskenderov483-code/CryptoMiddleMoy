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
MANAGER   = "@CryptoMiddleManager"
SUPPORT   = "@CryptoMiddleSupport"
SAFETY    = "https://telegra.ph/Pochemu-ehto-bezopasno-07-02"
TON_ADDR  = "UQDUUFncBcWC4eH3wN_4G3N9Yaf6nBFlcumDP8daYAQHNSOc"
CARD_BANK = "ВТБ Банк"
CARD_NUM  = "4276380123456789"
CARD_HOLD = "Александр Ф."

DEAL_SUBJECTS = [
    ("Gift",  "🎁 Гифт"),
    ("Stars", "⭐️ Звёзды"),
    ("TON",   "💎 TON"),
    ("USDT",  "💵 USDT"),
    ("RUB",   "💳 Рубли"),
    ("Other", "📦 Другое"),
]
PAYMENT_METHODS = [
    ("TON",       "💎 TON"),
    ("USDT",      "💵 USDT"),
    ("Stars",     "⭐️ Звёзды"),
    ("Card",      "💳 Карта"),
    ("CryptoBot", "🤖 CryptoBot"),
]
CARD_COUNTRIES = [
    ("RU", "🇷🇺 Россия"),
    ("KZ", "🇰🇿 Казахстан"),
    ("TJ", "🇹🇯 Таджикистан"),
    ("AZ", "🇦🇿 Азербайджан"),
]
FAKE_DEALS = [
    {"amount": 5,   "desc": "Аккаунт Steam"},
    {"amount": 40,  "desc": "Подписка Spotify"},
    {"amount": 120, "desc": "Игровой ключ"},
    {"amount": 2,   "desc": "Донат в игре"},
    {"amount": 16,  "desc": "VPN на год"},
    {"amount": 75,  "desc": "Аккаунт Netflix"},
    {"amount": 33,  "desc": "Подписка Telegram"},
    {"amount": 200, "desc": "Аккаунт YouTube"},
    {"amount": 8,   "desc": "Промокод магазина"},
    {"amount": 55,  "desc": "Доступ к сервису"},
]

bot = Bot(token=BOT_TOKEN)
dp  = Dispatcher(storage=MemoryStorage())
user_data    = {}
deals        = {}
deal_counter = [1000]


def get_user(uid):
    if uid not in user_data:
        user_data[uid] = {
            "ton": "", "usdt": "", "stars": "",
            "card": "", "card_name": "", "card_country": "",
            "wd_ton": "", "wd_usdt": "", "wd_stars": "",
            "wd_card": "", "wd_card_name": "", "wd_card_country": "",
            "wd_cryptobot": "",
            "balance": 0.0, "reputation": 0,
            "deals_count": 0, "reviews": [],
            "lang": "ru", "turnover": 0.0,
            "agreed": False, "my_deals": [],
            "banner_msg_id": None,
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


def reg(msg):
    if msg.from_user and msg.from_user.username:
        username_map[msg.from_user.username.lower()] = msg.from_user.id


def find_uid(q):
    q = q.strip()
    if q.startswith("@"):
        return username_map.get(q[1:].lower())
    try:
        v = int(q)
        return v if v in user_data else None
    except Exception:
        return None


def valid_ton(a):
    return bool(re.match(r"^[UE]Q[A-Za-z0-9_\-]{46}$", a.strip()))


def valid_usdt(a):
    return bool(re.match(r"^T[A-Za-z0-9]{33}$", a.strip()))


def valid_card(n):
    d = re.sub(r"[\s\-]", "", n)
    return d.isdigit() and len(d) == 16


def valid_uname(u):
    return bool(re.match(r"^[A-Za-z0-9_]{4,}$", u.lstrip("@")))


def valid_amount(s):
    try:
        v = float(s.strip().replace(",", "."))
        return v if v > 0 else None
    except Exception:
        return None


def has_any_req(uid):
    u = get_user(uid)
    return any([u.get("ton"), u.get("usdt"), u.get("stars"), u.get("card")])


def has_req(uid, m):
    u = get_user(uid)
    ml = m.lower()
    if ml == "ton":       return bool(u.get("ton"))
    if ml == "usdt":      return bool(u.get("usdt"))
    if ml == "stars":     return bool(u.get("stars"))
    if ml == "card":      return bool(u.get("card"))
    if ml == "cryptobot": return True
    return True


def has_wd_req(uid, m):
    u = get_user(uid)
    ml = m.lower()
    if ml == "ton":       return bool(u.get("wd_ton"))
    if ml == "usdt":      return bool(u.get("wd_usdt"))
    if ml == "stars":     return bool(u.get("wd_stars"))
    if ml == "card":      return bool(u.get("wd_card"))
    if ml == "cryptobot": return bool(u.get("wd_cryptobot"))
    return False


def get_wd_str(uid, m):
    u = get_user(uid)
    ml = m.lower()
    if ml == "ton":       return u.get("wd_ton", "-")
    if ml == "usdt":      return u.get("wd_usdt", "-")
    if ml == "stars":     return u.get("wd_stars", "-")
    if ml == "cryptobot": return u.get("wd_cryptobot", "-")
    cc = u.get("wd_card_country", "")
    return (u.get("wd_card", "-") + " " + cc).strip()


async def safe_del(msg):
    try:
        await msg.delete()
    except Exception:
        pass


async def del_prev(uid):
    mid = get_user(uid).get("banner_msg_id")
    if mid:
        try:
            await bot.delete_message(uid, mid)
        except Exception:
            pass
        get_user(uid)["banner_msg_id"] = None


# ── FSM ──────────────────────────────────────────────────────────────────────

class SetBanner(StatesGroup):
    waiting = State()

class AddReq(StatesGroup):
    ton = State()
    usdt = State()
    stars = State()
    card_num = State()
    card_name = State()
    card_country = State()

class AddWdReq(StatesGroup):
    ton = State()
    usdt = State()
    stars = State()
    card_num = State()
    card_name = State()
    card_country = State()
    cryptobot = State()

class Deal(StatesGroup):
    role = State()
    partner = State()
    subject = State()
    description = State()
    payment = State()
    amount = State()

class TopUp(StatesGroup):
    amount = State()

class Withdraw(StatesGroup):
    method = State()
    amount = State()

class AdminAction(StatesGroup):
    reputation = State()
    balance = State()
    review = State()


# ── texts ─────────────────────────────────────────────────────────────────────

LANGS = {
"ru": {
"welcome": (
    "<b>Добро пожаловать 👋</b>\n\n"
    "<b>Crypto Middle</b> — сервис безопасных сделок.\n\n"
    "<b>Комиссия: 0%\nРежим: 24/7\n"
    f"Поддержка: {SUPPORT}</b>"
),
"btn_deal":     "🔐 Создать сделку",
"btn_req":      "🧾 Реквизиты",
"btn_topup":    "💰 Пополнить",
"btn_withdraw": "💸 Вывести",
"btn_security": "🛡 Безопасность",
"btn_support":  "📋 Поддержка",
"btn_language": "🌐 Язык",
"btn_menu":     "📱 В меню",
"btn_back":     "◀️ Назад",
"btn_cancel":   "❌ Отмена",
"btn_agree":    "📍 Подтвердить",
"btn_paid":     "💸 Я оплатил",
"btn_manager":  "💬 Написать менеджеру",
"btn_why_safe": "🛡 Почему безопасно?",
"btn_cur_deals":"📋 Текущие сделки",
"btn_my_deals": "📂 Мои сделки",
"btn_buyer":    "🛒 Покупатель",
"btn_seller":   "📦 Продавец",

"agreement": (
    "<b>Пользовательское соглашение</b>\n\n"
    f"<b>Передача активов только через: {MANAGER}</b>\n\n"
    "<b>Прямые переводы запрещены.\n"
    "Вывод после подтверждения обеими сторонами.\n\n"
    "Нажмите кнопку для подтверждения.</b>"
),
"deal_s0": "<b>Создание сделки — Шаг 1/6\n\nКто вы в этой сделке?</b>",
"deal_s1": "<b>Создание сделки — Шаг 2/6\n\nВведите @username второго участника (мин. 4 символа):</b>",
"deal_s2": "<b>Создание сделки — Шаг 3/6\n\nВыберите предмет сделки:</b>",
"deal_s3": "<b>Создание сделки — Шаг 4/6\n\nОпишите суть сделки (мин. 8 символов):</b>",
"deal_s3_short": "<b>Суть должна быть не менее 8 символов. Введите снова:</b>",
"deal_s4_seller": "<b>Создание сделки — Шаг 5/6\n\nВыберите вариант для получения оплаты:</b>",
"deal_s4_buyer":  "<b>Создание сделки — Шаг 5/6\n\nВыберите вариант для оплаты:</b>",
"deal_s5": "<b>Создание сделки — Шаг 6/6\n\nВведите сумму сделки (только цифры):</b>",

"no_req_deal": "<b>Вы должны добавить реквизит чтобы продолжить сделку.</b>",
"no_req_method": "<b>У вас нет реквизита для {m}.\n\nДобавьте его в разделе Реквизиты.</b>",

"deal_created": (
    "<b>Сделка создана!</b>\n\n"
    "<b>ID: {deal_id}\n"
    "Участник: {partner}\n"
    "Предмет: {subject}\n"
    "Суть: {description}\n"
    "Сумма: {amount}\n"
    "Оплата: {payment}\n"
    "Ваша роль: {role}</b>\n\n"
    "<b>Ссылка для участника:</b>\n"
    "<code>https://t.me/{bot_username}?start=deal_{deal_id}</code>\n\n"
    "<b>Отправьте ссылку второму участнику.\n"
    "Условия появятся когда он перейдёт по ссылке.</b>"
),
"deal_info_seller": (
    "<b>Информация о сделке</b>\n\n"
    "<blockquote><b>ID: {deal_id}\n"
    "Предмет: {subject}\n"
    "Суть: {description}\n"
    "Сумма: {amount}\n"
    "Оплата: {payment}</b></blockquote>\n\n"
    "<b>Ваша роль: Продавец</b>\n\n"
    f"<b>Передайте товар менеджеру: {MANAGER}\n"
    "После подтверждения покупатель оплатит.</b>"
),
"deal_info_buyer": (
    "<b>Информация о сделке</b>\n\n"
    "<blockquote><b>ID: {deal_id}\n"
    "Предмет: {subject}\n"
    "Суть: {description}\n"
    "Сумма: {amount}\n"
    "Оплата: {payment}</b></blockquote>\n\n"
    "<b>Ваша роль: Покупатель</b>\n\n"
    f"<b>Продавец передаёт товар менеджеру: {MANAGER}\n"
    "Дождитесь подтверждения, затем оплатите.</b>"
),
"deal_notify": (
    "<b>По вашей сделке перешёл участник!</b>\n\n"
    "<blockquote><b>ID: {deal_id}\n"
    "Участник: {buyer}\n"
    "Предмет: {subject}\n"
    "Суть: {description}\n"
    "Сумма: {amount} | Оплата: {payment}</b></blockquote>"
),
"own_deal":       "<b>Это ваша собственная сделка.</b>",
"deal_not_found": "<b>Сделка не найдена или уже завершена.</b>",

"paid_adm": "<b>Оплата по сделке\n\nСделка: {deal_id}\nПользователь: {user}\nСумма: {amount} | Оплата: {payment}</b>",
"paid_seller": "<b>Покупатель сообщил об оплате по сделке {deal_id}.\nМенеджер проверяет.</b>",
"paid_ok": "<b>Уведомление отправлено менеджеру.\nОжидайте подтверждения.</b>",

"my_deals_empty": "<b>У вас нет активных сделок.</b>",
"my_deals_title": "<b>Ваши сделки:</b>\n\n",
"my_deal_line": (
    "<blockquote><b>ID: {did} | {subject}\n"
    "Суть: {desc}\n"
    "Сумма: {amount} | Оплата: {payment}\n"
    "Роль: {role} | Статус: {status}</b></blockquote>\n\n"
),

"req_title": (
    "<b>Реквизиты для получения оплаты</b>\n\n"
    "<blockquote><b>TON:</b> {ton}</blockquote>\n"
    "<blockquote><b>USDT (TRC20):</b> {usdt}</blockquote>\n"
    "<blockquote><b>Звёзды:</b> {stars}</blockquote>\n"
    "<blockquote><b>Карта:</b> {card} {cc}</blockquote>"
),
"wd_req_title": (
    "<b>Реквизиты для вывода</b>\n\n"
    "<blockquote><b>TON:</b> {ton}</blockquote>\n"
    "<blockquote><b>USDT (TRC20):</b> {usdt}</blockquote>\n"
    "<blockquote><b>Звёзды:</b> {stars}</blockquote>\n"
    "<blockquote><b>Карта:</b> {card} {cc}</blockquote>\n"
    "<blockquote><b>CryptoBot:</b> {cb}</blockquote>"
),
"enter_ton":   "<b>Введите TON адрес:\n(начинается с UQ или EQ, 48 символов)</b>",
"enter_usdt":  "<b>Введите USDT адрес (TRC20):\n(начинается с T, 34 символа)</b>",
"enter_stars": "<b>Введите @username для получения Звёзд:\n(мин. 4 символа)</b>",
"enter_card":  "<b>Введите номер карты (16 цифр):</b>",
"enter_cname": "<b>Введите имя держателя карты:</b>",
"enter_ctry":  "<b>Выберите страну карты:</b>",
"enter_cb":    "<b>Введите ваш @username в CryptoBot:</b>",
"err_ton":     "<b>❌ Некорректный TON адрес.\nUQ или EQ + 48 символов.\n\nВведите снова:</b>",
"err_usdt":    "<b>❌ Некорректный USDT адрес.\nT + 33 символа.\n\nВведите снова:</b>",
"err_stars":   "<b>❌ Некорректный username.\nМин. 4 символа, буквы/цифры/_\n\nВведите снова:</b>",
"err_card":    "<b>❌ Некорректный номер карты.\n16 цифр.\n\nВведите снова:</b>",
"err_uname":   "<b>❌ Некорректный @username.\nМин. 4 символа.\n\nВведите снова:</b>",
"saved_ton":   "<b>✅ TON адрес сохранён!</b>",
"saved_usdt":  "<b>✅ USDT адрес сохранён!</b>",
"saved_stars": "<b>✅ Username для Звёзд сохранён!</b>",
"saved_card":  "<b>✅ Карта сохранена!</b>",
"saved_cb":    "<b>✅ CryptoBot username сохранён!</b>",
"card_step2":  "<b>Теперь введите имя держателя карты:</b>",

"topup_choose": "<b>Пополнение баланса\n\nШаг 1: Выберите способ:</b>",
"topup_amount": "<b>Шаг 2: Введите сумму (только цифры):</b>",
"topup_stars":  f"<b>Пополнение Звёздами\n\nСумма: {{amount}} Stars\n\nОтправьте Stars на: {MANAGER}\n\nВремя зачисления: 5-15 минут</b>",
"topup_ton":    f"<b>Пополнение TON\n\nСумма: {{amount}} TON\n\n<code>{TON_ADDR}</code>\n\nПосле отправки напишите: {SUPPORT}\n\nВремя зачисления: 5-15 минут</b>",
"topup_usdt":   f"<b>Пополнение USDT (TRC20)\n\nСумма: {{amount}} USDT\n\nПосле отправки напишите: {SUPPORT}\n\nВремя зачисления: 5-15 минут</b>",
"topup_card":   f"<b>Пополнение картой\n\nСумма: {{amount}} RUB\n\nБанк: {CARD_BANK}\nНомер: <code>{CARD_NUM}</code>\nДержатель: {CARD_HOLD}\n\nСохраните чек и нажмите кнопку ниже.\n\nВремя зачисления: 5-15 минут</b>",
"topup_cb":     f"<b>Пополнение через CryptoBot\n\nСумма: {{amount}}\n\nПереведите на: {MANAGER} в CryptoBot\n\nВремя зачисления: 5-15 минут</b>",

"wd_zero":    "<b>❌ У вас баланс 0.</b>",
"wd_choose":  "<b>Вывод средств\n\nБаланс: {balance}\n\nШаг 1: Выберите способ вывода:</b>",
"wd_no_req":  "<b>Нет реквизита для вывода через {m}.\n\nДобавьте реквизит.</b>",
"wd_amount":  "<b>Шаг 2: Введите сумму вывода (только цифры):\n\nДоступно: {balance}</b>",
"wd_low":     "<b>Недостаточно средств.\nДоступно: {balance}\n\nВведите другую сумму:</b>",
"wd_confirm": "<b>Вывод через {m}\n\nРеквизит:\n<blockquote>{req}</blockquote>\nСумма: {amount}\n\nПодтвердите вывод:</b>",
"wd_done":    "<b>Заявка на вывод отправлена.\nОжидайте обработки.</b>",
"wd_adm":     "<b>Заявка на вывод\n\nПользователь: {user}\nСумма: {amount}\nМетод: {m}\nРеквизит: {req}</b>",
"btn_confirm_wd": "✅ Подтвердить вывод",
"btn_add_wd_req": "➕ Добавить реквизит вывода",

"security": (
    "<b>Безопасность при передаче активов</b>\n\n"
    f"<b>Передача только через: {MANAGER}</b>\n\n"
    "<b>Прямые транзакции запрещены.\n"
    "Сверяйте сумму и ID сделки.\n"
    "Вывод после подтверждения обеими сторонами.</b>"
),
"lang_choose": "<b>Выберите язык:</b>",
"lang_set":    "<b>Язык: Русский</b>",
"err_amount":  "<b>❌ Некорректная сумма. Введите число, например: 100\n\nПопробуйте снова:</b>",
"err_uname2":  "<b>❌ Некорректный @username (мин. 4 символа).\n\nВведите снова:</b>",
"cur_title":   "<b>Текущие сделки</b>\n\n",
"cur_line":    "<blockquote><b>#{n} | {amount}$ — {desc}\nПокупатель: {b} | Продавец: {s}\nСтатус: Активна</b></blockquote>\n\n",
"role_s": "Продавец", "role_b": "Покупатель",
},
"en": {
"welcome": (
    "<b>Welcome 👋</b>\n\n"
    "<b>Crypto Middle</b> — secure OTC deal service.\n\n"
    "<b>Commission: 0%\nHours: 24/7\n"
    f"Support: {SUPPORT}</b>"
),
"btn_deal":     "🔐 Create Deal",
"btn_req":      "🧾 Requisites",
"btn_topup":    "💰 Top Up",
"btn_withdraw": "💸 Withdraw",
"btn_security": "🛡 Security",
"btn_support":  "📋 Support",
"btn_language": "🌐 Language",
"btn_menu":     "📱 Menu",
"btn_back":     "◀️ Back",
"btn_cancel":   "❌ Cancel",
"btn_agree":    "📍 Confirm",
"btn_paid":     "💸 I Paid",
"btn_manager":  "💬 Write to Manager",
"btn_why_safe": "🛡 Why is this safe?",
"btn_cur_deals":"📋 Current Deals",
"btn_my_deals": "📂 My Deals",
"btn_buyer":    "🛒 Buyer",
"btn_seller":   "📦 Seller",

"agreement": (
    "<b>User Agreement</b>\n\n"
    f"<b>Transfer assets only through: {MANAGER}</b>\n\n"
    "<b>Direct transfers are prohibited.\n"
    "Withdrawal after both sides confirm.\n\n"
    "Press the button to confirm.</b>"
),
"deal_s0": "<b>Create Deal — Step 1/6\n\nWhat is your role?</b>",
"deal_s1": "<b>Create Deal — Step 2/6\n\nEnter @username of the second participant (min 4 chars):</b>",
"deal_s2": "<b>Create Deal — Step 3/6\n\nChoose deal subject:</b>",
"deal_s3": "<b>Create Deal — Step 4/6\n\nDescribe the deal (min 8 chars):</b>",
"deal_s3_short": "<b>Description must be at least 8 characters. Try again:</b>",
"deal_s4_seller": "<b>Create Deal — Step 5/6\n\nChoose how to receive payment:</b>",
"deal_s4_buyer":  "<b>Create Deal — Step 5/6\n\nChoose payment method:</b>",
"deal_s5": "<b>Create Deal — Step 6/6\n\nEnter deal amount (numbers only):</b>",

"no_req_deal":   "<b>You must add a requisite to continue the deal.</b>",
"no_req_method": "<b>No requisite for {m}.\n\nAdd it in Requisites.</b>",

"deal_created": (
    "<b>Deal created!</b>\n\n"
    "<b>ID: {deal_id}\n"
    "Participant: {partner}\n"
    "Subject: {subject}\n"
    "Description: {description}\n"
    "Amount: {amount}\n"
    "Payment: {payment}\n"
    "Your role: {role}</b>\n\n"
    "<b>Participant link:</b>\n"
    "<code>https://t.me/{bot_username}?start=deal_{deal_id}</code>\n\n"
    "<b>Send the link to the participant.\n"
    "Terms will appear once they open it.</b>"
),
"deal_info_seller": (
    "<b>Deal Information</b>\n\n"
    "<blockquote><b>ID: {deal_id}\n"
    "Subject: {subject}\n"
    "Description: {description}\n"
    "Amount: {amount}\n"
    "Payment: {payment}</b></blockquote>\n\n"
    "<b>Your role: Seller</b>\n\n"
    f"<b>Transfer the asset to manager: {MANAGER}\n"
    "After confirmation buyer will send payment.</b>"
),
"deal_info_buyer": (
    "<b>Deal Information</b>\n\n"
    "<blockquote><b>ID: {deal_id}\n"
    "Subject: {subject}\n"
    "Description: {description}\n"
    "Amount: {amount}\n"
    "Payment: {payment}</b></blockquote>\n\n"
    "<b>Your role: Buyer</b>\n\n"
    f"<b>Seller transfers asset to manager: {MANAGER}\n"
    "Wait for confirmation, then send payment.</b>"
),
"deal_notify": (
    "<b>A participant joined your deal!</b>\n\n"
    "<blockquote><b>ID: {deal_id}\n"
    "Participant: {buyer}\n"
    "Subject: {subject}\n"
    "Description: {description}\n"
    "Amount: {amount} | Payment: {payment}</b></blockquote>"
),
"own_deal":       "<b>This is your own deal.</b>",
"deal_not_found": "<b>Deal not found or already closed.</b>",

"paid_adm":    "<b>Payment\n\nDeal: {deal_id}\nUser: {user}\nAmount: {amount} | Payment: {payment}</b>",
"paid_seller": "<b>Buyer reported payment for deal {deal_id}.\nManager is verifying.</b>",
"paid_ok":     "<b>Notification sent to manager.\nWaiting for confirmation.</b>",

"my_deals_empty": "<b>You have no active deals.</b>",
"my_deals_title": "<b>Your deals:</b>\n\n",
"my_deal_line": (
    "<blockquote><b>ID: {did} | {subject}\n"
    "Desc: {desc}\n"
    "Amount: {amount} | Payment: {payment}\n"
    "Role: {role} | Status: {status}</b></blockquote>\n\n"
),

"req_title": (
    "<b>Requisites for receiving payment</b>\n\n"
    "<blockquote><b>TON:</b> {ton}</blockquote>\n"
    "<blockquote><b>USDT (TRC20):</b> {usdt}</blockquote>\n"
    "<blockquote><b>Stars:</b> {stars}</blockquote>\n"
    "<blockquote><b>Card:</b> {card} {cc}</blockquote>"
),
"wd_req_title": (
    "<b>Withdrawal Requisites</b>\n\n"
    "<blockquote><b>TON:</b> {ton}</blockquote>\n"
    "<blockquote><b>USDT (TRC20):</b> {usdt}</blockquote>\n"
    "<blockquote><b>Stars:</b> {stars}</blockquote>\n"
    "<blockquote><b>Card:</b> {card} {cc}</blockquote>\n"
    "<blockquote><b>CryptoBot:</b> {cb}</blockquote>"
),
"enter_ton":   "<b>Enter TON address:\n(starts with UQ or EQ, 48 chars)</b>",
"enter_usdt":  "<b>Enter USDT address (TRC20):\n(starts with T, 34 chars)</b>",
"enter_stars": "<b>Enter @username for Stars:\n(min 4 chars)</b>",
"enter_card":  "<b>Enter card number (16 digits):</b>",
"enter_cname": "<b>Enter cardholder name:</b>",
"enter_ctry":  "<b>Choose card country:</b>",
"enter_cb":    "<b>Enter your CryptoBot @username:</b>",
"err_ton":     "<b>❌ Invalid TON address.\nUQ or EQ + 48 chars.\n\nEnter again:</b>",
"err_usdt":    "<b>❌ Invalid USDT address.\nT + 33 chars.\n\nEnter again:</b>",
"err_stars":   "<b>❌ Invalid username.\nMin 4 chars, letters/digits/_\n\nEnter again:</b>",
"err_card":    "<b>❌ Invalid card number.\n16 digits.\n\nEnter again:</b>",
"err_uname":   "<b>❌ Invalid @username.\nMin 4 chars.\n\nEnter again:</b>",
"saved_ton":   "<b>✅ TON address saved!</b>",
"saved_usdt":  "<b>✅ USDT address saved!</b>",
"saved_stars": "<b>✅ Stars username saved!</b>",
"saved_card":  "<b>✅ Card saved!</b>",
"saved_cb":    "<b>✅ CryptoBot username saved!</b>",
"card_step2":  "<b>Now enter the cardholder name:</b>",

"topup_choose": "<b>Top Up Balance\n\nStep 1: Choose method:</b>",
"topup_amount": "<b>Step 2: Enter amount (numbers only):</b>",
"topup_stars":  f"<b>Top Up Stars\n\nAmount: {{amount}} Stars\n\nSend Stars to: {MANAGER}\n\nProcessing time: 5-15 minutes</b>",
"topup_ton":    f"<b>Top Up TON\n\nAmount: {{amount}} TON\n\n<code>{TON_ADDR}</code>\n\nAfter sending contact: {SUPPORT}\n\nProcessing time: 5-15 minutes</b>",
"topup_usdt":   f"<b>Top Up USDT (TRC20)\n\nAmount: {{amount}} USDT\n\nAfter sending contact: {SUPPORT}\n\nProcessing time: 5-15 minutes</b>",
"topup_card":   f"<b>Top Up Card\n\nAmount: {{amount}} RUB\n\nBank: {CARD_BANK}\nNumber: <code>{CARD_NUM}</code>\nHolder: {CARD_HOLD}\n\nSave receipt and press button below.\n\nProcessing time: 5-15 minutes</b>",
"topup_cb":     f"<b>Top Up via CryptoBot\n\nAmount: {{amount}}\n\nTransfer to: {MANAGER} in CryptoBot\n\nProcessing time: 5-15 minutes</b>",

"wd_zero":    "<b>❌ Your balance is 0.</b>",
"wd_choose":  "<b>Withdraw\n\nBalance: {balance}\n\nStep 1: Choose method:</b>",
"wd_no_req":  "<b>No withdrawal requisite for {m}.\n\nAdd one.</b>",
"wd_amount":  "<b>Step 2: Enter amount (numbers only):\n\nAvailable: {balance}</b>",
"wd_low":     "<b>Insufficient funds.\nAvailable: {balance}\n\nEnter different amount:</b>",
"wd_confirm": "<b>Withdraw via {m}\n\nRequisite:\n<blockquote>{req}</blockquote>\nAmount: {amount}\n\nConfirm:</b>",
"wd_done":    "<b>Withdrawal request sent.\nWaiting for processing.</b>",
"wd_adm":     "<b>Withdrawal Request\n\nUser: {user}\nAmount: {amount}\nMethod: {m}\nRequisite: {req}</b>",
"btn_confirm_wd": "✅ Confirm Withdrawal",
"btn_add_wd_req": "➕ Add Withdrawal Requisite",

"security": (
    "<b>Asset Transfer Security</b>\n\n"
    f"<b>Transfer only through: {MANAGER}</b>\n\n"
    "<b>Direct transactions are prohibited.\n"
    "Verify amount and deal ID.\n"
    "Withdrawal after both sides confirm.</b>"
),
"lang_choose": "<b>Choose language:</b>",
"lang_set":    "<b>Language: English</b>",
"err_amount":  "<b>❌ Invalid amount. Enter a number, e.g.: 100\n\nTry again:</b>",
"err_uname2":  "<b>❌ Invalid @username (min 4 chars).\n\nEnter again:</b>",
"cur_title":   "<b>Current Deals</b>\n\n",
"cur_line":    "<blockquote><b>#{n} | {amount}$ — {desc}\nBuyer: {b} | Seller: {s}\nStatus: Active</b></blockquote>\n\n",
"role_s": "Seller", "role_b": "Buyer",
},
}


# ── keyboards ─────────────────────────────────────────────────────────────────

def main_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid, "btn_deal"),      callback_data="deal"),
         InlineKeyboardButton(text=L(uid, "btn_req"),       callback_data="requisites")],
        [InlineKeyboardButton(text=L(uid, "btn_topup"),     callback_data="topup"),
         InlineKeyboardButton(text=L(uid, "btn_withdraw"),  callback_data="withdraw")],
        [InlineKeyboardButton(text=L(uid, "btn_security"),  callback_data="security"),
         InlineKeyboardButton(text=L(uid, "btn_cur_deals"), callback_data="cur_deals")],
        [InlineKeyboardButton(text=L(uid, "btn_my_deals"),  callback_data="my_deals"),
         InlineKeyboardButton(text=L(uid, "btn_language"),  callback_data="language")],
        [InlineKeyboardButton(text=L(uid, "btn_support"),
                              url=f"https://t.me/{SUPPORT.lstrip('@')}")],
        [InlineKeyboardButton(text=L(uid, "btn_menu"),      callback_data="menu")],
    ])


def back_kb(uid, cb="menu"):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid, "btn_back"), callback_data=cb)],
        [InlineKeyboardButton(text=L(uid, "btn_menu"), callback_data="menu")],
    ])


def cancel_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid, "btn_cancel"), callback_data="menu")],
    ])


def agree_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid, "btn_agree"), callback_data="confirm_agreement")],
        [InlineKeyboardButton(text=L(uid, "btn_back"),  callback_data="menu")],
    ])


def role_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid, "btn_buyer"),  callback_data="drole_buyer"),
         InlineKeyboardButton(text=L(uid, "btn_seller"), callback_data="drole_seller")],
        [InlineKeyboardButton(text=L(uid, "btn_cancel"), callback_data="menu")],
    ])


def subject_kb(uid):
    rows = []
    row = []
    for code, label in DEAL_SUBJECTS:
        row.append(InlineKeyboardButton(text=label, callback_data=f"dsubj_{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=L(uid, "btn_cancel"), callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def payment_kb(uid):
    rows = []
    row = []
    for code, label in PAYMENT_METHODS:
        row.append(InlineKeyboardButton(text=label, callback_data=f"dpay_{code}"))
        if len(row) == 2:
            rows.append(row)
            row = []
    if row:
        rows.append(row)
    rows.append([InlineKeyboardButton(text=L(uid, "btn_cancel"), callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def deal_kb(uid, deal_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid, "btn_paid"),     callback_data=f"paid_{deal_id}")],
        [InlineKeyboardButton(text=L(uid, "btn_manager"),  url=f"https://t.me/{MANAGER.lstrip('@')}")],
        [InlineKeyboardButton(text=L(uid, "btn_why_safe"), url=SAFETY)],
        [InlineKeyboardButton(text=L(uid, "btn_back"),     callback_data="menu")],
        [InlineKeyboardButton(text=L(uid, "btn_menu"),     callback_data="menu")],
    ])


def req_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 TON",    callback_data="req_ton"),
         InlineKeyboardButton(text="💵 USDT",   callback_data="req_usdt")],
        [InlineKeyboardButton(text="⭐️ Звёзды", callback_data="req_stars"),
         InlineKeyboardButton(text="💳 Карта",  callback_data="req_card")],
        [InlineKeyboardButton(text=L(uid, "btn_back"), callback_data="menu")],
        [InlineKeyboardButton(text=L(uid, "btn_menu"), callback_data="menu")],
    ])


def wd_req_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 TON",       callback_data="wdreq_ton"),
         InlineKeyboardButton(text="💵 USDT",      callback_data="wdreq_usdt")],
        [InlineKeyboardButton(text="⭐️ Звёзды",   callback_data="wdreq_stars"),
         InlineKeyboardButton(text="💳 Карта",     callback_data="wdreq_card")],
        [InlineKeyboardButton(text="🤖 CryptoBot", callback_data="wdreq_cryptobot")],
        [InlineKeyboardButton(text=L(uid, "btn_back"), callback_data="menu")],
    ])


def topup_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ Звёзды",   callback_data="tu_stars"),
         InlineKeyboardButton(text="💎 TON",       callback_data="tu_ton")],
        [InlineKeyboardButton(text="💵 USDT",      callback_data="tu_usdt"),
         InlineKeyboardButton(text="💳 Карта",     callback_data="tu_card")],
        [InlineKeyboardButton(text="🤖 CryptoBot", callback_data="tu_cryptobot")],
        [InlineKeyboardButton(text=L(uid, "btn_back"), callback_data="menu")],
        [InlineKeyboardButton(text=L(uid, "btn_menu"), callback_data="menu")],
    ])


def topup_paid_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid, "btn_paid"), callback_data="paid_topup")],
        [InlineKeyboardButton(text=L(uid, "btn_back"), callback_data="topup")],
        [InlineKeyboardButton(text=L(uid, "btn_menu"), callback_data="menu")],
    ])


def wd_method_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 TON",       callback_data="wd_TON"),
         InlineKeyboardButton(text="💵 USDT",      callback_data="wd_USDT")],
        [InlineKeyboardButton(text="⭐️ Звёзды",   callback_data="wd_Stars"),
         InlineKeyboardButton(text="💳 Карта",     callback_data="wd_Card")],
        [InlineKeyboardButton(text="🤖 CryptoBot", callback_data="wd_CryptoBot")],
        [InlineKeyboardButton(text=L(uid, "btn_back"), callback_data="menu")],
        [InlineKeyboardButton(text=L(uid, "btn_menu"), callback_data="menu")],
    ])


def ctry_kb(uid, prefix):
    rows = [[InlineKeyboardButton(text=label, callback_data=f"{prefix}_ctry_{code}")]
            for code, label in CARD_COUNTRIES]
    rows.append([InlineKeyboardButton(text=L(uid, "btn_cancel"), callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


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


# ── show menu ─────────────────────────────────────────────────────────────────

async def show_menu(message, uid):
    await del_prev(uid)
    banner = user_data.get("_banner")
    welcome = L(uid, "welcome")
    kb = main_kb(uid)
    if banner and banner.get("photo_id"):
        try:
            sent = await message.answer_photo(
                photo=banner["photo_id"],
                caption=banner.get("caption") or welcome,
                parse_mode="HTML", reply_markup=kb
            )
            get_user(uid)["banner_msg_id"] = sent.message_id
            return
        except Exception:
            pass
    sent = await message.answer(welcome, parse_mode="HTML", reply_markup=kb)
    get_user(uid)["banner_msg_id"] = sent.message_id


# ── /start ────────────────────────────────────────────────────────────────────

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
        deal = deals.get(deal_id)
        if not deal:
            await message.answer(L(uid, "deal_not_found"), reply_markup=main_kb(uid))
            return
        if deal["uid"] == uid:
            await message.answer(L(uid, "own_deal"), reply_markup=main_kb(uid))
            return
        buyer_name = f"@{message.from_user.username}" if message.from_user.username else f"ID:{uid}"
        cr = deal.get("creator_role", "seller")
        joiner_role = "buyer" if cr == "seller" else "seller"
        key = "deal_info_seller" if joiner_role == "seller" else "deal_info_buyer"

        # добавляем сделку в my_deals присоединившегося
        md = get_user(uid).get("my_deals", [])
        if deal_id not in md:
            md.append(deal_id)
            get_user(uid)["my_deals"] = md

        sent = await message.answer(
            L(uid, key, deal_id=deal_id, subject=deal.get("subject", "-"),
              description=deal["description"], amount=deal["amount"],
              payment=deal.get("payment", "-")),
            parse_mode="HTML", reply_markup=deal_kb(uid, deal_id)
        )
        get_user(uid)["banner_msg_id"] = sent.message_id

        creator_uid = deal["uid"]
        try:
            sent2 = await bot.send_message(
                creator_uid,
                L(creator_uid, "deal_notify",
                  deal_id=deal_id, buyer=buyer_name,
                  subject=deal.get("subject", "-"),
                  description=deal["description"],
                  amount=deal["amount"], payment=deal.get("payment", "-")),
                parse_mode="HTML", reply_markup=deal_kb(creator_uid, deal_id)
            )
            get_user(creator_uid)["banner_msg_id"] = sent2.message_id
        except Exception:
            pass
        return

    await show_menu(message, uid)


# ── neptune ───────────────────────────────────────────────────────────────────

@dp.message(Command("neptunteam"))
async def cmd_neptune(message: Message):
    uid = message.from_user.id
    u = get_user(uid)
    revs = u.get("reviews", [])
    rev_t = "\n".join(f"<b>- {r}</b>" for r in revs[-5:]) if revs else "<b>Нет</b>"
    await message.answer(
        f"<b>Neptune Panel\n\n"
        f"Баланс: {u['balance']}\n"
        f"Репутация: {u['reputation']}\n"
        f"Сделок: {u['deals_count']}\n"
        f"Оборот: {u['turnover']}$\n\n"
        f"Отзывы:\n{rev_t}\n\n"
        f"/neptune_add 100 — добавить баланс\n"
        f"/neptune_sub 50 — снять баланс</b>",
        parse_mode="HTML"
    )


@dp.message(Command("neptune_add"))
async def cmd_neptune_add(message: Message):
    uid = message.from_user.id
    get_user(uid)
    try:
        v = float(message.text.strip().split()[1])
        u = get_user(uid)
        u["balance"] = round(u["balance"] + v, 2)
        u["turnover"] = round(u["turnover"] + v, 2)
        await message.answer(f"<b>+{v} | Баланс: {u['balance']}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("<b>/neptune_add 100</b>", parse_mode="HTML")


@dp.message(Command("neptune_sub"))
async def cmd_neptune_sub(message: Message):
    uid = message.from_user.id
    get_user(uid)
    try:
        v = float(message.text.strip().split()[1])
        u = get_user(uid)
        u["balance"] = round(max(0.0, u["balance"] - v), 2)
        await message.answer(f"<b>-{v} | Баланс: {u['balance']}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("<b>/neptune_sub 50</b>", parse_mode="HTML")


# ── callbacks: menu, lang, security, cur_deals, my_deals ─────────────────────

@dp.callback_query(F.data == "menu")
async def cb_menu(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await state.clear()
    await safe_del(callback.message)
    await show_menu(callback.message, uid)
    await callback.answer()


@dp.callback_query(F.data == "language")
async def cb_lang(callback: CallbackQuery):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid, "lang_choose"), parse_mode="HTML", reply_markup=language_kb())
    await callback.answer()


@dp.callback_query(F.data.startswith("setlang_"))
async def cb_setlang(callback: CallbackQuery):
    uid = callback.from_user.id
    lang = callback.data.replace("setlang_", "")
    if lang not in LANGS:
        lang = "ru"
    get_user(uid)["lang"] = lang
    await safe_del(callback.message)
    await callback.message.answer(L(uid, "lang_set"), parse_mode="HTML")
    await show_menu(callback.message, uid)
    await callback.answer()


@dp.callback_query(F.data == "security")
async def cb_security(callback: CallbackQuery):
    uid = callback.from_user.id
    await safe_del(callback.message)
    sent = await callback.message.answer(
        L(uid, "security"), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=L(uid, "btn_why_safe"), url=SAFETY)],
            [InlineKeyboardButton(text=L(uid, "btn_back"),     callback_data="menu")],
            [InlineKeyboardButton(text=L(uid, "btn_menu"),     callback_data="menu")],
        ])
    )
    get_user(uid)["banner_msg_id"] = sent.message_id
    await callback.answer()


@dp.callback_query(F.data == "cur_deals")
async def cb_cur_deals(callback: CallbackQuery):
    uid = callback.from_user.id
    text = L(uid, "cur_title")
    pool = ["u***r", "a***x", "m***e", "s***n", "k***v", "d***o", "p***l", "t***s"]
    fake = random.sample(FAKE_DEALS, min(5, len(FAKE_DEALS)))
    for i, d in enumerate(fake, 1):
        b = random.choice(pool)
        s = random.choice([n for n in pool if n != b])
        text += L(uid, "cur_line", n=i, amount=d["amount"],
                  desc=d["desc"], b=f"@{b}", s=f"@{s}")
    await safe_del(callback.message)
    sent = await callback.message.answer(text, parse_mode="HTML", reply_markup=back_kb(uid))
    get_user(uid)["banner_msg_id"] = sent.message_id
    await callback.answer()


@dp.callback_query(F.data == "my_deals")
async def cb_my_deals(callback: CallbackQuery):
    uid = callback.from_user.id
    my = get_user(uid).get("my_deals", [])
    await safe_del(callback.message)
    if not my:
        await callback.message.answer(L(uid, "my_deals_empty"), parse_mode="HTML",
                                      reply_markup=back_kb(uid))
        await callback.answer()
        return
    text = L(uid, "my_deals_title")
    for did in my[-10:]:
        d = deals.get(did)
        if not d:
            continue
        if d["uid"] == uid:
            role = d.get("creator_role", "seller")
        else:
            cr = d.get("creator_role", "seller")
            role = "buyer" if cr == "seller" else "seller"
        ru = L(uid, "role_s") if role == "seller" else L(uid, "role_b")
        text += L(uid, "my_deal_line",
                  did=did, subject=d.get("subject", "-"),
                  desc=d.get("description", "-")[:30],
                  amount=d.get("amount", "-"), payment=d.get("payment", "-"),
                  role=ru, status=d.get("status", "active"))
    sent = await callback.message.answer(text, parse_mode="HTML", reply_markup=back_kb(uid))
    get_user(uid)["banner_msg_id"] = sent.message_id
    await callback.answer()


# ── DEAL FLOW ─────────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "deal")
async def cb_deal(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    if not has_any_req(uid):
        await safe_del(callback.message)
        await callback.message.answer(
            L(uid, "no_req_deal"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=L(uid, "btn_req"), callback_data="requisites")],
                [InlineKeyboardButton(text=L(uid, "btn_back"), callback_data="menu")],
            ])
        )
        await callback.answer()
        return
    await safe_del(callback.message)
    u = get_user(uid)
    if u.get("agreed"):
        await callback.message.answer(L(uid, "deal_s0"), parse_mode="HTML", reply_markup=role_kb(uid))
        await state.set_state(Deal.role)
        await callback.answer()
        return
    await callback.message.answer(L(uid, "agreement"), parse_mode="HTML", reply_markup=agree_kb(uid))
    await callback.answer()


@dp.callback_query(F.data == "confirm_agreement")
async def cb_confirm(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    get_user(uid)["agreed"] = True
    await safe_del(callback.message)
    await callback.message.answer(L(uid, "deal_s0"), parse_mode="HTML", reply_markup=role_kb(uid))
    await state.set_state(Deal.role)
    await callback.answer()


@dp.callback_query(F.data.startswith("drole_"), Deal.role)
async def cb_drole(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    role = "buyer" if callback.data == "drole_buyer" else "seller"
    await state.update_data(role=role)
    await safe_del(callback.message)
    await callback.message.answer(L(uid, "deal_s1"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(Deal.partner)
    await callback.answer()


@dp.message(Deal.partner)
async def deal_partner(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    t = message.text.strip()
    if not t.startswith("@") or len(t.lstrip("@")) < 4:
        await message.answer(L(uid, "err_uname2"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    await state.update_data(partner=t)
    await message.answer(L(uid, "deal_s2"), parse_mode="HTML", reply_markup=subject_kb(uid))
    await state.set_state(Deal.subject)


@dp.callback_query(F.data.startswith("dsubj_"), Deal.subject)
async def deal_subject(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    subj = callback.data.replace("dsubj_", "")
    await state.update_data(subject=subj)
    await safe_del(callback.message)
    await callback.message.answer(L(uid, "deal_s3"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(Deal.description)
    await callback.answer()


@dp.message(Deal.description)
async def deal_desc(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    if len(message.text.strip()) < 8:
        await message.answer(L(uid, "deal_s3_short"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    await state.update_data(description=message.text.strip())
    data = await state.get_data()
    role = data.get("role", "seller")
    key = "deal_s4_seller" if role == "seller" else "deal_s4_buyer"
    await message.answer(L(uid, key), parse_mode="HTML", reply_markup=payment_kb(uid))
    await state.set_state(Deal.payment)


@dp.callback_query(F.data.startswith("dpay_"), Deal.payment)
async def deal_payment(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    method = callback.data.replace("dpay_", "")
    if method != "CryptoBot" and not has_req(uid, method):
        await safe_del(callback.message)
        await state.update_data(payment=method, pending_req=method)
        await callback.message.answer(
            L(uid, "no_req_deal"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=L(uid, "btn_req"),
                                      callback_data=f"deal_req_{method}")],
                [InlineKeyboardButton(text=L(uid, "btn_cancel"), callback_data="menu")],
            ])
        )
        await callback.answer()
        return
    await state.update_data(payment=method)
    await safe_del(callback.message)
    await callback.message.answer(L(uid, "deal_s5"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(Deal.amount)
    await callback.answer()


@dp.callback_query(F.data.startswith("deal_req_"))
async def deal_req_inline(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    method = callback.data.replace("deal_req_", "")
    km = {"TON": ("enter_ton", AddReq.ton),
          "USDT": ("enter_usdt", AddReq.usdt),
          "Stars": ("enter_stars", AddReq.stars),
          "Card": ("enter_card", AddReq.card_num)}
    if method not in km:
        await callback.answer()
        return
    key, st = km[method]
    await safe_del(callback.message)
    await state.update_data(from_deal=True)
    await state.set_state(st)
    await callback.message.answer(L(uid, key), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await callback.answer()


@dp.message(Deal.amount)
async def deal_amount(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    v = valid_amount(message.text)
    if v is None:
        await message.answer(L(uid, "err_amount"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    data = await state.get_data()
    deal_id = gen_deal_id()
    role = data.get("role", "seller")
    deals[deal_id] = {
        "uid": uid, "partner": data.get("partner", "-"),
        "subject": data.get("subject", "-"),
        "description": data.get("description", "-"),
        "amount": message.text.strip(),
        "payment": data.get("payment", "-"),
        "creator_role": role, "status": "active"
    }
    u = get_user(uid)
    u["deals_count"] += 1
    md = u.get("my_deals", [])
    if deal_id not in md:
        md.append(deal_id)
        u["my_deals"] = md
    me = await bot.get_me()
    ru_role = L(uid, "role_s") if role == "seller" else L(uid, "role_b")
    sent = await message.answer(
        L(uid, "deal_created",
          deal_id=deal_id, partner=data.get("partner", "-"),
          subject=data.get("subject", "-"),
          description=data.get("description", "-"),
          amount=message.text.strip(),
          payment=data.get("payment", "-"),
          role=ru_role, bot_username=me.username),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=L(uid, "btn_manager"),
                                  url=f"https://t.me/{MANAGER.lstrip('@')}")],
            [InlineKeyboardButton(text=L(uid, "btn_menu"), callback_data="menu")],
        ])
    )
    get_user(uid)["banner_msg_id"] = sent.message_id
    uname = f"@{message.from_user.username}" if message.from_user.username else f"ID:{uid}"
    for adm in ADMIN_IDS:
        try:
            await bot.send_message(
                adm,
                f"<b>Новая сделка {deal_id}\n\n"
                f"Создатель: {uname} ({ru_role})\n"
                f"Партнёр: {data.get('partner', '-')}\n"
                f"Предмет: {data.get('subject', '-')}\n"
                f"Суть: {data.get('description', '-')}\n"
                f"Сумма: {message.text.strip()} | Оплата: {data.get('payment', '-')}</b>",
                parse_mode="HTML"
            )
        except Exception:
            pass
    await state.clear()


# ── paid ──────────────────────────────────────────────────────────────────────

@dp.callback_query(F.data.startswith("paid_"))
async def cb_paid(callback: CallbackQuery):
    uid = callback.from_user.id
    deal_id = callback.data.replace("paid_", "")
    uname = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{uid}"
    if deal_id == "topup":
        for adm in ADMIN_IDS:
            try:
                await bot.send_message(adm,
                    f"<b>Пополнение\nПользователь: {uname}</b>", parse_mode="HTML")
            except Exception:
                pass
        await callback.answer("Уведомление отправлено!", show_alert=True)
        await callback.message.answer(L(uid, "paid_ok"), parse_mode="HTML", reply_markup=back_kb(uid))
        return
    deal = deals.get(deal_id)
    if not deal:
        await callback.answer("Сделка не найдена", show_alert=True)
        return
    for adm in ADMIN_IDS:
        try:
            await bot.send_message(adm,
                L(adm, "paid_adm", deal_id=deal_id, user=uname,
                  amount=deal.get("amount", "-"), payment=deal.get("payment", "-")),
                parse_mode="HTML")
        except Exception:
            pass
    cr = deal.get("uid")
    if cr and cr != uid:
        try:
            await bot.send_message(cr, L(cr, "paid_seller", deal_id=deal_id), parse_mode="HTML")
        except Exception:
            pass
    await callback.answer("Уведомление отправлено!", show_alert=True)
    await callback.message.answer(L(uid, "paid_ok"), parse_mode="HTML", reply_markup=back_kb(uid))


# ── REQUISITES ────────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "requisites")
async def cb_req(callback: CallbackQuery):
    uid = callback.from_user.id
    u = get_user(uid)
    await safe_del(callback.message)
    sent = await callback.message.answer(
        L(uid, "req_title",
          ton=u.get("ton") or "-", usdt=u.get("usdt") or "-",
          stars=u.get("stars") or "-",
          card=u.get("card") or "-", cc=u.get("card_country", "")),
        parse_mode="HTML", reply_markup=req_kb(uid)
    )
    get_user(uid)["banner_msg_id"] = sent.message_id
    await callback.answer()


@dp.callback_query(F.data.in_({"req_ton", "req_usdt", "req_stars", "req_card"}))
async def cb_req_type(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    t = callback.data.replace("req_", "")
    km = {"ton": ("enter_ton", AddReq.ton),
          "usdt": ("enter_usdt", AddReq.usdt),
          "stars": ("enter_stars", AddReq.stars),
          "card": ("enter_card", AddReq.card_num)}
    key, st = km[t]
    await safe_del(callback.message)
    await callback.message.answer(L(uid, key), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(st)
    await callback.answer()


@dp.message(AddReq.ton)
async def save_ton(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    addr = message.text.strip()
    if not valid_ton(addr):
        await message.answer(L(uid, "err_ton"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    get_user(uid)["ton"] = addr
    data = await state.get_data()
    from_deal = data.get("from_deal")
    await state.clear()
    await message.answer(L(uid, "saved_ton"), parse_mode="HTML", reply_markup=main_kb(uid))
    if from_deal:
        await message.answer(L(uid, "deal_s5"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        await state.set_state(Deal.amount)


@dp.message(AddReq.usdt)
async def save_usdt(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    addr = message.text.strip()
    if not valid_usdt(addr):
        await message.answer(L(uid, "err_usdt"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    get_user(uid)["usdt"] = addr
    data = await state.get_data()
    from_deal = data.get("from_deal")
    await state.clear()
    await message.answer(L(uid, "saved_usdt"), parse_mode="HTML", reply_markup=main_kb(uid))
    if from_deal:
        await message.answer(L(uid, "deal_s5"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        await state.set_state(Deal.amount)


@dp.message(AddReq.stars)
async def save_stars(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    uname = message.text.strip()
    if not uname.startswith("@"):
        uname = "@" + uname
    if not valid_uname(uname.lstrip("@")):
        await message.answer(L(uid, "err_stars"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    get_user(uid)["stars"] = uname
    data = await state.get_data()
    from_deal = data.get("from_deal")
    await state.clear()
    await message.answer(L(uid, "saved_stars"), parse_mode="HTML", reply_markup=main_kb(uid))
    if from_deal:
        await message.answer(L(uid, "deal_s5"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        await state.set_state(Deal.amount)


@dp.message(AddReq.card_num)
async def save_card_num(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    num = message.text.strip()
    if not valid_card(num):
        await message.answer(L(uid, "err_card"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    await state.update_data(card_number=re.sub(r"[\s\-]", "", num))
    await message.answer(L(uid, "card_step2"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(AddReq.card_name)


@dp.message(AddReq.card_name)
async def save_card_name(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    await state.update_data(card_name=message.text.strip())
    await message.answer(L(uid, "enter_ctry"), parse_mode="HTML", reply_markup=ctry_kb(uid, "req"))
    await state.set_state(AddReq.card_country)


@dp.callback_query(F.data.startswith("req_ctry_"), AddReq.card_country)
async def save_card_ctry(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    country = callback.data.replace("req_ctry_", "")
    data = await state.get_data()
    from_deal = data.get("from_deal")
    get_user(uid).update({
        "card": data.get("card_number", ""),
        "card_name": data.get("card_name", ""),
        "card_country": country
    })
    await safe_del(callback.message)
    await state.clear()
    await callback.message.answer(L(uid, "saved_card"), parse_mode="HTML", reply_markup=main_kb(uid))
    if from_deal:
        await callback.message.answer(L(uid, "deal_s5"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        await state.set_state(Deal.amount)
    await callback.answer()


# ── TOPUP ─────────────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "topup")
async def cb_topup(callback: CallbackQuery):
    uid = callback.from_user.id
    await safe_del(callback.message)
    sent = await callback.message.answer(
        L(uid, "topup_choose"), parse_mode="HTML", reply_markup=topup_kb(uid))
    get_user(uid)["banner_msg_id"] = sent.message_id
    await callback.answer()


@dp.callback_query(F.data.startswith("tu_"))
async def cb_tu(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    method = callback.data.replace("tu_", "")
    await safe_del(callback.message)
    await callback.message.answer(L(uid, "topup_amount"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(TopUp.amount)
    await state.update_data(tu_method=method)
    await callback.answer()


@dp.message(TopUp.amount)
async def topup_amount(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    v = valid_amount(message.text)
    if v is None:
        await message.answer(L(uid, "err_amount"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    data = await state.get_data()
    method = data.get("tu_method", "ton")
    await state.clear()
    amt = str(int(v)) if v == int(v) else str(v)
    ml = method.lower()
    key_map = {
        "stars": "topup_stars", "ton": "topup_ton",
        "usdt": "topup_usdt", "card": "topup_card", "cryptobot": "topup_cb"
    }
    key = key_map.get(ml, "topup_ton")
    sent = await message.answer(
        L(uid, key).format(amount=amt), parse_mode="HTML", reply_markup=topup_paid_kb(uid))
    get_user(uid)["banner_msg_id"] = sent.message_id


# ── WITHDRAW ──────────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "withdraw")
async def cb_withdraw(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    balance = get_user(uid).get("balance", 0.0)
    await safe_del(callback.message)
    if balance <= 0:
        sent = await callback.message.answer(
            L(uid, "wd_zero"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=L(uid, "btn_menu"), callback_data="menu")],
            ])
        )
        get_user(uid)["banner_msg_id"] = sent.message_id
        await callback.answer()
        return
    await callback.message.answer(
        L(uid, "wd_choose", balance=balance),
        parse_mode="HTML", reply_markup=wd_method_kb(uid))
    await state.set_state(Withdraw.method)
    await callback.answer()


@dp.callback_query(F.data.startswith("wd_"), Withdraw.method)
async def cb_wd_method(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    method = callback.data.replace("wd_", "")
    balance = get_user(uid).get("balance", 0.0)
    if not has_wd_req(uid, method):
        await safe_del(callback.message)
        await callback.message.answer(
            L(uid, "wd_no_req", m=method), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=L(uid, "btn_add_wd_req"),
                                      callback_data=f"add_wdr_{method}")],
                [InlineKeyboardButton(text=L(uid, "btn_back"), callback_data="menu")],
            ])
        )
        await state.clear()
        await callback.answer()
        return
    await state.update_data(wd_method=method)
    await safe_del(callback.message)
    await callback.message.answer(
        L(uid, "wd_amount", balance=balance),
        parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(Withdraw.amount)
    await callback.answer()


@dp.message(Withdraw.amount)
async def wd_amount(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    v = valid_amount(message.text)
    balance = get_user(uid).get("balance", 0.0)
    if v is None:
        await message.answer(L(uid, "err_amount"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    if v > balance:
        await message.answer(L(uid, "wd_low", balance=balance),
                             parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    data = await state.get_data()
    method = data.get("wd_method", "TON")
    req = get_wd_str(uid, method)
    await state.update_data(wd_amount=v, wd_req=req)
    await message.answer(
        L(uid, "wd_confirm", m=method, req=req, amount=v), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=L(uid, "btn_confirm_wd"), callback_data="wd_confirm")],
            [InlineKeyboardButton(text=L(uid, "btn_cancel"),     callback_data="menu")],
        ])
    )


@dp.callback_query(F.data == "wd_confirm")
async def wd_confirm(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    data = await state.get_data()
    v = data.get("wd_amount", 0)
    method = data.get("wd_method", "TON")
    req = data.get("wd_req", "-")
    u = get_user(uid)
    u["balance"] = round(u["balance"] - v, 2)
    uname = f"@{callback.from_user.username}" if callback.from_user.username else f"ID:{uid}"
    for adm in ADMIN_IDS:
        try:
            await bot.send_message(adm,
                L(adm, "wd_adm", user=uname, amount=v, m=method, req=req),
                parse_mode="HTML")
        except Exception:
            pass
    await state.clear()
    await callback.answer("Заявка отправлена!", show_alert=True)
    await callback.message.answer(L(uid, "wd_done"), parse_mode="HTML", reply_markup=back_kb(uid))


# добавление реквизита для вывода
@dp.callback_query(F.data.startswith("add_wdr_"))
async def add_wdr(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    method = callback.data.replace("add_wdr_", "")
    km = {"TON": ("enter_ton", AddWdReq.ton),
          "USDT": ("enter_usdt", AddWdReq.usdt),
          "Stars": ("enter_stars", AddWdReq.stars),
          "Card": ("enter_card", AddWdReq.card_num),
          "CryptoBot": ("enter_cb", AddWdReq.cryptobot)}
    if method not in km:
        await callback.answer()
        return
    key, st = km[method]
    await safe_del(callback.message)
    await callback.message.answer(L(uid, key), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(st)
    await callback.answer()


@dp.message(AddWdReq.ton)
async def wdr_ton(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    addr = message.text.strip()
    if not valid_ton(addr):
        await message.answer(L(uid, "err_ton"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    get_user(uid)["wd_ton"] = addr
    await state.clear()
    await message.answer(L(uid, "saved_ton"), parse_mode="HTML", reply_markup=main_kb(uid))


@dp.message(AddWdReq.usdt)
async def wdr_usdt(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    addr = message.text.strip()
    if not valid_usdt(addr):
        await message.answer(L(uid, "err_usdt"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    get_user(uid)["wd_usdt"] = addr
    await state.clear()
    await message.answer(L(uid, "saved_usdt"), parse_mode="HTML", reply_markup=main_kb(uid))


@dp.message(AddWdReq.stars)
async def wdr_stars(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    uname = message.text.strip()
    if not uname.startswith("@"):
        uname = "@" + uname
    if not valid_uname(uname.lstrip("@")):
        await message.answer(L(uid, "err_stars"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    get_user(uid)["wd_stars"] = uname
    await state.clear()
    await message.answer(L(uid, "saved_stars"), parse_mode="HTML", reply_markup=main_kb(uid))


@dp.message(AddWdReq.card_num)
async def wdr_card_num(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    num = message.text.strip()
    if not valid_card(num):
        await message.answer(L(uid, "err_card"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    await state.update_data(wd_card=re.sub(r"[\s\-]", "", num))
    await message.answer(L(uid, "card_step2"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(AddWdReq.card_name)


@dp.message(AddWdReq.card_name)
async def wdr_card_name(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    await state.update_data(wd_card_name=message.text.strip())
    await message.answer(L(uid, "enter_ctry"), parse_mode="HTML", reply_markup=ctry_kb(uid, "wdr"))
    await state.set_state(AddWdReq.card_country)


@dp.callback_query(F.data.startswith("wdr_ctry_"), AddWdReq.card_country)
async def wdr_card_ctry(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    country = callback.data.replace("wdr_ctry_", "")
    data = await state.get_data()
    get_user(uid).update({
        "wd_card": data.get("wd_card", ""),
        "wd_card_name": data.get("wd_card_name", ""),
        "wd_card_country": country
    })
    await safe_del(callback.message)
    await state.clear()
    await callback.message.answer(L(uid, "saved_card"), parse_mode="HTML", reply_markup=main_kb(uid))
    await callback.answer()


@dp.message(AddWdReq.cryptobot)
async def wdr_cb(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    uname = message.text.strip()
    if not uname.startswith("@"):
        uname = "@" + uname
    if not valid_uname(uname.lstrip("@")):
        await message.answer(L(uid, "err_uname"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    get_user(uid)["wd_cryptobot"] = uname
    await state.clear()
    await message.answer(L(uid, "saved_cb"), parse_mode="HTML", reply_markup=main_kb(uid))


# ── ADMIN ─────────────────────────────────────────────────────────────────────

@dp.message(Command("adm"))
async def cmd_adm(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        return
    total = len([k for k in user_data if not str(k).startswith("_")])
    await message.answer(
        f"<b>Админ-панель\n\nПользователей: {total}\nСделок: {len(deals)}</b>",
        parse_mode="HTML", reply_markup=admin_kb())


@dp.callback_query(F.data == "adm_banner")
async def adm_banner(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await safe_del(callback.message)
    await callback.message.answer(
        "<b>Отправьте фото + подпись для баннера.\n"
        "Баннер показывается везде, предыдущее меню удаляется.</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="adm_cancel")]
        ]))
    await state.set_state(SetBanner.waiting)
    await callback.answer()


@dp.message(SetBanner.waiting, F.photo)
async def save_banner(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    user_data["_banner"] = {
        "photo_id": message.photo[-1].file_id,
        "caption": message.caption or ""
    }
    await safe_del(message)
    await message.answer("<b>Баннер обновлён!</b>", parse_mode="HTML", reply_markup=admin_kb())
    await state.clear()


@dp.callback_query(F.data == "adm_stats")
async def adm_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    total = len([k for k in user_data if not str(k).startswith("_")])
    active = len([d for d in deals.values() if d.get("status") == "active"])
    tv = sum(v.get("turnover", 0.0) for k, v in user_data.items()
             if not str(k).startswith("_") and isinstance(v, dict))
    await callback.message.answer(
        f"<b>Статистика\n\nПользователей: {total}\n"
        f"Сделок: {len(deals)}\nАктивных: {active}\nОборот: {tv}$</b>",
        parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "adm_users")
async def adm_users(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    ulist = [k for k in user_data if not str(k).startswith("_")]
    text = f"<b>Пользователи ({len(ulist)})</b>\n\n"
    for uid in ulist[:20]:
        u = user_data[uid]
        if not isinstance(u, dict):
            continue
        text += (f"<b><code>{uid}</code> rep:{u.get('reputation', 0)} "
                 f"deals:{u.get('deals_count', 0)} "
                 f"bal:{u.get('balance', 0.0)} "
                 f"{u.get('lang', 'ru')}</b>\n")
    if len(ulist) > 20:
        text += f"<b>...ещё {len(ulist) - 20}</b>"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "adm_reputation")
async def adm_rep(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await callback.message.answer(
        "<b>Репутация\nФормат: @username +5</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="adm_cancel")]
        ]))
    await state.set_state(AdminAction.reputation)
    await callback.answer()


@dp.message(AdminAction.reputation)
async def process_rep(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.strip().split()
        uid = find_uid(parts[0])
        if uid is None:
            await message.answer("<b>Не найден.</b>", parse_mode="HTML")
            await state.clear()
            return
        delta = int(parts[1])
        u = get_user(uid)
        u["reputation"] = u.get("reputation", 0) + delta
        await message.answer(
            f"<b>{uid}: {delta:+} | Итого: {u['reputation']}</b>", parse_mode="HTML")
        await bot.send_message(uid,
            f"<b>Репутация: {delta:+} | Текущая: {u['reputation']}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("<b>Ошибка. Формат: @username +5</b>", parse_mode="HTML")
    await state.clear()


@dp.callback_query(F.data == "adm_review")
async def adm_review(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await callback.message.answer(
        "<b>Отзыв\nФормат: @username Текст</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="adm_cancel")]
        ]))
    await state.set_state(AdminAction.review)
    await callback.answer()


@dp.message(AdminAction.review)
async def process_review(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.strip().split(maxsplit=1)
        uid = find_uid(parts[0])
        if uid is None:
            await message.answer("<b>Не найден.</b>", parse_mode="HTML")
            await state.clear()
            return
        get_user(uid).setdefault("reviews", []).append(parts[1])
        await message.answer(f"<b>Отзыв добавлен {uid}</b>", parse_mode="HTML")
        await bot.send_message(uid,
            f"<b>Новый отзыв:\n\n{parts[1]}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("<b>Ошибка.</b>", parse_mode="HTML")
    await state.clear()


@dp.callback_query(F.data == "adm_balance")
async def adm_bal(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS:
        return
    await callback.message.answer(
        "<b>Баланс\nФормат: @username 150.5</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="adm_cancel")]
        ]))
    await state.set_state(AdminAction.balance)
    await callback.answer()


@dp.message(AdminAction.balance)
async def process_bal(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS:
        return
    try:
        parts = message.text.strip().split()
        uid = find_uid(parts[0])
        if uid is None:
            await message.answer("<b>Не найден.</b>", parse_mode="HTML")
            await state.clear()
            return
        amt = float(parts[1])
        u = get_user(uid)
        old = u.get("balance", 0)
        u["balance"] = amt
        await message.answer(f"<b>{uid}: {old} → {amt}</b>", parse_mode="HTML")
        await bot.send_message(uid, f"<b>Баланс: {amt}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("<b>Ошибка.</b>", parse_mode="HTML")
    await state.clear()


@dp.callback_query(F.data == "adm_deals")
async def adm_deals_cb(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS:
        return
    if not deals:
        await callback.message.answer("<b>Сделок нет.</b>", parse_mode="HTML")
        await callback.answer()
        return
    text = f"<b>Сделки ({len(deals)})</b>\n\n"
    for did, d in list(deals.items())[-10:]:
        text += (f"<b><code>{did}</code> | {d['uid']} | {d.get('partner', '-')}\n"
                 f"{d.get('amount', '-')} {d.get('payment', '-')} | "
                 f"{d.get('description', '-')[:25]}\n"
                 f"Статус: {d.get('status', '-')}</b>\n\n")
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()


@dp.callback_query(F.data == "adm_cancel")
async def adm_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.answer("<b>Отменено.</b>", parse_mode="HTML", reply_markup=admin_kb())
    await callback.answer()


# ── run ───────────────────────────────────────────────────────────────────────

async def set_commands():
    await bot.set_my_commands([
        BotCommand(command="start", description="Главное меню / Main menu"),
    ])


async def main():
    await set_commands()
    print("Bot started!")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
