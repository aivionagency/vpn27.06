START_NEW_USER = """<tg-emoji emoji-id="5237763160647149111">👋</tg-emoji> Привет! Это умный VPN.

<tg-emoji emoji-id="5231008469875706287">💳</tg-emoji> <tg-emoji emoji-id="5280502771051667560">🇷🇺</tg-emoji> Госуслуги, банки и российские сайты
работают без отключения VPN.

🎁 Дарим 3 дня бесплатно — ключ уже готов.
Можно подключить сразу на 2 устройства.

<tg-emoji emoji-id="5296369303661067030">🔒</tg-emoji> Ваш ключ:
<code>{vpn_key}</code>"""

START_RETURNING_USER = """<tg-emoji emoji-id="5237763160647149111">👋</tg-emoji> Привет! Это умный VPN.

<tg-emoji emoji-id="5231008469875706287">💳</tg-emoji> <tg-emoji emoji-id="5280502771051667560">🇷🇺</tg-emoji> Госуслуги, банки и российские сайты
работают без отключения VPN.

<tg-emoji emoji-id="5296369303661067030">🔒</tg-emoji> Ваш ключ:
<code>{vpn_key}</code>"""

MAIN_MENU = "Здравствуйте, {username}! Здесь вы можете пополнить баланс и управлять подписками"

SUBSCRIPTION_ACTIVE = """Ваша подписка

Статус: <tg-emoji emoji-id="5289768432848359522">👍</tg-emoji> Активна (до {expires_at})
Тариф: {tariff_name}
Баланс: {balance} ₽

<tg-emoji emoji-id="5296369303661067030">🔒</tg-emoji> Ваш ключ (на {devices}):
<code>{vpn_key}</code>"""

SUBSCRIPTION_TRIAL = """Ваша подписка

Статус: 🎁 Пробный период (осталось {days_left} дн.)
Баланс: {balance} ₽

<tg-emoji emoji-id="5296369303661067030">🔒</tg-emoji> Ваш ключ (на {devices}):
<code>{vpn_key}</code>"""

SUBSCRIPTION_EXPIRED = """Ваша подписка

Статус: 🔴 Истекла
Баланс: {balance} ₽

<tg-emoji emoji-id="5296369303661067030">🔒</tg-emoji> Ваш ключ (на {devices}):
<code>{vpn_key}</code>"""

CHOOSE_DEVICES = """🛡 <b>Подписка умного VPN</b>

🌍 5 стран на выбор
♾ Безлимитный трафик без ограничений скорости
🔒 Надёжное шифрование, без логов
🇷🇺 Госуслуги, банки и российские сайты работают без отключения VPN
📱 Поддержка iOS, Android, Windows, macOS и Android TV
🆘 Поддержка 24/7

Выберите количество устройств:"""

CHOOSE_TARIFF = """📱 Подключаем: {devices}

💳 Выберите тариф:
Ваш баланс: {balance} ₽"""

TARIFF_CONFIRMATION = """Тариф: {title}
📱 Устройств: {devices}
Срок: {days} дней
Стоимость: {price} ₽

Ваш баланс: {balance} ₽"""

SUCCESSFUL_PURCHASE = """✅ Подписка активирована!
Списано: {price} ₽ · Остаток баланса: {balance} ₽
Активна до: {expires_at}"""

INSUFFICIENT_FUNDS = """⚠️ Недостаточно средств
Нужно: {price} ₽ · На балансе: {balance} ₽
Не хватает: {diff} ₽"""

REFERRAL_MENU = """Приглашайте друзей и зарабатывайте!

+{referral_reward} ₽ на баланс за каждого друга, кто оформит подписку.
+{referral_bonus} ₽ другу <b>после первого платежа</b>

<tg-emoji emoji-id="5350723128404228854">📈</tg-emoji> Ваша статистика:
 • Приглашено: {invited_count}
 • Оформили подписку: {purchased_count}
 • Заработано: {earned_total} ₽

<tg-emoji emoji-id="5291969685191936195">🔗</tg-emoji> Ваша ссылка:
{referral_link}"""

SUPPORT_TEXT = """💬 Связь с поддержкой

Опишите проблему одним сообщением ниже.
Укажите устройство и приложите скриншот.
Ответим прямо здесь."""

INSTRUCTION_STUB = "Здесь будет инструкция (заглушка)."
SUPPORT_SENT = "✅ Сообщение отправлено в поддержку. Мы ответим вам здесь."
SUPPORT_ERROR = "Произошла ошибка при отправке сообщения в поддержку."
SUPPORT_STUB = "✅ Заглушка: Ваше сообщение принято в обработку."

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
