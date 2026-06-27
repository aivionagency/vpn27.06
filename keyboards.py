from urllib.parse import quote
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.filters.callback_data import CallbackData

class TariffCallbackData(CallbackData, prefix="tariff"):
    id: int
    devices: int

class DeviceCallbackData(CallbackData, prefix="dev"):
    count: int

class PayCallbackData(CallbackData, prefix="pay"):
    tariff_id: int
    devices: int

class ActionCallbackData(CallbackData, prefix="action"):
    action: str

# Define Tariffs (base price is per 1 device; multiplied by the device option)
TARIFFS = [
    {"id": 1, "title": "1 месяц", "days": 30, "price": 159, "discount": None},
    {"id": 2, "title": "3 месяца", "days": 90, "price": 429, "discount": "−10%"},
    {"id": 3, "title": "6 месяцев", "days": 180, "price": 762, "discount": "−20%"},
    {"id": 4, "title": "12 месяцев", "days": 360, "price": 1146, "discount": "−40%"},
]

# Device count options and their price multipliers
DEVICE_OPTIONS = [
    {"count": 1, "multiplier": 1},
    {"count": 3, "multiplier": 2},
    {"count": 5, "multiplier": 3},
]

DEFAULT_DEVICES = 2  # trial keys work on 2 devices

def get_tariff_by_id(tariff_id: int):
    for t in TARIFFS:
        if t["id"] == tariff_id:
            return t
    return None

def get_device_multiplier(count: int) -> int:
    for opt in DEVICE_OPTIONS:
        if opt["count"] == count:
            return opt["multiplier"]
    return 1

def tariff_price(tariff: dict, devices: int) -> int:
    return tariff["price"] * get_device_multiplier(devices)

def start_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Подключить в 1 клик", url="https://example.com/placeholder")
    builder.button(text="📚 Инструкция по подключению", callback_data=ActionCallbackData(action="instruction").pack())
    builder.button(text="Главное меню", callback_data=ActionCallbackData(action="main_menu").pack())
    builder.adjust(1)
    return builder.as_markup()

def main_menu_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⚡️ Мой VPN", callback_data=ActionCallbackData(action="my_subscription").pack())
    builder.button(text="💰 Купить подписку", callback_data=ActionCallbackData(action="buy").pack())
    builder.button(text="🎁 Пригласить друга", callback_data=ActionCallbackData(action="referral").pack())
    builder.button(text="💬 Поддержка", callback_data=ActionCallbackData(action="support").pack())
    builder.adjust(1)
    return builder.as_markup()

def subscription_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="🚀 Подключить в 1 клик / 🔄 Обновить ключ", url="https://example.com/placeholder")
    builder.button(text="💰 Купить / Продлить", callback_data=ActionCallbackData(action="buy").pack())
    builder.button(text="🎁 Пригласить друга", callback_data=ActionCallbackData(action="referral").pack())
    builder.button(text="⬅️ Назад", callback_data=ActionCallbackData(action="main_menu").pack())
    builder.adjust(1)
    return builder.as_markup()

def devices_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for opt in DEVICE_OPTIONS:
        builder.button(
            text=f'📱 {opt["count"]}',
            callback_data=DeviceCallbackData(count=opt["count"]).pack(),
        )
    builder.button(text="⬅️ Назад", callback_data=ActionCallbackData(action="main_menu").pack())
    builder.adjust(len(DEVICE_OPTIONS), 1)
    return builder.as_markup()

def tariffs_keyboard(devices: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for tariff in TARIFFS:
        price = tariff_price(tariff, devices)
        label = f'{tariff["title"]} — {price} ₽'
        if tariff["discount"]:
            label += f' · {tariff["discount"]}'
        builder.button(
            text=label,
            callback_data=TariffCallbackData(id=tariff["id"], devices=devices).pack(),
        )
    builder.button(text="⬅️ Назад", callback_data=ActionCallbackData(action="buy").pack())
    builder.adjust(1)
    return builder.as_markup()

def tariff_confirmation_keyboard(tariff_id: int, devices: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="✅ Оплатить", callback_data=PayCallbackData(tariff_id=tariff_id, devices=devices).pack())
    builder.button(text="⬅️ Назад", callback_data=DeviceCallbackData(count=devices).pack())
    builder.adjust(1)
    return builder.as_markup()

def successful_purchase_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⚡️ Моя подписка", callback_data=ActionCallbackData(action="my_subscription").pack())
    builder.button(text="Меню", callback_data=ActionCallbackData(action="main_menu").pack())
    builder.adjust(2)
    return builder.as_markup()

def insufficient_funds_keyboard(topup_url: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="💰 Пополнить баланс", url=topup_url)
    builder.button(text="⬅️ Назад", callback_data=ActionCallbackData(action="buy").pack())
    builder.adjust(1)
    return builder.as_markup()

def referral_keyboard(referral_link: str | None = None) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    if referral_link:
        share_text = f"Присоединяйся к нашему VPN! {referral_link}"
        share_url = f"https://t.me/share/url?url={quote(referral_link)}&text={quote(share_text)}"
        builder.button(text="📢 Поделиться", url=share_url)
    else:
        builder.button(text="📢 Поделиться", switch_inline_query="Присоединяйся к нашему VPN!")
    builder.button(text="⬅️ Назад", callback_data=ActionCallbackData(action="main_menu").pack())
    builder.adjust(1)
    return builder.as_markup()

def support_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.button(text="⬅️ Назад", callback_data=ActionCallbackData(action="main_menu").pack())
    return builder.as_markup()
