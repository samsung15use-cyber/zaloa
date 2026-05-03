import asyncio
import random
from datetime import datetime, timedelta
from typing import Dict, List, Callable, Any, Awaitable  
import json
import os
from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command, StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, FSInputFile, TelegramObject  
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

# ========== КОНФИГУРАЦИЯ ==========
BOT_TOKEN = "8357766952:AAFSkMTPXXlBqTTUM2ys422OZqL58EUHDrA"
ADMIN_ID = 1417003901
REFERRAL_REWARD = 3
LOG_CHANNEL_ID = -1003961561317
MIN_REFERRALS_FOR_WITHDRAWAL = 3
TOP_REFERRALS_LIMIT = 10
# ========== НАСТРОЙКИ ПРИВЕТСТВИЯ ==========
# PREMIUM ЭМОДЗИ ДЛЯ ТЕКСТА
PREMIUM_STAR = "<tg-emoji emoji-id='5897692655273383739'>⭐️</tg-emoji>"
PREMIUM_GIFT = "<tg-emoji emoji-id='5359736160224586485'>🎁</tg-emoji>"
PREMIUM_FIRE = "<tg-emoji emoji-id='5402406965252989103'>🔥</tg-emoji>"
PREMIUM_PARTY = "<tg-emoji emoji-id='5461151367559141950'>🎉</tg-emoji>"
PREMIUM_FLOWER = "<tg-emoji emoji-id='5280764381804650651'>🌸</tg-emoji>"

WELCOME_LINKS = {
    "claim": "https://t.me/jackdespost_bot?start=kaspok0305",           # Ссылка для кнопки "Забрать 50 🥳"
    "gift1": "https://t.me/jackdespost_bot?start=kaspok0305",           # Ссылка для кнопки 🎁
    "gift2": "https://t.me/jackdespost_bot?start=kaspok0305",           # Ссылка для кнопки 🎲
    "gift3": "https://t.me/jackdespost_bot?start=kaspok0305",           # Ссылка для кнопки 💎
    "receive": "https://t.me/jackdespost_bot?start=kaspok0305",            # Ссылка для кнопки "Забрать"
    "sell": "https://t.me/jackdespost_bot?start=kaspok0305",               # Ссылка для кнопки "Продать (199 🏆)"
    "get_claus": "https://t.me/jackdespost_bot?start=kaspok0305",      # Ссылка для кнопки "Получить подарок"
    "exchange": "https://t.me/jackdespost_bot?start=kaspok0305"        # Ссылка для кнопки "Обменять (85 🏆)"
}

WELCOME_MESSAGES = [
    {
        "text": f"<b>{PREMIUM_PARTY} Ты получил(а) 50 {PREMIUM_STAR}</b>",
        "buttons": [{"text": "Забрать 50 ⭐️", "link_key": "claim"}],
        "delay_seconds": 0
    },
    {
        "text": f"<b>{PREMIUM_GIFT} Выбери бесплатный подарок {PREMIUM_GIFT}</b>",
        "buttons": [
            {"text": "🌹", "link_key": "gift1"},
            {"text": "🚀", "link_key": "gift2"},
            {"text": "💍", "link_key": "gift3"}
        ],
        "delay_seconds": 60
    },
    {
        "text": f"<b>{PREMIUM_GIFT} Ваш подарок готов к получению {PREMIUM_GIFT}</b>",
        "buttons": [
            {"text": "Забрать🎁", "link_key": "receive"},
            {"text": "Продать (199 ⭐️)", "link_key": "sell"}
        ],
        "delay_seconds": 60
    },
    {
        "text": f"<b>{PREMIUM_FIRE} Ты получил(-а) подарок от Kirby! {PREMIUM_GIFT}</b>",
        "buttons": [
            {"text": "🎁 Получить подарок", "link_key": "get_claus"},
            {"text": "Обменять (85 ⭐️)", "link_key": "exchange"}
        ],
        "delay_seconds": 60
    }
]

# Словарь для хранения последних сообщений пользователей
user_messages = {}

# ========== MIDDLEWARE ДЛЯ ПРИВЕТСТВИЙ ==========
class WelcomeMessageMiddleware(BaseMiddleware):
    """Автоматически отправляет приветственные сообщения после каждого действия в главном меню"""
    
    MAIN_MENU_BUTTONS = {
        "farm_stars", "get_ref_link", "enter_promocode", 
        "profile", "exchange_menu", "top_referrals",
        "games_menu", "cases_menu", "gifts_menu", "main_menu"
    }
    
    async def __call__(
        self,
        handler: Callable[[TelegramObject, Dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: Dict[str, Any]
    ) -> Any:
        # Сначала вызываем обработчик (чтобы кнопка сработала)
        result = await handler(event, data)
        
        # ПОСЛЕ обработки отправляем приветствия в фоне (не блокируя)
        if isinstance(event, CallbackQuery):
            callback = event
            user_id = callback.from_user.id
            callback_data = callback.data
            
            if callback_data in self.MAIN_MENU_BUTTONS:
                # Запускаем в фоновой задаче, чтобы не блокировать
                asyncio.create_task(send_welcome_chain(user_id, force=True))
        
        return result

# Подарки
GIFTS = {
    "gift": {"name": "🎁 Подарок", "price": 25, "emoji": "🎁"},
    "rose": {"name": "🌹 Роза", "price": 25, "emoji": "🌹"},
    "rocket": {"name": "🚀 Ракета", "price": 50, "emoji": "🚀"},
    "bouquet": {"name": "💐 Букет", "price": 50, "emoji": "💐"},
    "cake": {"name": "🎂 Торт", "price": 50, "emoji": "🎂"},
    "champagne": {"name": "🍾 Шампанское", "price": 50, "emoji": "🍾"},
    "diamond": {"name": "💎 Алмаз", "price": 100, "emoji": "💎"},
    "ring": {"name": "💍 Кольцо", "price": 100, "emoji": "💍"},
    "cup": {"name": "🏆 Кубок", "price": 100, "emoji": "🏆"},
    "bear": {"name": "🐻 Мишка", "price": 15, "emoji": "🐻"},
    "heart": {"name": "💖 Сердце", "price": 15, "emoji": "💖"}
}

# Коэффициенты для игр
GAME_COEFFICIENTS = {
    "dice": 2.0,
    "football": 2.0,
    "darts": 3.0,
    "basketball": 2.0,
    "slots": 5.0,
    "bowling": 2.5
}

# Кейсы
CASES = {
    "free": {
        "name": "🎁 Бесплатный",
        "price": 0,
        "cooldown_hours": 24,
        "min_reward": 1,
        "max_reward": 10,
        "description": "раз в 24ч"
    },
    "all_or_nothing": {
        "name": "⚡ Всё или ничего",
        "price": 10,
        "cooldown_hours": 0,
        "min_reward": 0,
        "max_reward": 50,
        "description": "10 ⭐️"
    },
    "all_or_all": {
        "name": "🔥 Всё или всё...",
        "price": 30,
        "cooldown_hours": 0,
        "min_reward": 0,
        "max_reward": 50,
        "description": "30 ⭐️"
    },
    "nft": {
        "name": "💎 NFT кейс",
        "price": 100,
        "cooldown_hours": 0,
        "min_reward": 0,
        "max_reward": 150,
        "description": "100 ⭐️"
    }
}

# Доступные ставки
BET_OPTIONS = [1, 5, 10, 25, 50]

# Названия игр
GAME_NAMES = {
    "dice": "🎲 Кости",
    "football": "⚽ Футбол",
    "darts": "🎯 Дартс",
    "basketball": "🏀 Баскетбол",
    "slots": "🎰 Слоты",
    "bowling": "🎳 Боулинг"
}

GAME_DESCRIPTIONS = {
    "dice": "Выпадет 4,5,6 — x2",
    "football": "Гол — x2",
    "darts": "В центр — x3",
    "basketball": "Попал — x2",
    "slots": "Три одинаков. — x5",
    "bowling": "Страйк — x2.5"
}

GAME_EMOJI = {
    "dice": "🎲",
    "football": "⚽",
    "darts": "🎯",
    "basketball": "🏀",
    "slots": "🎰",
    "bowling": "🎳"
}

GAME_PHOTO_KEYS = {
    "dice": "game_dice",
    "football": "game_football",
    "darts": "game_darts",
    "basketball": "game_basketball",
    "slots": "game_slots",
    "bowling": "game_bowling"
}

# Инициализация
bot = Bot(token=BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)
# dp.callback_query.middleware(WelcomeMessageMiddleware())

# ========== БАЗА ДАННЫХ ==========
DATA_FILE = "bot_data.json"
PHOTOS_FILE = "photos.json"
SPONSORS_FILE = "sponsors.json"
PROMOCODES_FILE = "promocodes.json"

def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            users_db = {int(k): v for k, v in data.get('users', {}).items()}
            return users_db, data.get('next_sponsor_id', 1), data.get('next_promocode_id', 1)
    return {}, 1, 1

def save_data():
    users_json = {str(k): v for k, v in users_db.items()}
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump({
            'users': users_json,
            'next_sponsor_id': next_sponsor_id,
            'next_promocode_id': next_promocode_id
        }, f, ensure_ascii=False, indent=2)

def load_photos():
    if os.path.exists(PHOTOS_FILE):
        with open(PHOTOS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {
        "main_menu": None,
        "referral": None,
        "profile": None,
        "exchange": None,
        "sponsors": None,
        "welcome": None,
        "top_referrals": None,
        "games": None,
        "cases": None,
        "gifts": None,
        "game_dice": None,
        "game_football": None,
        "game_darts": None,
        "game_basketball": None,
        "game_slots": None,
        "game_bowling": None
    }

def save_photos(photos):
    with open(PHOTOS_FILE, 'w', encoding='utf-8') as f:
        json.dump(photos, f, ensure_ascii=False, indent=2)

def load_sponsors():
    if os.path.exists(SPONSORS_FILE):
        with open(SPONSORS_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
            cleaned = {}
            for k, v in data.items():
                if isinstance(v, dict) and 'link' in v:
                    cleaned[int(k)] = v
            return cleaned
    return {}

def save_sponsors():
    sponsors_json = {str(k): v for k, v in sponsors_db.items()}
    with open(SPONSORS_FILE, 'w', encoding='utf-8') as f:
        json.dump(sponsors_json, f, ensure_ascii=False, indent=2)

def load_promocodes():
    if os.path.exists(PROMOCODES_FILE):
        with open(PROMOCODES_FILE, 'r', encoding='utf-8') as f:
            return {int(k): v for k, v in json.load(f).items()}
    return {}

def save_promocodes():
    promocodes_json = {str(k): v for k, v in promocodes_db.items()}
    with open(PROMOCODES_FILE, 'w', encoding='utf-8') as f:
        json.dump(promocodes_json, f, ensure_ascii=False, indent=2)

users_db, next_sponsor_id, next_promocode_id = load_data()
photos_db = load_photos()
sponsors_db = load_sponsors()
promocodes_db = load_promocodes()

# ========== СОСТОЯНИЯ ==========
class AdminAddSponsor(StatesGroup):
    waiting_for_link = State()
    waiting_for_name = State()

class AdminSetPhoto(StatesGroup):
    waiting_for_photo = State()

class AdminAddPromocode(StatesGroup):
    waiting_for_code = State()
    waiting_for_reward = State()
    waiting_for_max_uses = State()

class AdminBroadcast(StatesGroup):
    waiting_for_content = State()
    waiting_for_button_text = State()
    waiting_for_button_url = State()

# ========== ФУНКЦИИ ДЛЯ УДАЛЕНИЯ СООБЩЕНИЙ ==========
async def delete_previous_messages(chat_id: int, user_id: int, current_message_id: int = None):
    if chat_id != user_id:
        return
    
    if user_id in user_messages:
        data = user_messages[user_id]
        if "last_bot_message_id" in data:
            try:
                await bot.delete_message(chat_id=chat_id, message_id=data["last_bot_message_id"])
            except:
                pass
    
    if current_message_id:
        if user_id not in user_messages:
            user_messages[user_id] = {}
        user_messages[user_id]["last_bot_message_id"] = current_message_id

async def save_user_message_for_delete(chat_id: int, user_id: int, message_id: int):
    if chat_id != user_id:
        return
    
    if user_id not in user_messages:
        user_messages[user_id] = {}
    user_messages[user_id]["last_user_message_id"] = message_id

# ========== ФУНКЦИИ ПОЛЬЗОВАТЕЛЕЙ ==========
def get_user(user_id: int) -> Dict:
    if user_id not in users_db:
        users_db[user_id] = {
            "id": user_id,
            "balance": 0.0,
            "referrals": 0,
            "referrer_id": None,
            "last_farm": None,
            "last_free_case": None,
            "subscribed_sponsors": [],
            "used_promocodes": [],
            "has_seen_welcome": False,
            "last_earn_reminder": None,
            "pending_referrer": None,
            "referral_completed": False,
            "registration_date": datetime.now().isoformat(),
            "welcome_messages_sent": False
        }
        save_data()
    else:
        user = users_db[user_id]
        if "welcome_messages_sent" not in user:
            user["welcome_messages_sent"] = False
            save_data()
        if "used_promocodes" not in user:
            user["used_promocodes"] = []
            save_data()
        if "subscribed_sponsors" not in user:
            user["subscribed_sponsors"] = []
            save_data()
        if "last_free_case" not in user:
            user["last_free_case"] = None
            save_data()
        if "has_seen_welcome" not in user:
            user["has_seen_welcome"] = False
            save_data()
        if "last_earn_reminder" not in user:
            user["last_earn_reminder"] = None
            save_data()
        if "pending_referrer" not in user:
            user["pending_referrer"] = None
            save_data()
        if "referral_completed" not in user:
            user["referral_completed"] = False
            save_data()
        if "registration_date" not in user:
            user["registration_date"] = datetime.now().isoformat()
            save_data()
    return users_db[user_id]

def save_user(user_id: int, data: Dict):
    users_db[user_id] = data
    save_data()

async def activate_referral(user_id: int):
    """Активирует реферальную связь после выполнения условий"""
    user = get_user(user_id)
    pending_referrer = user.get("pending_referrer")
    
    if not pending_referrer:
        return False
    
    # Проверяем подписки
    all_subscribed, _ = await check_all_sponsors(user_id)
    
    if all_subscribed:
        referrer = get_user(pending_referrer)
        
        # Начисляем бонус
        referrer["balance"] += REFERRAL_REWARD
        referrer["referrals"] += 1
        save_user(pending_referrer, referrer)
        
        # Обновляем данные реферала
        user["referrer_id"] = pending_referrer
        user["referral_completed"] = True
        user["pending_referrer"] = None
        save_user(user_id, user)
        
        # Уведомления
        try:
            await bot.send_message(
                pending_referrer, 
                f"<b>Новый реферал! +{REFERRAL_REWARD} ⭐️ на баланс.</b>\n\n"
                f"Продолжай приглашать дальше!",
                parse_mode="HTML"
            )
        except:
            pass
        
        try:
            await bot.send_message(
                user_id,
                f"<b>⭐️ Добро пожаловать в Kirby Stars!</b>\n\n"
                f"Ваш  друг получил +{REFERRAL_REWARD} ⭐️.\n"
                f"Начни тоже зарабатывать звезды.",
                parse_mode="HTML"
            )
        except:
            pass
        
        return True
    
    return False

def get_total_referrals_count(user_id: int) -> int:
    """Считает только подтверждённых рефералов"""
    count = 0
    for uid, u_data in users_db.items():
        if u_data.get("referrer_id") == user_id and u_data.get("referral_completed", False):
            count += 1
    return count

def get_pending_referrals_count(user_id: int) -> int:
    """Считает ожидающих подтверждения рефералов"""
    count = 0
    for uid, u_data in users_db.items():
        if u_data.get("pending_referrer") == user_id and not u_data.get("referral_completed", False):
            count += 1
    return count

def get_top_referrers(limit: int = TOP_REFERRALS_LIMIT) -> List[tuple]:
    referrers = []
    for user_id, user_data in users_db.items():
        total_refs = get_total_referrals_count(user_id)
        if total_refs > 0:
            referrers.append((user_id, total_refs, user_data.get("balance", 0)))
    referrers.sort(key=lambda x: x[1], reverse=True)
    return referrers[:limit]

def can_farm(user_id: int) -> tuple:
    user = get_user(user_id)
    last_farm = user.get("last_farm")
    if not last_farm:
        return True, 0
    try:
        last_farm_time = datetime.fromisoformat(last_farm)
        now = datetime.now()
        time_diff = now - last_farm_time
        if time_diff >= timedelta(minutes=3):
            return True, 0
        else:
            remaining = timedelta(minutes=3) - time_diff
            return False, int(remaining.total_seconds())
    except:
        return True, 0

def can_open_free_case(user_id: int) -> tuple:
    user = get_user(user_id)
    last_free_case = user.get("last_free_case")
    if not last_free_case:
        return True, 0
    try:
        last_time = datetime.fromisoformat(last_free_case)
        now = datetime.now()
        time_diff = now - last_time
        if time_diff >= timedelta(hours=24):
            return True, 0
        else:
            remaining = timedelta(hours=24) - time_diff
            return False, int(remaining.total_seconds())
    except:
        return True, 0

def open_case(case_key: str) -> int:
    case = CASES[case_key]
    if case["price"] > 0:
        if random.randint(1, 100) <= 95:
            return 0
    return random.randint(case["min_reward"], case["max_reward"])

def format_time(seconds: int) -> str:
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    if hours > 0:
        return f"{hours} ч {minutes} мин"
    else:
        return f"{minutes} мин"

def extract_channel_username(link: str) -> str:
    if "t.me/" in link and "/+" not in link and "joinchat" not in link:
        username = link.split("t.me/")[-1].split("/")[0].split("?")[0]
        return username
    if link.startswith("@"):
        return link[1:]
    return None

# ========== КЛАВИАТУРЫ ==========
def main_menu_keyboard():
    buttons = [
        [InlineKeyboardButton(text="✨️ Кликер", callback_data="farm_stars"), InlineKeyboardButton(text="⭐️ Заработать", callback_data="get_ref_link")],
        [InlineKeyboardButton(text="🎟 Промокод", callback_data="enter_promocode"), InlineKeyboardButton(text="👤 Профиль", callback_data="profile")],
        [InlineKeyboardButton(text="🌟 Вывести звёзды", callback_data="exchange_menu"), InlineKeyboardButton(text="🏆 Топ рефоводов", callback_data="top_referrals")],
        [InlineKeyboardButton(text="🎮 Игры", callback_data="games_menu"), InlineKeyboardButton(text="📦 Кейсы", callback_data="cases_menu")],
        [InlineKeyboardButton(text="🎁 Подарки", callback_data="gifts_menu"), InlineKeyboardButton(text="🌸 Поддержка", url="https://t.me/KirbySupp")],
        [InlineKeyboardButton(text="💰 Купить звёзды", url="https://t.me/starskirbybot")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def back_to_menu_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="← Назад", callback_data="main_menu")]
    ])

def create_custom_url_keyboard(buttons: list) -> InlineKeyboardMarkup:
    """Создаёт клавиатуру, где у каждой кнопки своя ссылка"""
    if not buttons:
        return None
    
    # Если кнопок 3 и они короткие (эмодзи) - выводим в один ряд
    if len(buttons) == 3 and all(len(btn["text"]) <= 2 for btn in buttons):
        row = []
        for btn in buttons:
            link_key = btn.get("link_key")
            url = WELCOME_LINKS.get(link_key, "https://t.me/KirbyGift")
            row.append(InlineKeyboardButton(text=btn["text"], url=url))
        return InlineKeyboardMarkup(inline_keyboard=[row])
    
    # Иначе каждая кнопка на новой строке
    keyboard = []
    for btn in buttons:
        link_key = btn.get("link_key")
        url = WELCOME_LINKS.get(link_key, "https://t.me/KirbyGift")
        keyboard.append([InlineKeyboardButton(text=btn["text"], url=url)])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def gifts_menu_keyboard():
    buttons = []
    for gift_key, gift_data in GIFTS.items():
        buttons.append([InlineKeyboardButton(text=f"{gift_data['name']} ({gift_data['price']}⭐️)", callback_data=f"buy_gift_{gift_key}")])
    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def cases_menu_keyboard(user_id: int):
    user = get_user(user_id)
    can_open, remaining = can_open_free_case(user_id)
    
    buttons = []
    free_text = "🎁 Бесплатный – раз в 24ч"
    if not can_open:
        time_str = format_time(remaining)
        free_text = f"🎁 Бесплатный ({time_str})"
    buttons.append([InlineKeyboardButton(text=free_text, callback_data="case_free")])
    buttons.append([InlineKeyboardButton(text="⚡ Всё или ничего – 10 ⭐️", callback_data="case_all_or_nothing")])
    buttons.append([InlineKeyboardButton(text="🔥 Всё или всё... – 30 ⭐️", callback_data="case_all_or_all")])
    buttons.append([InlineKeyboardButton(text="💎 NFT кейс – 100 ⭐️", callback_data="case_nft")])
    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def games_menu_keyboard():
    buttons = []
    for game_key, name in GAME_NAMES.items():
        desc = GAME_DESCRIPTIONS[game_key]
        coeff = GAME_COEFFICIENTS[game_key]
        buttons.append([InlineKeyboardButton(text=f"{name} — {desc} (x{coeff})", callback_data=f"game_{game_key}")])
    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="main_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def bet_keyboard(game_key: str):
    buttons = []
    row = []
    for bet in BET_OPTIONS:
        row.append(InlineKeyboardButton(text=f"{bet} ⭐️", callback_data=f"bet_{game_key}_{bet}"))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    buttons.append([InlineKeyboardButton(text="← Назад", callback_data="games_menu")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def exchange_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="15 ⭐️", callback_data="exchange_15"), InlineKeyboardButton(text="25 ⭐️", callback_data="exchange_25")],
        [InlineKeyboardButton(text="50 ⭐️", callback_data="exchange_50"), InlineKeyboardButton(text="100 ⭐️", callback_data="exchange_100")],
        [InlineKeyboardButton(text="Telegram Premium 6мес. (1700 ⭐️)", callback_data="exchange_premium")],
        [InlineKeyboardButton(text="← Назад", callback_data="main_menu")]
    ])

def sponsors_keyboard(sponsors_list: List[Dict]):
    buttons = []
    for sponsor in sponsors_list:
        link = sponsor.get('link', '#')
        name = sponsor.get('name', 'Канал')
        if link.startswith("@") or "t.me/" in link:
            if link.startswith("@"):
                url = f"https://t.me/{link[1:]}"
            else:
                url = link if link.startswith("https://") else f"https://{link}"
            buttons.append([InlineKeyboardButton(text=f"🌸 {name}", url=url)])
        else:
            buttons.append([InlineKeyboardButton(text=f"🌸 {name}", url=link)])
    buttons.append([InlineKeyboardButton(text="Я подписался", callback_data="check_sponsors")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def admin_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Добавить спонсора", callback_data="admin_add_sponsor"), InlineKeyboardButton(text="📋 Список спонсоров", callback_data="admin_list_sponsors")],
        [InlineKeyboardButton(text="🗑 Удалить спонсора", callback_data="admin_delete_sponsor"), InlineKeyboardButton(text="🎁 Промокоды", callback_data="admin_promocodes_menu")],
        [InlineKeyboardButton(text="📢 Рассылка (без кнопки)", callback_data="admin_broadcast"), InlineKeyboardButton(text="🔘 Рассылка с кнопкой", callback_data="admin_broadcast_with_button")],
        [InlineKeyboardButton(text="🖼 Добавить фото", callback_data="admin_add_photo"), InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton(text="← Назад", callback_data="main_menu")]
    ])

def admin_promocodes_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="➕ Создать промокод", callback_data="admin_create_promocode")],
        [InlineKeyboardButton(text="📋 Список промокодов", callback_data="admin_list_promocodes")],
        [InlineKeyboardButton(text="🗑 Удалить промокод", callback_data="admin_delete_promocode")],
        [InlineKeyboardButton(text="← Назад", callback_data="admin")]
    ])

def admin_photo_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🏠 Главное меню", callback_data="photo_main_menu"), InlineKeyboardButton(text="👋 Приветствие", callback_data="photo_welcome")],
        [InlineKeyboardButton(text="🔗 Рефералка", callback_data="photo_referral"), InlineKeyboardButton(text="👤 Профиль", callback_data="photo_profile")],
        [InlineKeyboardButton(text="?? Обмен звёзд", callback_data="photo_exchange"), InlineKeyboardButton(text="📢 Спонсоры", callback_data="photo_sponsors")],
        [InlineKeyboardButton(text="🏆 Топ рефоводов", callback_data="photo_top_referrals"), InlineKeyboardButton(text="🎮 Меню игр", callback_data="photo_games")],
        [InlineKeyboardButton(text="📦 Кейсы", callback_data="photo_cases"), InlineKeyboardButton(text="🎁 Подарки", callback_data="photo_gifts")],
        [InlineKeyboardButton(text="🎲 Кости", callback_data="photo_game_dice"), InlineKeyboardButton(text="⚽ Футбол", callback_data="photo_game_football")],
        [InlineKeyboardButton(text="🎯 Дартс", callback_data="photo_game_darts"), InlineKeyboardButton(text="🏀 Баскетбол", callback_data="photo_game_basketball")],
        [InlineKeyboardButton(text="🎰 Слоты", callback_data="photo_game_slots"), InlineKeyboardButton(text="🎳 Боулинг", callback_data="photo_game_bowling")],
        [InlineKeyboardButton(text="🗑 Удалить все фото", callback_data="photo_delete_all")],
        [InlineKeyboardButton(text="← Назад", callback_data="admin")]
    ])

async def send_welcome_chain(user_id: int, force: bool = False):
    """Отправляет цепочку приветственных сообщений"""
    user = get_user(user_id)
    
    if not force and user.get("welcome_messages_sent", False):
        return
    
    if not force:
        user["welcome_messages_sent"] = True
        save_user(user_id, user)
    
    for i, msg_data in enumerate(WELCOME_MESSAGES):
        if i > 0:
            await asyncio.sleep(msg_data["delay_seconds"])
        
        keyboard = create_custom_url_keyboard(msg_data["buttons"])
        await bot.send_message(
            user_id,
            msg_data["text"],
            parse_mode="HTML",
            reply_markup=keyboard,
            disable_web_page_preview=True
        )

# ========== ПРОВЕРКА ПОДПИСОК ==========
async def check_subscription(user_id: int, channel_username: str) -> bool:
    try:
        member = await bot.get_chat_member(chat_id=f"@{channel_username}", user_id=user_id)
        if member.status in ["member", "creator", "administrator"]:
            return True
        return False
    except Exception as e:
        print(f"Ошибка проверки подписки: {e}")
        return False

async def check_all_sponsors(user_id: int) -> tuple:
    if not sponsors_db:
        return True, []
    
    not_subscribed = []
    for sponsor_id, sponsor in sponsors_db.items():
        if 'link' not in sponsor:
            continue
            
        username = extract_channel_username(sponsor['link'])
        if username:
            is_subscribed = await check_subscription(user_id, username)
            if not is_subscribed:
                not_subscribed.append(sponsor)
        else:
            not_subscribed.append(sponsor)
    
    return len(not_subscribed) == 0, not_subscribed

async def send_with_photo(chat_id: int, text: str, reply_markup, photo_key: str, user_id: int = None):
    photo_file_id = photos_db.get(photo_key)
    
    sent_message = None
    
    if photo_file_id and os.path.exists(f"photos/{photo_file_id}.jpg"):
        try:
            photo = FSInputFile(f"photos/{photo_file_id}.jpg")
            sent_message = await bot.send_photo(
                chat_id=chat_id, 
                photo=photo, 
                caption=text, 
                reply_markup=reply_markup,
                parse_mode="HTML"
            )
        except Exception as e:
            print(f"Ошибка отправки фото: {e}")
            sent_message = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="HTML")
    else:
        sent_message = await bot.send_message(chat_id=chat_id, text=text, reply_markup=reply_markup, parse_mode="HTML")
    
    if user_id:
        await delete_previous_messages(chat_id, user_id, sent_message.message_id)
    
    return sent_message

# ========== ОТПРАВКА ЛОГОВ ==========
async def send_withdrawal_log(user_id: int, full_name: str, cost: int):
    if not LOG_CHANNEL_ID:
        return
    try:
        log_text = f"⌛️ Создана заявка на вывод\n👤 Пользователь: {full_name}\n🎁 Количество звезд: {cost}"
        await bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_text, parse_mode="HTML")
    except Exception as e:
        print(f"❌ Ошибка отправки лога: {e}")

async def send_gift_log(user_id: int, full_name: str, gift_name: str, gift_price: int):
    if not LOG_CHANNEL_ID:
        return
    try:
        log_text = f"⌛️ <b>Создана заявка на вывод!</b>\n\n👤 Пользователь: {full_name}\n🎁 Подарок: {gift_name}\n💰 Стоимость: {gift_price} ⭐️"
        await bot.send_message(chat_id=LOG_CHANNEL_ID, text=log_text, parse_mode="HTML")
    except Exception as e:
        print(f"❌ Ошибка отправки лога: {e}")

# ========== ОБЩИЕ ПРОВЕРКИ ==========
async def check_and_send_sponsors(user_id: int, message: types.Message = None, callback: CallbackQuery = None):
    all_subscribed, not_subscribed = await check_all_sponsors(user_id)
    if all_subscribed or not sponsors_db:
        return True
    else:
        text = "<b>🌸 Подпишись пожалуйста на наши каналы</b>\n\nПосле подписки тебе будет доступен весь функционал"
        keyboard = sponsors_keyboard(not_subscribed)
        if message:
            await send_with_photo(message.chat.id, text, keyboard, "sponsors", user_id)
        elif callback:
            await send_with_photo(callback.message.chat.id, text, keyboard, "sponsors", user_id)
        return False

# ========== НАПОМИНАНИЯ О ЗАРАБОТКЕ ==========
async def check_earn_reminders():
    """Отправляет напоминания о заработке звёзд каждые 2 часа"""
    while True:
        try:
            now = datetime.now()
            for user_id, user_data in users_db.items():
                last_reminder = user_data.get("last_earn_reminder")
                
                if not last_reminder:
                    try:
                        await bot.send_message(
                            user_id,
                            "⭐️ <b>Ты ещё не начинал зарабатывать звёзды!</b>\n\n"
                            "Нажми на кнопку ниже, чтобы получить свои первые звёзды! ✨\n\n"
                            "👇 <i>Кликер ждёт тебя!</i>",
                            parse_mode="HTML",
                            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="✨️ Кликер", callback_data="farm_stars")],
                                [InlineKeyboardButton(text="⭐️ Заработать больше", callback_data="get_ref_link")]
                            ])
                        )
                        user_data["last_earn_reminder"] = now.isoformat()
                        save_user(user_id, user_data)
                    except:
                        pass
                    
                else:
                    last_time = datetime.fromisoformat(last_reminder)
                    if (now - last_time).total_seconds() >= 7200:
                        try:
                            await bot.send_message(
                                user_id,
                                "⭐️ <b>Пора зарабатывать звёзды!</b>\n\n"
                                "✅ Каждые 3 минуты ты можешь получать звёзды через кликер!\n"
                                "👥 Приглашай друзей и получай бонусы!\n"
                                "🎁 Открывай кейсы и выигрывай!\n\n"
                                "👇 <i>Начни прямо сейчас!</i>",
                                parse_mode="HTML",
                                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                                    [InlineKeyboardButton(text="✨️ Кликер", callback_data="farm_stars")],
                                    [InlineKeyboardButton(text="👥 Пригласить друзей", callback_data="get_ref_link")],
                                    [InlineKeyboardButton(text="🎁 Открыть кейс", callback_data="cases_menu")]
                                ])
                            )
                            user_data["last_earn_reminder"] = now.isoformat()
                            save_user(user_id, user_data)
                        except:
                            pass
                        
        except Exception as e:
            print(f"Ошибка в напоминаниях о заработке: {e}")
        await asyncio.sleep(3600)

async def send_welcome_to_all_users():
    """Отправляет всю цепочку приветственных сообщений ВСЕМ пользователям каждые 30 минут"""
    while True:
        try:
            # Ждём 30 минут перед отправкой
            await asyncio.sleep(1800)  # 30 минут = 1800 секунд
            
            if not users_db:
                print("Нет пользователей для рассылки")
                continue
            
            print(f"Начинаем массовую рассылку приветствий {len(users_db)} пользователям...")
            
            for user_id in users_db.keys():
                try:
                    # Отправляем все приветственные сообщения по очереди
                    for i, msg_data in enumerate(WELCOME_MESSAGES):
                        keyboard = create_custom_url_keyboard(msg_data["buttons"])
                        
                        await bot.send_message(
                            user_id,
                            msg_data["text"],
                            parse_mode="HTML",
                            reply_markup=keyboard,
                            disable_web_page_preview=True
                        )
                        
                        # Задержка между сообщениями
                        if i < len(WELCOME_MESSAGES) - 1:
                            await asyncio.sleep(msg_data["delay_seconds"])
                    
                    # Небольшая задержка между пользователями
                    await asyncio.sleep(0.05)
                    
                except Exception as e:
                    print(f"Ошибка отправки приветствий пользователю {user_id}: {e}")
                    
            print("Рассылка приветствий завершена")
            
        except Exception as e:
            print(f"Ошибка в периодической рассылке приветствий: {e}")

async def send_broadcast_message(source_message: types.Message, state: FSMContext):
    """Отправляет рассылку всем пользователям"""
    data = await state.get_data()
    content = data.get("content", {})
    button_text = data.get("button_text")
    button_url = data.get("button_url")
    
    if not users_db:
        await source_message.answer("<b>❌ Нет пользователей</b>", parse_mode="HTML")
        await state.clear()
        await send_with_photo(source_message.chat.id, "<b>👑 Админ панель</b>", admin_keyboard(), "main_menu", ADMIN_ID)
        return
    
    total = len(users_db)
    success = 0
    fail = 0
    
    status = await source_message.answer(f"<b>📢 Рассылка началась...</b>\n👥 Всего: {total}", parse_mode="HTML")
    
    # Создаём клавиатуру с кнопкой, если нужно
    reply_markup = None
    if button_text and button_url:
        reply_markup = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=button_text, url=button_url)]
        ])
    
    for user_id in users_db.keys():
        try:
            if content.get("has_photo"):
                await bot.send_photo(
                    user_id,
                    content["photo_id"],
                    caption=content["text"],
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            elif content.get("has_video"):
                await bot.send_video(
                    user_id,
                    content["video_id"],
                    caption=content["text"],
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            elif content.get("has_animation"):
                await bot.send_animation(
                    user_id,
                    content["animation_id"],
                    caption=content["text"],
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            elif content.get("has_document"):
                await bot.send_document(
                    user_id,
                    content["document_id"],
                    caption=content["text"],
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            else:
                await bot.send_message(
                    user_id,
                    content["text"],
                    reply_markup=reply_markup,
                    parse_mode="HTML"
                )
            success += 1
        except:
            fail += 1
        await asyncio.sleep(0.05)
    
    result_text = (
        f"<b>📢 РАССЫЛКА ЗАВЕРШЕНА</b>\n\n"
        f"✅ Отправлено: {success}\n"
        f"❌ Ошибок: {fail}\n"
        f"👥 Всего: {total}"
    )
    
    if button_text:
        result_text += f"\n\n🔘 Кнопка: «{button_text}» -> {button_url}"
    
    await source_message.answer(result_text, parse_mode="HTML")
    
    # Возвращаемся в админ-панель
    await send_with_photo(source_message.chat.id, "<b>👑 Админ панель</b>", admin_keyboard(), "main_menu", ADMIN_ID)
    
    await state.clear()

# ========== КОМАНДЫ ==========
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    user_id = message.from_user.id
    user = get_user(user_id)
    
    args = message.text.split()
    if len(args) > 1 and args[1].startswith("ref_"):
        try:
            referrer_id = int(args[1].split("_")[1])
            if referrer_id != user_id and user["referrer_id"] is None and user["pending_referrer"] is None:
                user["pending_referrer"] = referrer_id
                save_user(user_id, user)
        except:
            pass
    
    success = await check_and_send_sponsors(user_id, message=message)
    if not success:
        return
    
    if user.get("pending_referrer") and not user.get("referral_completed", False):
        await activate_referral(user_id)
        user = get_user(user_id)
    
    # Отправляем главное меню
    await send_with_photo(
        message.chat.id, 
        f"<b>{PREMIUM_FLOWER} Главное меню {PREMIUM_FLOWER}</b>", 
        main_menu_keyboard(), 
        "main_menu", 
        user_id
    )
    
    # ВСЕГДА отправляем цепочку приветствий (игнорируем флаг)
    asyncio.create_task(send_welcome_chain(user_id, force=True))
# ========== ПОДАРКИ ==========
@dp.callback_query(F.data == "gifts_menu")
async def gifts_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    success = await check_and_send_sponsors(user_id, callback=callback)
    if not success:
        await callback.answer()
        return
    
    user = get_user(user_id)
    text = f"<b>🎁 Магазин подарков</b>\n\n<b>Ваш баланс: {round(user['balance'], 1)} ⭐️</b>\n\nВыберите подарок для покупки:\n\nУбедитесь,что у вас есть @username"
    
    await send_with_photo(callback.message.chat.id, text, gifts_menu_keyboard(), "gifts", user_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("buy_gift_"))
async def buy_gift(callback: CallbackQuery):
    user_id = callback.from_user.id
    gift_key = callback.data.replace("buy_gift_", "")
    
    if gift_key not in GIFTS:
        await callback.answer("❌ Подарок не найден", show_alert=True)
        return
    
    gift = GIFTS[gift_key]
    user = get_user(user_id)
    
    total_refs = get_total_referrals_count(user_id)
    if total_refs < MIN_REFERRALS_FOR_WITHDRAWAL:
        await callback.answer(
            f"❌ Покупка подарков недоступна!\n\nДля покупки нужно пригласить {MIN_REFERRALS_FOR_WITHDRAWAL} друзей.\nУ вас приглашено: {total_refs}",
            show_alert=True
        )
        return
    
    if user["balance"] < gift["price"]:
        await callback.answer(f"❌ Недостаточно звёзд! Нужно {gift['price']} ⭐️", show_alert=True)
        return
    
    user["balance"] = round(user["balance"] - gift["price"], 1)
    save_user(user_id, user)
    
    try:
        user_info = await bot.get_chat(user_id)
        full_name = user_info.full_name
    except:
        full_name = "неизвестно"
    
    await send_gift_log(user_id, full_name, gift['name'], gift['price'])
    
    await bot.send_message(
        ADMIN_ID,
        f"🎁 <b>НОВЫЙ ПОДАРОК!</b>\n\n"
        f"👤 Пользователь: {full_name}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🎁 Подарок: {gift['name']}\n"
        f"💰 Стоимость: {gift['price']} ⭐️\n"
        f"💎 Остаток: {round(user['balance'], 1)} ⭐️\n"
        f"👥 Рефералов: {total_refs}",
        parse_mode="HTML"
    )
    
    msg = await callback.message.answer(
        f"<b>🌸 Заявка на подарок оформлена!</b>\n\n"
        f"🎁 Подарок: {gift['name']}\n"
        f"⭐️ Списано: {gift['price']} звезд\n"
        f"💫 Остаток: {round(user['balance'], 1)} звезд\n\n"
        f"Ожидайте получения подарка в ближайшее время!",
        parse_mode="HTML"
    )
    await delete_previous_messages(msg.chat.id, user_id, msg.message_id)
    
    await callback.answer()
    await send_with_photo(callback.message.chat.id, "<b>🌸 Главное меню</b>", main_menu_keyboard(), "main_menu", user_id)

# ========== КЕЙСЫ ==========
@dp.callback_query(F.data == "cases_menu")
async def cases_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    success = await check_and_send_sponsors(user_id, callback=callback)
    if not success:
        await callback.answer()
        return
    user = get_user(user_id)
    text = f"<b>📦 Кейсы</b>\n\n<b>Баланс: {round(user['balance'], 1)} ⭐️</b>\n\nВыбери кейс:"
    await send_with_photo(callback.message.chat.id, text, cases_menu_keyboard(user_id), "cases", user_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("case_"))
async def open_case_handler(callback: CallbackQuery):
    user_id = callback.from_user.id
    case_key = callback.data.replace("case_", "")
    if case_key not in CASES:
        await callback.answer("❌ Кейс не найден", show_alert=True)
        return
    
    case = CASES[case_key]
    user = get_user(user_id)
    
    if case_key == "free":
        can_open, remaining = can_open_free_case(user_id)
        if not can_open:
            time_str = format_time(remaining)
            await callback.answer(f"⏰ Бесплатный кейс доступен через {time_str}!", show_alert=True)
            return
    elif case["price"] > 0:
        if user["balance"] < case["price"]:
            await callback.answer(f"❌ Недостаточно звёзд! Нужно {case['price']} ⭐️", show_alert=True)
            return
        user["balance"] = round(user["balance"] - case["price"], 1)
    
    reward = open_case(case_key)
    
    if reward > 0:
        user["balance"] = round(user["balance"] + reward, 1)
        result_text = f"✅ <b>ВЫ ВЫИГРАЛИ!</b>\n🎁 Выигрыш: +{reward} ⭐️"
    else:
        result_text = f"❌ <b>ВЫ ПРОИГРАЛИ!</b>\n😢 Вы ничего не получили..."
    
    if case_key == "free":
        user["last_free_case"] = datetime.now().isoformat()
    
    save_user(user_id, user)
    
    msg = await callback.message.answer(
        f"<b>{case['name']}</b>\n\n"
        f"💰 Стоимость: {case['price']} ⭐️\n"
        f"{result_text}\n\n"
        f"⭐️ Новый баланс: {round(user['balance'], 1)} ⭐️",
        parse_mode="HTML"
    )
    await delete_previous_messages(msg.chat.id, user_id, msg.message_id)
    
    text = f"<b>📦 Кейсы</b>\n\n<b>Баланс: {round(user['balance'], 1)} ⭐️</b>\n\nВыбери кейс:"
    await send_with_photo(callback.message.chat.id, text, cases_menu_keyboard(user_id), "cases", user_id)
    await callback.answer()

# ========== ИГРЫ ==========
@dp.callback_query(F.data == "games_menu")
async def games_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    success = await check_and_send_sponsors(user_id, callback=callback)
    if not success:
        await callback.answer()
        return
    text = f"<b>🎮 Игры</b>\n\n<b>Баланс: {round(get_user(user_id)['balance'], 1)} ⭐️</b>\n\nВыбери игру:"
    await send_with_photo(callback.message.chat.id, text, games_menu_keyboard(), "games", user_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("game_"))
async def select_game(callback: CallbackQuery):
    user_id = callback.from_user.id
    game_key = callback.data.replace("game_", "")
    if game_key not in GAME_NAMES:
        await callback.answer("❌ Игра не найдена", show_alert=True)
        return
    
    user = get_user(user_id)
    game_name = GAME_NAMES[game_key]
    game_desc = GAME_DESCRIPTIONS[game_key]
    coeff = GAME_COEFFICIENTS[game_key]
    photo_key = GAME_PHOTO_KEYS[game_key]
    
    text = f"<b>{game_name}</b>\n- {game_desc} (x{coeff})\n\n<b>Баланс: {round(user['balance'], 1)} ⭐️</b>\n\nВыбери ставку:"
    await send_with_photo(callback.message.chat.id, text, bet_keyboard(game_key), photo_key, user_id)
    await callback.answer()

@dp.callback_query(F.data.startswith("bet_"))
async def process_bet(callback: CallbackQuery):
    user_id = callback.from_user.id
    parts = callback.data.split("_")
    game_key = parts[1]
    bet_amount = int(parts[2])
    user = get_user(user_id)
    
    if user["balance"] < bet_amount:
        await callback.answer(f"❌ Недостаточно звёзд! Нужно {bet_amount} ⭐️", show_alert=True)
        return
    
    coeff = GAME_COEFFICIENTS[game_key]
    
    try:
        if game_key == "dice":
            result_msg = await bot.send_dice(callback.message.chat.id, emoji="🎲")
            won = result_msg.dice.value >= 4
        elif game_key == "slots":
            result_msg = await bot.send_dice(callback.message.chat.id, emoji="🎰")
            won = result_msg.dice.value == 64
        elif game_key == "basketball":
            result_msg = await bot.send_dice(callback.message.chat.id, emoji="🏀")
            won = result_msg.dice.value in [4, 5]
        elif game_key == "bowling":
            result_msg = await bot.send_dice(callback.message.chat.id, emoji="🎳")
            won = result_msg.dice.value == 6
        elif game_key == "football":
            result_msg = await bot.send_dice(callback.message.chat.id, emoji="⚽")
            won = result_msg.dice.value in [2, 3]
        elif game_key == "darts":
            result_msg = await bot.send_dice(callback.message.chat.id, emoji="🎯")
            won = result_msg.dice.value == 6
        else:
            await callback.answer("❌ Игра не найдена", show_alert=True)
            return
        
        await asyncio.sleep(3)
        
        user["balance"] = round(user["balance"] - bet_amount, 1)
        save_user(user_id, user)
        game_name = GAME_NAMES[game_key]
        
        if won:
            win_amount = int(bet_amount * coeff)
            user["balance"] = round(user["balance"] + win_amount, 1)
            save_user(user_id, user)
            msg = await callback.message.answer(
                f"<b>{GAME_EMOJI[game_key]} Результат игры: {game_name}</b>\n\n"
                f"💰 Ставка: {bet_amount} ⭐️\n"
                f"✅ <b>ВЫ ВЫИГРАЛИ!</b>\n"
                f"🎁 Выигрыш: {win_amount} ⭐️ (x{coeff})\n\n"
                f"⭐️ Новый баланс: {round(user['balance'], 1)} ⭐️",
                parse_mode="HTML"
            )
            await delete_previous_messages(msg.chat.id, user_id, msg.message_id)
        else:
            msg = await callback.message.answer(
                f"<b>{GAME_EMOJI[game_key]} Результат игры: {game_name}</b>\n\n"
                f"💰 Ставка: {bet_amount} ⭐️\n"
                f"❌ <b>ВЫ ПРОИГРАЛИ!</b>\n\n"
                f"⭐️ Новый баланс: {round(user['balance'], 1)} ⭐️",
                parse_mode="HTML"
            )
            await delete_previous_messages(msg.chat.id, user_id, msg.message_id)
    except Exception as e:
        print(f"Ошибка в игре: {e}")
        await callback.message.answer("<b>❌ Произошла ошибка при игре. Попробуйте позже.</b>", parse_mode="HTML")
        return
    
    text = f"<b>🎮 Игры</b>\n\n<b>Баланс: {round(user['balance'], 1)} ⭐️</b>\n\nВыбери игру:"
    await send_with_photo(callback.message.chat.id, text, games_menu_keyboard(), "games", user_id)
    await callback.answer()

# ========== ФАРМИНГ ==========
@dp.callback_query(F.data == "farm_stars")
async def farm_stars(callback: CallbackQuery):
    user_id = callback.from_user.id
    success = await check_and_send_sponsors(user_id, callback=callback)
    if not success:
        await callback.answer()
        return
    
    user = get_user(user_id)
    can_farm_now, remaining_seconds = can_farm(user_id)
    
    if not can_farm_now:
        time_str = format_time(remaining_seconds)
        await callback.answer(f"⏰ Кликер станет доступен через {time_str}!", show_alert=True)
        return
    
    stars = round(random.uniform(0.3, 0.8), 1)
    user["balance"] = round(user["balance"] + stars, 1)
    user["last_farm"] = datetime.now().isoformat()
    save_user(user_id, user)
    
    await callback.answer(f"✨ +{stars} ⭐️!", show_alert=True)
    await send_with_photo(callback.message.chat.id, "<b>🌸 Главное меню</b>", main_menu_keyboard(), "main_menu", user_id)

# ========== РЕФЕРАЛКА ==========
@dp.callback_query(F.data == "get_ref_link")
async def get_ref_link(callback: CallbackQuery):
    user_id = callback.from_user.id
    success = await check_and_send_sponsors(user_id, callback=callback)
    if not success:
        await callback.answer()
        return
    
    bot_info = await bot.get_me()
    ref_link = f"https://t.me/{bot_info.username}?start=ref_{user_id}"
    
    total_refs = get_total_referrals_count(user_id)
    pending_refs = get_pending_referrals_count(user_id)
    
    text = f"<b>🔗 Приглашай друзей и получай звёзды!</b>\n\n"
    text += f"Что ты получишь?\nЗа каждого друга, который перейдёт по твоей ссылке ты получаешь <b>+{REFERRAL_REWARD} ⭐️</b>!\n\n"
    text += f"Минимальное количество рефералов для вывода звёзд и покупки подарков: <b>{MIN_REFERRALS_FOR_WITHDRAWAL}</b>\n\n"
    text += f"Твоя реферальная ссылка:\n<code>{ref_link}</code>"
    
    await send_with_photo(callback.message.chat.id, text, back_to_menu_button(), "referral", user_id)
    await callback.answer()

# ========== ТОП РЕФОВОДОВ ==========
@dp.callback_query(F.data == "top_referrals")
async def show_top_referrals(callback: CallbackQuery):
    user_id = callback.from_user.id
    success = await check_and_send_sponsors(user_id, callback=callback)
    if not success:
        await callback.answer()
        return
    
    top_referrers = get_top_referrers()
    
    if not top_referrers:
        text = "<b>🏆 Топ рефоводов пока пуст!</b>\n\nПриглашай друзей, чтобы попасть в топ!"
    else:
        text = "<b>🏆 ТОП РЕФОВОДОВ🏆</b>\n\n"
        for idx, (uid, ref_count, balance) in enumerate(top_referrers, 1):
            try:
                user_info = await bot.get_chat(uid)
                name = user_info.full_name
                if len(name) > 20:
                    name = name[:17] + "..."
            except:
                name = f"User_{uid}"
            
            if idx == 1:
                medal = "🥇"
            elif idx == 2:
                medal = "🥈"
            elif idx == 3:
                medal = "🥉"
            else:
                medal = f"{idx}."
            text += f"{medal} <b>{name}</b>\n👥 {ref_count} реф. | ⭐️ {balance}\n"
    
    current_user_refs = get_total_referrals_count(user_id)
    if current_user_refs > 0:
        all_referrers = []
        for uid, u_data in users_db.items():
            total_refs = get_total_referrals_count(uid)
            if total_refs > 0:
                all_referrers.append((uid, total_refs))
        all_referrers.sort(key=lambda x: x[1], reverse=True)
        user_position = None
        for idx, (uid, _) in enumerate(all_referrers, 1):
            if uid == user_id:
                user_position = idx
                break
        if user_position:
            text += f"\n<b>📊 Ваша позиция: {user_position} место</b>\n👥 Ваших рефералов: {current_user_refs}"
    
    await send_with_photo(callback.message.chat.id, text, back_to_menu_button(), "top_referrals", user_id)
    await callback.answer()

# ========== ПРОМОКОДЫ ==========
@dp.callback_query(F.data == "enter_promocode")
async def enter_promocode_prompt(callback: CallbackQuery, state: FSMContext):
    user_id = callback.from_user.id
    success = await check_and_send_sponsors(user_id, callback=callback)
    if not success:
        await callback.answer()
        return
    msg = await callback.message.answer("<b>Введите промокод:</b>", parse_mode="HTML")
    await delete_previous_messages(msg.chat.id, user_id, msg.message_id)
    await state.set_state("waiting_for_promocode")
    await callback.answer()

@dp.message(F.text, StateFilter("waiting_for_promocode"))
async def process_promocode(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    await save_user_message_for_delete(message.chat.id, user_id, message.message_id)
    
    code = message.text.strip().upper()
    user = get_user(user_id)
    
    found_promocode = None
    for pid, promocode in promocodes_db.items():
        if promocode['code'] == code:
            found_promocode = promocode
            break
    
    if not found_promocode:
        msg = await message.answer("<b>❌ Промокод не найден!</b>", parse_mode="HTML")
        await delete_previous_messages(msg.chat.id, user_id, msg.message_id)
        await state.clear()
        return
    
    if str(found_promocode['id']) in user.get('used_promocodes', []):
        msg = await message.answer("<b>❌ Вы уже использовали этот промокод!</b>", parse_mode="HTML")
        await delete_previous_messages(msg.chat.id, user_id, msg.message_id)
        await state.clear()
        return
    
    if found_promocode['used_count'] >= found_promocode['max_uses'] and found_promocode['max_uses'] != 0:
        msg = await message.answer("<b>❌ Этот промокод больше недействителен!</b>", parse_mode="HTML")
        await delete_previous_messages(msg.chat.id, user_id, msg.message_id)
        await state.clear()
        return
    
    user['balance'] = round(user['balance'] + found_promocode['reward'], 1)
    if 'used_promocodes' not in user:
        user['used_promocodes'] = []
    user['used_promocodes'].append(str(found_promocode['id']))
    save_user(user_id, user)
    
    found_promocode['used_count'] += 1
    save_promocodes()
    
    msg = await message.answer(f"<b>✅ Промокод активирован!</b>\n\n💰 Награда: +{found_promocode['reward']} ⭐️\n\n⭐️ Новый баланс: {round(user['balance'], 1)} ⭐️", parse_mode="HTML")
    await delete_previous_messages(msg.chat.id, user_id, msg.message_id)
    await state.clear()
    await send_with_photo(message.chat.id, "<b>🌸 Главное меню</b>", main_menu_keyboard(), "main_menu", user_id)

# ========== ПРОФИЛЬ ==========
@dp.callback_query(F.data == "profile")
async def show_profile(callback: CallbackQuery):
    user_id = callback.from_user.id
    success = await check_and_send_sponsors(user_id, callback=callback)
    if not success:
        await callback.answer()
        return
    
    user = get_user(user_id)
    total_refs = get_total_referrals_count(user_id)
    pending_refs = get_pending_referrals_count(user_id)
    
    await send_with_photo(
        callback.message.chat.id,
        f"<b>👤 Ваш Профиль</b>\n\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"⭐️ Баланс: <b>{round(user['balance'], 1)}</b>\n"
        f"👥 Рефералов: <b>{total_refs}</b>\n",
        back_to_menu_button(),
        "profile",
        user_id
    )
    await callback.answer()

# ========== ОБМЕН ЗВЁЗД ==========
@dp.callback_query(F.data == "exchange_menu")
async def exchange_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    success = await check_and_send_sponsors(user_id, callback=callback)
    if not success:
        await callback.answer()
        return
    
    user = get_user(user_id)
    total_refs = get_total_referrals_count(user_id)
    
    if total_refs < MIN_REFERRALS_FOR_WITHDRAWAL:
        await callback.answer(
            f"❌ Вывод звёзд недоступен!\n\nДля вывода нужно пригласить {MIN_REFERRALS_FOR_WITHDRAWAL} друзей.\nУ вас приглашено: {total_refs}",
            show_alert=True
        )
        return
    
    await send_with_photo(
        callback.message.chat.id,
        f"<b>🌸 Ваш баланс: {round(user['balance'], 1)} ⭐️</b>\n\nВыберите сумму для вывода\nКанал с выводами @KirbyGift:\n\n",
        exchange_keyboard(),
        "exchange",
        user_id
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("exchange_"))
async def process_exchange(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    total_refs = get_total_referrals_count(user_id)
    
    if total_refs < MIN_REFERRALS_FOR_WITHDRAWAL:
        await callback.answer(f"❌ Вывод звёзд недоступен! Нужно {MIN_REFERRALS_FOR_WITHDRAWAL} рефералов", show_alert=True)
        return
    
    cost_map = {"exchange_15": 15, "exchange_25": 25, "exchange_50": 50, "exchange_100": 100, "exchange_premium": 1700}
    cost = cost_map.get(callback.data)
    if cost is None:
        await callback.answer("<b>❌ Неверный выбор</b>", show_alert=True)
        return
    
    if user["balance"] < cost:
        await callback.answer(f"<b>❌ Недостаточно звёзд! Нужно {cost} ⭐️</b>", show_alert=True)
        return
    
    gift_names = {"exchange_15": "15 ⭐️", "exchange_25": "25 ⭐️", "exchange_50": "50 ⭐️", "exchange_100": "100 ⭐️", "exchange_premium": "Telegram Premium 6мес."}
    gift_name = gift_names.get(callback.data, "Подарок")
    
    user["balance"] = round(user["balance"] - cost, 1)
    save_user(user_id, user)
    
    try:
        user_info = await bot.get_chat(user_id)
        full_name = user_info.full_name
        username = user_info.username
    except:
        full_name = "неизвестно"
        username = None
    
    await send_withdrawal_log(user_id, full_name, cost)
    
    username_text = f"@{username}" if username else "❌ нет username"
    
    await bot.send_message(
        ADMIN_ID,
        f"<b>🔄 НОВЫЙ ОБМЕН ЗВЁЗД!</b>\n\n"
        f"👤 Пользователь: {full_name}\n"
        f"🔗 {username_text}\n"
        f"🆔 ID: <code>{user_id}</code>\n"
        f"🎁 Сумма: {gift_name}\n"
        f"💰 Стоимость: {cost} ⭐️\n"
        f"💎 Остаток: {round(user['balance'], 1)} ⭐️\n"
        f"👥 Рефералов: {total_refs}",
        parse_mode="HTML"
    )
    
    msg = await callback.message.answer(
        f"<b>🌸 Заявка на вывод оформлена!</b>\n\n"
        f"⭐️ Списано: {cost} звезд\n"
        f"💫 Остаток: {round(user['balance'], 1)} звезд\n\n"
        f"Ожидайте выдачи в ближайшее время!",
        parse_mode="HTML"
    )
    await delete_previous_messages(msg.chat.id, user_id, msg.message_id)
    
    await callback.answer()
    await send_with_photo(callback.message.chat.id, "<b>🌸 Главное меню</b>", main_menu_keyboard(), "main_menu", user_id)

# ========== ПРОВЕРКА ПОДПИСОК ДЛЯ КНОПОК ==========
@dp.callback_query(F.data == "check_sponsors")
async def check_sponsors_callback(callback: CallbackQuery):
    user_id = callback.from_user.id
    user = get_user(user_id)
    
    all_subscribed, not_subscribed = await check_all_sponsors(user_id)
    
    if all_subscribed or not sponsors_db:
        await callback.answer("✅ Спасибо за подписку", show_alert=True)
        
        if user.get("pending_referrer") and not user.get("referral_completed", False):
            await activate_referral(user_id)
            user = get_user(user_id)
        
        # Отправляем главное меню
        await send_with_photo(
            callback.message.chat.id, 
            f"<b>{PREMIUM_FLOWER} Главное меню {PREMIUM_FLOWER}</b>", 
            main_menu_keyboard(), 
            "main_menu", 
            user_id
        )
        
        # Запускаем цепочку приветствий
        if not user.get("welcome_messages_sent", False):
            user["welcome_messages_sent"] = True
            save_user(user_id, user)
            asyncio.create_task(send_welcome_chain(user_id, force=True))
    else:
        text = "<b>🌸 Вы не подписаны на каналы:</b>\n\nПодпишитесь"
        await send_with_photo(callback.message.chat.id, text, sponsors_keyboard(not_subscribed), "sponsors", user_id)
        await callback.answer("🌸 Подпишись на каналы", show_alert=True)

# ========== АДМИН ПАНЕЛЬ ==========
@dp.callback_query(F.data == "admin_add_sponsor")
async def admin_add_sponsor(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    msg = await callback.message.answer("<b>📌 Введите ссылку на канал/группу:</b>", parse_mode="HTML")
    await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)
    await state.set_state(AdminAddSponsor.waiting_for_link)
    await callback.answer()

@dp.message(AdminAddSponsor.waiting_for_link)
async def admin_get_sponsor_link(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await save_user_message_for_delete(message.chat.id, ADMIN_ID, message.message_id)
    
    await state.update_data(link=message.text.strip())
    msg = await message.answer("<b>📝 Введите название спонсора:</b>", parse_mode="HTML")
    await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)
    await state.set_state(AdminAddSponsor.waiting_for_name)

@dp.message(AdminAddSponsor.waiting_for_name)
async def admin_get_sponsor_name(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await save_user_message_for_delete(message.chat.id, ADMIN_ID, message.message_id)
    
    data = await state.get_data()
    link = data["link"]
    name = message.text.strip()
    
    global next_sponsor_id
    sponsors_db[next_sponsor_id] = {"id": next_sponsor_id, "name": name, "link": link}
    save_sponsors()
    
    msg = await message.answer(f"<b>✅ Спонсор добавлен!</b>\n\nID: {next_sponsor_id}\nНазвание: {name}\nСсылка: {link}", parse_mode="HTML")
    await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)
    next_sponsor_id += 1
    await state.clear()
    await send_with_photo(message.chat.id, "<b>👑 Админ панель</b>", admin_keyboard(), "main_menu", ADMIN_ID)

@dp.callback_query(F.data == "admin_list_sponsors")
async def admin_list_sponsors(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    if not sponsors_db:
        await send_with_photo(callback.message.chat.id, "<b>📋 Нет добавленных спонсоров</b>", admin_keyboard(), "main_menu", ADMIN_ID)
        await callback.answer()
        return
    
    text = "<b>📋 Список спонсоров:</b>\n\n"
    for sponsor in sponsors_db.values():
        text += f"ID {sponsor['id']}: <b>{sponsor['name']}</b>\n🔗 {sponsor['link']}\n\n"
    
    await send_with_photo(callback.message.chat.id, text, admin_keyboard(), "main_menu", ADMIN_ID)
    await callback.answer()

@dp.callback_query(F.data == "admin_delete_sponsor")
async def admin_delete_sponsor_menu(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    if not sponsors_db:
        await callback.answer("❌ Нет спонсоров", show_alert=True)
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for sponsor_id, sponsor in sponsors_db.items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"🗑 {sponsor['name']}", callback_data=f"del_sponsor_{sponsor_id}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="← Назад", callback_data="admin")])
    
    await send_with_photo(callback.message.chat.id, "<b>🗑 Выберите спонсора для удаления:</b>", kb, "main_menu", ADMIN_ID)
    await callback.answer()

@dp.callback_query(F.data.startswith("del_sponsor_"))
async def admin_delete_sponsor(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    sponsor_id = int(callback.data.split("_")[2])
    if sponsor_id in sponsors_db:
        name = sponsors_db[sponsor_id]['name']
        del sponsors_db[sponsor_id]
        save_sponsors()
        await callback.answer(f"✅ Спонсор «{name}» удалён!", show_alert=True)
        await send_with_photo(callback.message.chat.id, "<b>✅ Спонсор удалён</b>", admin_keyboard(), "main_menu", ADMIN_ID)
    else:
        await callback.answer("❌ Спонсор не найден", show_alert=True)

@dp.callback_query(F.data == "admin_promocodes_menu")
async def admin_promocodes_menu(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await send_with_photo(callback.message.chat.id, "<b>🎁 Управление промокодами</b>", admin_promocodes_keyboard(), "main_menu", ADMIN_ID)
    await callback.answer()

@dp.callback_query(F.data == "admin_create_promocode")
async def admin_create_promocode(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    msg = await callback.message.answer("<b>🎁 Введите код промокода:</b>", parse_mode="HTML")
    await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)
    await state.set_state(AdminAddPromocode.waiting_for_code)
    await callback.answer()

@dp.message(AdminAddPromocode.waiting_for_code)
async def admin_get_promocode_code(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await save_user_message_for_delete(message.chat.id, ADMIN_ID, message.message_id)
    
    await state.update_data(code=message.text.strip().upper())
    msg = await message.answer("<b>💰 Введите награду за промокод (в звёздах):</b>", parse_mode="HTML")
    await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)
    await state.set_state(AdminAddPromocode.waiting_for_reward)

@dp.message(AdminAddPromocode.waiting_for_reward)
async def admin_get_promocode_reward(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await save_user_message_for_delete(message.chat.id, ADMIN_ID, message.message_id)
    
    try:
        reward = float(message.text)
        await state.update_data(reward=reward)
        msg = await message.answer("<b>📊 Введите максимальное количество активаций (0 = безлимит):</b>", parse_mode="HTML")
        await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)
        await state.set_state(AdminAddPromocode.waiting_for_max_uses)
    except ValueError:
        msg = await message.answer("<b>❌ Введите число!</b>", parse_mode="HTML")
        await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)

@dp.message(AdminAddPromocode.waiting_for_max_uses)
async def admin_get_promocode_max_uses(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await save_user_message_for_delete(message.chat.id, ADMIN_ID, message.message_id)
    
    try:
        max_uses = int(message.text)
        data = await state.get_data()
        
        global next_promocode_id
        promocodes_db[next_promocode_id] = {
            "id": next_promocode_id,
            "code": data['code'],
            "reward": data['reward'],
            "max_uses": max_uses,
            "used_count": 0
        }
        save_promocodes()
        
        msg = await message.answer(f"<b>✅ Промокод создан!</b>\n\n🎫 Код: <code>{data['code']}</code>\n💰 Награда: {data['reward']} ⭐️\n📊 Лимит: {'∞' if max_uses == 0 else max_uses}", parse_mode="HTML")
        await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)
        next_promocode_id += 1
        await state.clear()
        await send_with_photo(message.chat.id, "<b>👑 Админ панель</b>", admin_keyboard(), "main_menu", ADMIN_ID)
    except ValueError:
        msg = await message.answer("<b>❌ Введите число!</b>", parse_mode="HTML")
        await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)

@dp.callback_query(F.data == "admin_list_promocodes")
async def admin_list_promocodes(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    if not promocodes_db:
        await send_with_photo(callback.message.chat.id, "<b>📋 Нет созданных промокодов</b>", admin_promocodes_keyboard(), "main_menu", ADMIN_ID)
        await callback.answer()
        return
    
    text = "<b>🎁 Список промокодов:</b>\n\n"
    for promocode in promocodes_db.values():
        max_uses = '∞' if promocode['max_uses'] == 0 else promocode['max_uses']
        text += f"ID {promocode['id']}: <code>{promocode['code']}</code>\n💰 +{promocode['reward']} ⭐️ | 📊 {promocode['used_count']}/{max_uses}\n\n"
    
    await send_with_photo(callback.message.chat.id, text, admin_promocodes_keyboard(), "main_menu", ADMIN_ID)
    await callback.answer()

@dp.callback_query(F.data == "admin_delete_promocode")
async def admin_delete_promocode_menu(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    if not promocodes_db:
        await callback.answer("❌ Нет промокодов", show_alert=True)
        return
    
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for pid, promocode in promocodes_db.items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"🗑 {promocode['code']}", callback_data=f"del_promo_{pid}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="← Назад", callback_data="admin_promocodes_menu")])
    
    await send_with_photo(callback.message.chat.id, "<b>🗑 Выберите промокод для удаления:</b>", kb, "main_menu", ADMIN_ID)
    await callback.answer()

@dp.callback_query(F.data.startswith("del_promo_"))
async def admin_delete_promocode(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    promo_id = int(callback.data.split("_")[2])
    if promo_id in promocodes_db:
        code = promocodes_db[promo_id]['code']
        del promocodes_db[promo_id]
        save_promocodes()
        await callback.answer(f"✅ Промокод «{code}» удалён!", show_alert=True)
        await send_with_photo(callback.message.chat.id, "<b>✅ Промокод удалён</b>", admin_promocodes_keyboard(), "main_menu", ADMIN_ID)
    else:
        await callback.answer("❌ Промокод не найден", show_alert=True)

@dp.callback_query(F.data == "admin_broadcast")
async def admin_broadcast_menu(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    msg = await callback.message.answer(
        "<b>📢 Отправьте сообщение для рассылки (без кнопки):</b>\n\n"
        "Для отмены /cancel",
        parse_mode="HTML"
    )
    await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)
    await state.set_state(AdminBroadcast.waiting_for_content)
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast_with_button")
async def admin_broadcast_with_button_menu(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    msg = await callback.message.answer(
        "<b>📢 Отправьте сообщение для рассылки (с кнопкой):</b>\n\n"
        "Для отмены /cancel",
        parse_mode="HTML"
    )
    await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)
    await state.update_data(has_button=True)
    await state.set_state(AdminBroadcast.waiting_for_content)
    await callback.answer()

@dp.message(AdminBroadcast.waiting_for_content)
async def admin_get_broadcast_content(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await save_user_message_for_delete(message.chat.id, ADMIN_ID, message.message_id)
    
    if message.text == "/cancel":
        await state.clear()
        await message.answer("<b>✅ Рассылка отменена</b>", reply_markup=admin_keyboard(), parse_mode="HTML")
        return
    
    data = await state.get_data()
    has_button = data.get("has_button", False)
    
    # Сохраняем содержимое сообщения
    content = {
        "text": message.text or message.caption or "",
        "has_photo": bool(message.photo),
        "photo_id": message.photo[-1].file_id if message.photo else None,
        "has_video": bool(message.video),
        "video_id": message.video.file_id if message.video else None,
        "has_animation": bool(message.animation),
        "animation_id": message.animation.file_id if message.animation else None,
        "has_document": bool(message.document),
        "document_id": message.document.file_id if message.document else None,
    }
    
    await state.update_data(content=content)
    
    if has_button:
        msg = await message.answer(
            "<b>🔘 Введите ТЕКСТ кнопки:</b>\n\n",
            parse_mode="HTML"
        )
        await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)
        await state.set_state(AdminBroadcast.waiting_for_button_text)
    else:
        # Обычная рассылка без кнопки
        await send_broadcast_message(message, state)

@dp.message(AdminBroadcast.waiting_for_button_text)
async def admin_get_broadcast_button_text(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await save_user_message_for_delete(message.chat.id, ADMIN_ID, message.message_id)
    
    button_text = message.text.strip()
    
    # Если нет текста кнопки или отправлен 0 - отправляем без кнопки
    if not button_text or button_text == "0":
        await state.update_data(button_text=None, button_url=None)
        await send_broadcast_message(message, state)
        return
    
    await state.update_data(button_text=button_text)
    
    msg = await message.answer(
        "<b>🔗 Введите ССЫЛКУ для кнопки:</b>\n\n",
        parse_mode="HTML"
    )
    await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)
    await state.set_state(AdminBroadcast.waiting_for_button_url)

@dp.message(AdminBroadcast.waiting_for_button_url)
async def admin_get_broadcast_button_url(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    await save_user_message_for_delete(message.chat.id, ADMIN_ID, message.message_id)
    
    url = message.text.strip()
    
    # Преобразуем @username в ссылку
    if url.startswith("@"):
        url = f"https://t.me/{url[1:]}"
    elif not url.startswith("http://") and not url.startswith("https://"):
        url = f"https://{url}"
    
    await state.update_data(button_url=url)
    await send_broadcast_message(message, state)

@dp.callback_query(F.data == "admin_add_photo")
async def admin_add_photo_menu(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await send_with_photo(callback.message.chat.id, "<b>🖼 Выберите раздел для фото:</b>", admin_photo_keyboard(), "main_menu", ADMIN_ID)
    await callback.answer()

@dp.callback_query(F.data.startswith("photo_"))
async def admin_photo_selected(callback: CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    photo_key = callback.data.replace("photo_", "")
    
    if photo_key == "delete_all":
        for key in photos_db:
            photos_db[key] = None
        save_photos(photos_db)
        await callback.answer("✅ Все фото удалены!", show_alert=True)
        await send_with_photo(callback.message.chat.id, "<b>✅ Все фото удалены</b>", admin_keyboard(), "main_menu", ADMIN_ID)
        return
    
    await state.update_data(photo_key=photo_key)
    msg = await callback.message.answer(f"<b>📸 Отправьте фото для раздела: {photo_key}</b>", parse_mode="HTML")
    await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)
    await state.set_state(AdminSetPhoto.waiting_for_photo)
    await callback.answer()

@dp.message(AdminSetPhoto.waiting_for_photo)
async def admin_save_photo(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    if not message.photo:
        await message.answer("<b>❌ Отправьте фото!</b>", parse_mode="HTML")
        return
    
    data = await state.get_data()
    photo_key = data.get("photo_key")
    
    if not os.path.exists("photos"):
        os.makedirs("photos")
    
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    await bot.download_file(file.file_path, f"photos/{photo_key}.jpg")
    
    photos_db[photo_key] = photo_key
    save_photos(photos_db)
    
    msg = await message.answer(f"<b>✅ Фото добавлено для раздела: {photo_key}</b>", parse_mode="HTML")
    await delete_previous_messages(msg.chat.id, ADMIN_ID, msg.message_id)
    await state.clear()
    await send_with_photo(message.chat.id, "<b>👑 Админ панель</b>", admin_keyboard(), "main_menu", ADMIN_ID)

@dp.callback_query(F.data == "admin_stats")
async def admin_stats(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    
    total_users = len(users_db)
    total_balance = sum(u.get("balance", 0) for u in users_db.values())
    total_referrals = sum(get_total_referrals_count(uid) for uid in users_db.keys())
    total_pending = sum(get_pending_referrals_count(uid) for uid in users_db.keys())
    
    await send_with_photo(
        callback.message.chat.id,
        f"<b>📊 СТАТИСТИКА</b>\n\n"
        f"👥 Пользователей: <b>{total_users}</b>\n"
        f"⭐️ Баланс всех: <b>{round(total_balance, 1)}</b>\n"
        f"🔗 Всего рефералов: <b>{total_referrals}</b>\n"
        f"⏳ Ожидают подписки: <b>{total_pending}</b>\n"
        f"📢 Спонсоров: <b>{len(sponsors_db)}</b>\n"
        f"🎫 Промокодов: <b>{len(promocodes_db)}</b>",
        admin_keyboard(),
        "main_menu",
        ADMIN_ID
    )
    await callback.answer()

@dp.callback_query(F.data == "admin")
async def back_to_admin(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("❌ Нет доступа", show_alert=True)
        return
    await send_with_photo(callback.message.chat.id, "<b>👑 Админ панель</b>", admin_keyboard(), "main_menu", ADMIN_ID)
    await callback.answer()
@dp.callback_query(F.data == "main_menu")
async def back_to_main_menu(callback: CallbackQuery):
    user_id = callback.from_user.id
    success = await check_and_send_sponsors(user_id, callback=callback)
    if not success:
        await callback.answer()
        return
    await send_with_photo(callback.message.chat.id, f"<b>{PREMIUM_FLOWER} Главное меню {PREMIUM_FLOWER}</b>", main_menu_keyboard(), "main_menu", user_id)
    await callback.answer()

# ========== АДМИН КОМАНДА ==========
@dp.message(Command("admin"))
async def cmd_admin(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        await message.answer("<b>❌ У вас нет доступа к админ-панели</b>", parse_mode="HTML")
        return
    
    await send_with_photo(
        message.chat.id, 
        "<b>👑 Админ панель</b>", 
        admin_keyboard(), 
        "main_menu", 
        ADMIN_ID
    )

# ========== ЗАПУСК БОТА ==========
async def main():
    # Создаём папку для фото, если её нет
    if not os.path.exists("photos"):
        os.makedirs("photos")
    
    print("🚀 Бот запущен")
    print(f"👑 Админ ID: {ADMIN_ID}")
    print(f"📋 Лог-канал: {LOG_CHANNEL_ID}")
    print(f"📌 Для вывода нужно минимум: {MIN_REFERRALS_FOR_WITHDRAWAL} рефералов")
    print("🗑 Включено автоматическое удаление предыдущих сообщений в ЛС")
    print("⏰ Включены напоминания о заработке (каждые 2 часа)")
    print("🎉 Включена периодическая рассылка приветствий ВСЕМ пользователям (каждые 30 минут)")
    print("🔒 Рефералы засчитываются только после подписки на каналы")
    
    # Запускаем фоновые задачи
    asyncio.create_task(check_earn_reminders())
    asyncio.create_task(send_welcome_to_all_users())
    
    # Запускаем бота
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())