START_NEW_USER = """🔹 Добро пожаловать. Это ваш умный VPN.

💠 Госуслуги, банки и российские сервисы работают без отключения.
🟢 Вам доступно 3 дня бесплатно (подключение до 2 устройств).

Ключ доступа:
<code>{vpn_key}</code>"""

START_RETURNING_USER = """🔹 С возвращением.

💠 Госуслуги, банки и российские сервисы работают без отключения.

Ключ доступа:
<code>{vpn_key}</code>"""

MAIN_MENU = "🔹 {username}, управление подпиской и балансом:"

SUBSCRIPTION_ACTIVE = """🔹 Подписка активна (до {expires_at})

Тариф: {tariff_name}
Баланс: {balance} ₽

Ключ доступа ({devices}):
<code>{vpn_key}</code>"""

SUBSCRIPTION_TRIAL = """🔹 Пробный период (осталось {days_left} дн.)

Баланс: {balance} ₽

Ключ доступа ({devices}):
<code>{vpn_key}</code>"""

SUBSCRIPTION_EXPIRED = """🔹 Подписка истекла

Баланс: {balance} ₽

Ключ доступа ({devices}):
<code>{vpn_key}</code>"""

CHOOSE_DEVICES = """🔹 Выбор устройств

💠 5 локаций
💠 Безлимитный трафик
💠 Надёжное шифрование
💠 Поддержка всех платформ

Выберите количество устройств:"""

CHOOSE_TARIFF = """🔹 Устройств: {devices}

Выберите тариф (Баланс: {balance} ₽):"""

TARIFF_CONFIRMATION = """🔹 Подтверждение

Тариф: {title}
Устройств: {devices}
Срок: {days} дней
Стоимость: {price} ₽

Баланс: {balance} ₽"""

SUCCESSFUL_PURCHASE = """🟢 Подписка активирована

Списано: {price} ₽
Остаток баланса: {balance} ₽
Действует до: {expires_at}"""

INSUFFICIENT_FUNDS = """🔹 Недостаточно средств

Необходимо: {price} ₽
Ваш баланс: {balance} ₽"""

REFERRAL_MENU = """🔹 Приглашайте друзей

🟢 +{referral_reward} ₽ вам
🟢 +{referral_bonus} ₽ другу после первой оплаты

Статистика:
🔹 Приглашено: {invited_count}
🔹 Оформлено подписок: {purchased_count}
🔹 Ваш доход: {earned_total} ₽

Персональная ссылка:
{referral_link}"""

SUPPORT_TEXT = """🔹 Поддержка

Пожалуйста, опишите вашу проблему одним сообщением ниже.
Специалист ответит вам в этом чате."""

INSTRUCTION_STUB = "🔹 Инструкция по подключению (в разработке)."
SUPPORT_SENT = "🟢 Сообщение доставлено. Ожидайте ответа в этом чате."
SUPPORT_ERROR = "🔹 Произошла ошибка. Попробуйте еще раз."
SUPPORT_STUB = "🟢 Ваше обращение принято."

def devices_phrase(n: int) -> str:
    """Return a Russian phrase like '1 устройство', '3 устройства', '5 устройств'."""
    if n % 10 == 1 and n % 100 != 11:
        word = "устройство"
    elif 2 <= n % 10 <= 4 and not (12 <= n % 100 <= 14):
        word = "устройства"
    else:
        word = "устройств"
    return f"{n} {word}"

# Admin messages
ADD_BALANCE_USAGE = "Использование: /addbalance <сумма>"
ADD_BALANCE_INVALID = "Сумма должна быть числом."
ADD_BALANCE_SUCCESS = "✅ Баланс пополнен на {amount} ₽. Текущий баланс: {balance} ₽"
