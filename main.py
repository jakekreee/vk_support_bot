import sqlite3
import datetime
from vk_api import VkApi
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType
from vk_api.keyboard import VkKeyboard, VkKeyboardColor

# ================= НАСТРОЙКИ =================
TOKEN = "vk1.a.ZzY53BkvruJV0-JKYQEqNkKFUDxO8p8XeG5UgW3Vvr4wtncFyvbGsAgOvWwrDgpbVu42SZ6h3cr0HZnLSHl5PC7ysJABPmbVPKkLSgMvywONpilSc0h4k0Qf9xKZLKQbF5wcgpAD8cLHEMOMh1VTNdpPcOu6QO5rT6rYPLBkqNfBZqBwAoHJQrd6FXi2XDxQl_RwX8xZH4p2RuIdIpaUYQ"  # Токен сообщества
GROUP_ID = 240398315          # ID группы VK (число)
ADMIN_VK_IDS = [1109060680]        # VK ID главных администраторов/руководства

# ================= БАЗА ДАННЫХ =================
def init_db():
    conn = sqlite3.connect("black_russia_bot.db")
    cursor = conn.cursor()
    # Таблица агентов поддержки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS helpers (
            vk_id INTEGER PRIMARY KEY,
            nick_name TEXT,
            position TEXT DEFAULT 'Агент Поддержки',
            appoint_date TEXT,
            days INTEGER DEFAULT 0,
            norm_days INTEGER DEFAULT 0,
            answers INTEGER DEFAULT 0,
            points INTEGER DEFAULT 0,
            warns INTEGER DEFAULT 0,
            reprimands INTEGER DEFAULT 0,
            birthday TEXT DEFAULT '01.01'
        )
    ''')
    # Таблица неактивов
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS inactives (
            vk_id INTEGER PRIMARY KEY,
            start_date TEXT,
            end_date TEXT,
            status TEXT DEFAULT 'Одобрено'
        )
    ''')
    conn.commit()
    conn.close()

init_db()

# ================= ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ =================
def get_helper(vk_id):
    conn = sqlite3.connect("black_russia_bot.db")
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM helpers WHERE vk_id = ?", (vk_id,))
    res = cursor.fetchone()
    conn.close()
    return res

def add_helper(vk_id, nick_name, position, appoint_date):
    conn = sqlite3.connect("black_russia_bot.db")
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO helpers (vk_id, nick_name, position, appoint_date)
        VALUES (?, ?, ?, ?)
    ''', (vk_id, nick_name, position, appoint_date))
    conn.commit()
    conn.close()

def remove_helper(vk_id):
    conn = sqlite3.connect("black_russia_bot.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM helpers WHERE vk_id = ?", (vk_id,))
    cursor.execute("DELETE FROM inactives WHERE vk_id = ?", (vk_id,))
    conn.commit()
    conn.close()

def update_field(vk_id, field, delta):
    conn = sqlite3.connect("black_russia_bot.db")
    cursor = conn.cursor()
    cursor.execute(f"UPDATE helpers SET {field} = MAX(0, {field} + ?) WHERE vk_id = ?", (delta, vk_id))
    conn.commit()
    conn.close()

def generate_progress_bar(current, max_val):
    percent = min(100, int((current / max_val) * 100)) if max_val > 0 else 0
    filled = int(percent / 10)
    bar = "🟢" * filled + "⚪" * (10 - filled)
    return bar, percent

# ================= КЛАВИАТУРА =================
def get_main_keyboard():
    keyboard = VkKeyboard(one_time=False)
    keyboard.add_button("Статистика", color=VkKeyboardColor.PRIMARY)
    keyboard.add_button("road", color=VkKeyboardColor.POSITIVE)
    keyboard.add_line()
    keyboard.add_button("neak", color=VkKeyboardColor.SECONDARY)
    keyboard.add_button("онлайн", color=VkKeyboardColor.SECONDARY)
    return keyboard.get_keyboard()

# ================= ИНИЦИАЛИЗАЦИЯ ВК =================
vk_session = VkApi(token=TOKEN)
vk = vk_session.get_api()
longpoll = VkBotLongPoll(vk_session, GROUP_ID)

def send_msg(peer_id, text, keyboard=None):
    params = {'peer_id': peer_id, 'message': text, 'random_id': 0}
    if keyboard:
        params['keyboard'] = keyboard
    vk.messages.send(**params)

print("🚀 Бот Агентов Поддержки запущен!")

# ================= ОСНОВНОЙ ЦИКЛ =================
for event in longpoll.listen():
    if event.type == VkBotEventType.MESSAGE_NEW:
        msg = event.object.message
        user_id = msg['from_id']
        text = msg['text'].strip()
        peer_id = msg['peer_id']

        helper = get_helper(user_id)
        is_admin = user_id in ADMIN_VK_IDS

        # Проверка доступа: если пользователя нет в БД и он не админ — игнорируем
        if not helper and not is_admin:
            continue

        cmd = text.lower()

        # 📊 СТАТИСТИКА
        if cmd == "статистика":
            if not helper:
                send_msg(peer_id, "❌ Вы не являетесь Агентом Поддержки.")
                continue

            vk_id, nick, pos, appoint, days, norm_days, answers, points, warns, reprimands, bday = helper

            days_to_bday = "Не указана"
            try:
                b_day, b_month = map(int, bday.split('.'))
                today = datetime.date.today()
                next_bday = datetime.date(today.year, b_month, b_day)
                if next_bday < today:
                    next_bday = datetime.date(today.year + 1, b_month, b_day)
                days_to_bday = f"{(next_bday - today).days} дн."
            except Exception:
                pass

            stats_msg = (
                f"📊 **Статистика Агента Поддержки**\n\n"
                f"👤 **Nick_Name:** {nick}\n"
                f"📅 **Дата постановления:** {appoint}\n"
                f"⏳ **Дни:** {days}\n"
                f"✅ **Дни с нормой:** {norm_days}\n"
                f"💬 **Количество ответов:** {answers}\n"
                f"⭐ **Количество баллов:** {points}\n"
                f"⚠️ **Предупреждения:** {warns}/2\n"
                f"❌ **Выговоры:** {reprimands}/3\n"
                f"🎂 **До дня рождения:** {days_to_bday}"
            )
            send_msg(peer_id, stats_msg, keyboard=get_main_keyboard())

        # 🛣 ROAD (Путь к админке)
        elif cmd == "road":
            if not helper:
                continue

            answers = helper[6]
            norm_days = helper[5]

            ans_bar, ans_pct = generate_progress_bar(answers, 350)
            norm_bar, norm_pct = generate_progress_bar(norm_days, 10)

            total_pct = int((ans_pct + norm_pct) / 2)

            if total_pct < 30:
                grade = "🟥 Только начало пути."
            elif total_pct < 70:
                grade = "🟨 Хороший темп, продолжай!"
            elif total_pct < 100:
                grade = "🟦 Финишная прямая!"
            else:
                grade = "🟩 Готов к переводу на пост Администратора!"

            road_msg = (
                f"🛣 **Ваш путь к посту Администратора:**\n\n"
                f"📊 **Ответы:** {answers}/350\n"
                f"[{ans_bar}] {ans_pct}%\n\n"
                f"📅 **Дни с нормой:** {norm_days}/10\n"
                f"[{norm_bar}] {norm_pct}%\n\n"
                f"⭐ **Общий прогресс:** {total_pct}%\n"
                f"💡 **Оценка:** {grade}"
            )
            send_msg(peer_id, road_msg)

        # 📝 NEAK (Информация о неактиве)
        elif cmd.startswith("neak"):
            conn = sqlite3.connect("black_russia_bot.db")
            c = conn.cursor()
            c.execute("SELECT start_date, end_date, status FROM inactives WHERE vk_id = ?", (user_id,))
            inac = c.fetchone()
            conn.close()

            if inac:
                s_date, e_date, status = inac
                msg_text = (
                    f"📝 **Информация о неактиве:**\n\n"
                    f"📅 **С какого числа:** {s_date}\n"
                    f"📅 **До какого числа:** {e_date}\n"
                    f"📌 **Статус неактива:** {status}"
                )
            else:
                msg_text = "ℹ️ У вас нет зарегистрированного неактива."
            send_msg(peer_id, msg_text)

        # 💌 THANK (Анонимные пожелания)
        elif cmd.startswith("thank"):
            parts = text.split(maxsplit=2)
            if len(parts) >= 3:
                target_nick = parts[1]
                wish = parts[2]
                send_msg(peer_id, f"💌 **Анонимное пожелание для {target_nick} успешно отправлено!**\n«{wish}»")
            else:
                send_msg(peer_id, "💡 **Формат использования:**\n`thank [Nick_Name] [Текст пожелания]`")

        # 🟢 ОНЛАЙН
        elif cmd == "онлайн":
            conn = sqlite3.connect("black_russia_bot.db")
            c = conn.cursor()
            c.execute("SELECT nick_name, position FROM helpers")
            all_helpers = c.fetchall()
            conn.close()

            if not all_helpers:
                send_msg(peer_id, "📋 Список Агентов Поддержки пуст.")
                continue

            res_text = "🟢 **Список Агентов Поддержки в сети:**\n\n"
            for idx, h in enumerate(all_helpers, 1):
                res_text += f"{idx}. {h[0]} [{h[1]}]\n"
            send_msg(peer_id, res_text)

        # ⚙️ /ADMHELP (Для администрации)
        elif cmd == "/admhelp":
            if not is_admin:
                continue

            adm_text = (
                "⚙️ **Панель Управления Администрации:**\n\n"
                "🔹 `/chstats` — Список и управление Агентами Поддержки.\n"
                "🔹 `/addap [VK_ID] [Nick_Name] [Должность] [Дата]` — Поставить АП.\n"
                "🔹 `/removeap [VK_ID] [Причина]` — Снять АП с поста.\n"
                "🔹 `/setnorm [VK_ID] [+1/-1]` — Выдать/снять дни с нормой.\n"
                "🔹 `/setpoints [VK_ID] [+10/-10]` — Выдать/снять баллы.\n"
                "🔹 `/setwarn [VK_ID] [+1/-1] [Причина]` — Выдать/снять пред (0/2, 1/2, 2/2).\n"
                "🔹 `/setrep [VK_ID] [+1/-1] [Причина]` — Выдать/снять выговор (0/3, 1/3, 2/3, 3/3).\n"
                "🔹 `/setneak [VK_ID] [Дата_С] [Дата_По] [Одобрено/Отказано]` — Настроить неактив."
            )
            send_msg(peer_id, adm_text)

        # 📊 /CHSTATS (Управление составом)
        elif cmd == "/chstats":
            if not is_admin:
                continue

            conn = sqlite3.connect("black_russia_bot.db")
            c = conn.cursor()
            c.execute("SELECT vk_id, nick_name, norm_days, points, warns, reprimands FROM helpers")
            helpers_list = c.fetchall()
            conn.close()

            if not helpers_list:
                send_msg(peer_id, "📋 В базе нет зарегистрированных АП.")
                continue

            res_text = "📋 **Список Агентов Поддержки:**\n\n"
            for h in helpers_list:
                res_text += (
                    f"👤 **{h[1]}** (VK ID: `{h[0]}`)\n"
                    f"├ Дни с нормой: {h[2]} | Баллы: {h[3]}\n"
                    f"└ Предупреждения: {h[4]}/2 | Выговоры: {h[5]}/3\n"
                    f"────────────────────\n"
                )
            res_text += "\n💡 Используйте команды из `/admhelp` для управления параметрами."
            send_msg(peer_id, res_text)

        # 👑 АДМИН-КОМАНДЫ МОДИФИКАЦИИ

        # Поставить на должность
        elif cmd.startswith("/addap"):
            if not is_admin: continue
            try:
                _, target_id, nick, pos, appoint = text.split(maxsplit=4)
                target_id = int(target_id)
                add_helper(target_id, nick, pos, appoint)

                send_msg(peer_id, f"✅ Игрок **{nick}** успешно назначен на должность **{pos}**!")

                # Уведомление хелперу
                try:
                    send_msg(
                        target_id,
                        f"🎉 **Поздравляем!** Вам выдан доступ к боту Агентов Поддержки.\n\n"
                        f"👤 **Nick_Name:** {nick}\n"
                        f"💼 **Должность:** {pos}\n"
                        f"📅 **Дата постановления:** {appoint}"
                    )
                except Exception:
                    send_msg(peer_id, "⚠️ Не удалось отправить личное сообщение пользователю (закрыт ЛС).")
            except Exception:
                send_msg(peer_id, "💡 Формат: `/addap [VK_ID] [Nick_Name] [Должность] [Дата]`")

        # Снять с поста
        elif cmd.startswith("/removeap"):
            if not is_admin: continue
            try:
                _, target_id, reason = text.split(maxsplit=2)
                target_id = int(target_id)
                remove_helper(target_id)

                send_msg(peer_id, f"⛔ Пользователь ID `{target_id}` снят с поста. Причина: {reason}")
                try:
                    send_msg(target_id, f"⛔ Вы были сняты с поста Агента Поддержки.\n**Причина:** {reason}")
                except Exception:
                    pass
            except Exception:
                send_msg(peer_id, "💡 Формат: `/removeap [VK_ID] [Причина]`")

        # Выдать/снять дни с нормой
        elif cmd.startswith("/setnorm"):
            if not is_admin: continue
            try:
                _, target_id, val = text.split(maxsplit=2)
                target_id, val = int(target_id), int(val)
                update_field(target_id, "norm_days", val)
                h = get_helper(target_id)
                send_msg(peer_id, f"✅ Дни с нормой у **{h[1]}** изменены. Текущее количество: {h[5]}")
            except Exception:
                send_msg(peer_id, "💡 Формат: `/setnorm [VK_ID] [+1/-1]`")

        # Выдать/снять баллы
        elif cmd.startswith("/setpoints"):
            if not is_admin: continue
            try:
                _, target_id, val = text.split(maxsplit=2)
                target_id, val = int(target_id), int(val)
                update_field(target_id, "points", val)
                h = get_helper(target_id)
                send_msg(peer_id, f"⭐ Баллы у **{h[1]}** изменены. Текущий баланс: {h[7]}")
            except Exception:
                send_msg(peer_id, "💡 Формат: `/setpoints [VK_ID] [+10/-10]`")

        # Выдать/снять предупреждение
        elif cmd.startswith("/setwarn"):
            if not is_admin: continue
            try:
                _, target_id, val, reason = text.split(maxsplit=3)
                target_id, val = int(target_id), int(val)
                update_field(target_id, "warns", val)
                h = get_helper(target_id)
                send_msg(peer_id, f"⚠️ Предупреждение у **{h[1]}** изменено ({h[8]}/2). Причина: {reason}")
            except Exception:
                send_msg(peer_id, "💡 Формат: `/setwarn [VK_ID] [+1/-1] [Причина]`")

        # Выдать/снять выговор
        elif cmd.startswith("/setrep"):
            if not is_admin: continue
            try:
                _, target_id, val, reason = text.split(maxsplit=3)
                target_id, val = int(target_id), int(val)
                update_field(target_id, "reprimands", val)
                h = get_helper(target_id)
                send_msg(peer_id, f"❌ Выговор у **{h[1]}** изменен ({h[9]}/3). Причина: {reason}")
            except Exception:
                send_msg(peer_id, "💡 Формат: `/setrep [VK_ID] [+1/-1] [Причина]`")

        # Назначить неактив
        elif cmd.startswith("/setneak"):
            if not is_admin: continue
            try:
                _, target_id, s_date, e_date, status = text.split(maxsplit=4)
                target_id = int(target_id)
                conn = sqlite3.connect("black_russia_bot.db")
                c = conn.cursor()
                c.execute('''
                    INSERT OR REPLACE INTO inactives (vk_id, start_date, end_date, status)
                    VALUES (?, ?, ?, ?)
                ''', (target_id, s_date, e_date, status))
                conn.commit()
                conn.close()
                send_msg(peer_id, f"📝 Неактив для ID `{target_id}` установлен ({s_date} — {e_date} | {status}).")
            except Exception:
                send_msg(peer_id, "💡 Формат: `/setneak [VK_ID] [Дата_С] [Дата_По] [Одобрено/Отказано]`")
