from datetime import datetime

JIRA_BOT_TOKEN = ""
TG_BOT_TOKEN = ""

import datetime as _dt
from datetime import timezone
import logging
import os, requests, pprint
import sqlite3
import aiosqlite
import aiohttp
from functools import partial
from asyncio import to_thread
from contextlib import closing
from pathlib import Path
from atlassian import Jira
from jira import JIRA
from jira.exceptions import JIRAError
from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    CallbackQuery,
)
from telegram.error import TelegramError
from telegram.ext import (
    ApplicationBuilder,
    CallbackContext,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import json
from atlassian import Jira
import re

DB_PATH = Path("users.db")
JIRA_SERVER = "https://jira.saber3d.net"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)8s | %(name)s: %(message)s",
)
logger = logging.getLogger("report-bot")
user_states: dict[int, dict] = dict()
waiting_for_jira_username = dict()


# ------------------------------------------------------
# DB helpers
# ------------------------------------------------------
def init_db() -> None:
    """Создаёт таблицу users, если её ещё нет."""
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                tg_id INTEGER UNIQUE,
                name TEXT,
                username TEXT,
                jira_username TEXT,
                notifications_enabled INTEGER DEFAULT 1
            )
        """
        )
        conn.commit()


async def save_user(user_id: int, name: str, username: str, jira_username: str = "") -> None:
    async with aiosqlite.connect(DB_PATH) as conn:
        await conn.execute(
            """
            INSERT INTO users (tg_id, name, username, jira_username, notifications_enabled)
            VALUES (?, ?, ?, ?, 1)
            ON CONFLICT(tg_id) DO UPDATE SET
                name=excluded.name,
                username=excluded.username,
                jira_username=CASE
                              WHEN excluded.jira_username != '' THEN excluded.jira_username
                              ELSE users.jira_username
                              END
        """,
            (user_id, name, username, jira_username),
        )
        await conn.commit()


async def has_access_to_ticket(issue_key: str, token, username) -> bool:
    def check():
        jira = Jira(url=JIRA_SERVER, token=token)
        users = jira.get_users_with_browse_permission_to_a_project(
            username=username,
            project_key=issue_key
        )
        return bool(users)

    return await to_thread(check)


def get_projects(token):
    jira_url = "https://jira.saber3d.net"

    session = requests.Session()
    session.headers.update({
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    })

    def get_all_projects():
        try:
            url = f"{jira_url}/rest/api/2/project"
            resp = session.get(url, timeout=20)
            resp.raise_for_status()
            return resp.json()
        except:
            return []

    def extract_name_key_mapping(json_data):
        if isinstance(json_data, str):
            data = json.loads(json_data)
        else:
            data = json_data
        return {item['name']: item['key'] for item in data if 'name' in item and 'key' in item}

    def find_reporting_or_time_tracking_issues(project_name, project_key):
        jira = Jira(
            url="https://jira.saber3d.net",
            token=token,
        )
        jql = (
            f'project = "{project_key}" AND '
            f'(issuetype = "Reporting Ticket" OR summary ~ "time tracking")'
        )

        issues = jira.jql(jql).get("issues", [])

        result = []
        for issue in issues:
            key = issue["key"]
            summary = issue["fields"]["summary"]
            issue_type = issue["fields"]["issuetype"]["name"]
            result.append((project_name, key, issue_type, summary))

        return result

    projects_json = get_all_projects()
    projects_dict = extract_name_key_mapping(projects_json)
    result = []

    for project_name, project_key in projects_dict.items():
        result.extend(find_reporting_or_time_tracking_issues(project_name, project_key))

    result_dict = {
        f"{ticket[3]}/{ticket[0]}": ticket[1]
        for ticket in result
    }

    return result_dict


async def log_time_to_ticket(jira_server, token, worker, issue_key, time_hours):
    time_seconds = int(time_hours * 3600)
    endpoint = f"{jira_server}/rest/tempo-timesheets/4/worklogs"
    payload = {
        "originTaskId": issue_key,
        "timeSpentSeconds": time_seconds,
        "billableSeconds": time_seconds,
        "started": datetime.now(timezone.utc).isoformat(timespec='milliseconds').replace('+00:00', 'Z'),
        "comment": f"Logged via Telegram bot\nWorking on issue {issue_key}",
        "worker": worker,
        "includeNonWorkingDays": False
    }

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json",
        "Authorization": f"Bearer {token}"
    }

    async with aiohttp.ClientSession(headers=headers) as session:
        async with session.post(endpoint, json=payload, timeout=30) as resp:
            try:
                response_data = await resp.json()
                logger.info(response_data)
            except aiohttp.ContentTypeError:
                text = await resp.text()
                logger.info(text)

            resp.raise_for_status()


def shorten_project_name(project_key: str) -> str:
    """
    :param project_key: саммери тикета для репорта
    :return: сокращенная строчка для создания кнопки
    """
    key = project_key.lower()

    junk_keywords = [
        "qa time tracking", "time tracking", "выполнения ранов",
        "задачи по процессам", "qa_project", "spl", "qa spl"
    ]

    replacements = {
        "world war z": "WWZ",
        "world war z vr": "WWZVR",
        "mudrunner vr": "MVR",
        "shockwave": "SHV",
        "codex": "COD",
        "training (advanced)": "TADV",
        "magnus": "MGSSPL",
        "alaska": "AL",
        "amber": "AMB",
        "husky": "HSK",
        "red sand": "RS",
        "road builder": "RB",
        "thunder": "TNDR",
        "playground": "PG",
    }

    for junk in junk_keywords:
        key = key.replace(junk, '')


    key = re.sub(r'[^\w\s/()-]', '', key)
    key = re.sub(r'\s+', ' ', key).strip()

    for full, short in replacements.items():
        key = key.replace(full, short)

    words = key.upper().split('/')
    seen = set()
    result = []
    for word in words:
        if word not in seen:
            result.append(word)
            seen.add(word)

    return ' / '.join(result)


PROJECTS: dict[str, str] = get_projects(token=JIRA_BOT_TOKEN)


# ------------------------------------------------------
# Bot handlers
# ------------------------------------------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await save_user(user.id, user.full_name, user.username or "", "")


    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "UPDATE users SET notifications_enabled=1 WHERE tg_id=?", (user.id,)
        )
        conn.commit()
    await update.message.reply_text("Уведомления включены!\n/help - справка.")


# async def unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
#     await update.message.reply_text("Неизвестная команда. /help — список команд.")


async def off(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    with closing(sqlite3.connect(DB_PATH)) as conn:
        conn.execute(
            "UPDATE users SET notifications_enabled=0 WHERE tg_id=?", (user.id,)
        )
        conn.commit()
    await update.message.reply_text("Уведомления выключены.")


async def jira_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    waiting_for_jira_username[user_id] = True
    await update.message.reply_text("Введите ваш Jira username:")



async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "/start — включить уведомления\n"
        "/off   — выключить уведомления\n"
        "/report— выбрать проект и залогировать время\n"
        "/help  — эта справка\n"
        "/jira - команда для ввода юзернейма "
    )


async def send_project_keyboard(
    chat_id: int, user_id: int, context: ContextTypes.DEFAULT_TYPE
):

    with closing(sqlite3.connect(DB_PATH)) as conn:
        row = conn.execute(
            "SELECT jira_username FROM users WHERE tg_id=?", (user_id,)
        ).fetchone()

    if not row or not row[0]:
        await context.bot.send_message(
            chat_id=chat_id,
            text="Jira username не задан. Отправьте его в ответ на это сообщение.",
        )
        waiting_for_jira_username[user_id] = True
        return

    jira_username = row[0]

    accessible = {}
    for name, key in PROJECTS.items():
        if await has_access_to_ticket(key.split("-")[0], JIRA_BOT_TOKEN, jira_username):
            accessible[name] = key

    if not accessible:
        await context.bot.send_message(chat_id=chat_id, text="❌ Нет доступа к проектам.")
        return


    buttons = [
        InlineKeyboardButton(shorten_project_name(name), callback_data=f"project_{key}")
        for name, key in accessible.items()
    ]
    keyboard = [buttons[i: i + 2] for i in range(0, len(buttons), 2)]

    await context.bot.send_message(
        chat_id=chat_id,
        text="Выберите проект:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )



async def report_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_project_keyboard(
        chat_id=update.effective_chat.id,
        user_id=update.effective_user.id,
        context=context,
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    # 1) Принимаем и сохраняем JIra username
    if waiting_for_jira_username.pop(user_id, False):
        with closing(sqlite3.connect(DB_PATH)) as conn:
            conn.execute(
                "UPDATE users SET jira_username=? WHERE tg_id=?", (text, user_id)
            )
            conn.commit()
        await update.message.delete()
        await update.message.reply_text("Jira username сохранён ✔︎")
        return

    # 2) Ожидаем количество часов
    if user_id in user_states and user_states[user_id]["state"] == "awaiting_time":
        if text.isdigit() and 1 <= int(text) <= 8:
            hours = int(text)
            issue_key = user_states[user_id]["issue_key"]

            with closing(sqlite3.connect(DB_PATH)) as conn:
                row = conn.execute(
                    "SELECT jira_username FROM users WHERE tg_id=?", (user_id,)
                ).fetchone()
            if not row or not row[0]:
                await update.message.reply_text("Jira username не задан. Отправьте его текстом.")
                waiting_for_jira_username[user_id] = True
                return

            jira_username = row[0]
            try:
                await log_time_to_ticket(
                    jira_server=JIRA_SERVER,
                    token=JIRA_BOT_TOKEN,
                    worker=jira_username,
                    issue_key=issue_key,
                    time_hours=hours
                )
                await update.message.reply_text("Время залогировано ✔\nВнести ещё время — /report")
            except Exception as exc:
                await update.message.reply_text(f"Ошибка: {exc}")
            user_states.pop(user_id, None)
        else:
            await update.message.reply_text("Введите число от 1 до 8.")
        return

    await update.message.reply_text("Не понял. /help — список команд.")


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query: CallbackQuery = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "report_time":
        await send_project_keyboard(
            chat_id=query.message.chat.id,
            user_id=user_id,
            context=context,
        )
        return

    if query.data.startswith("project_"):
        issue_key = query.data.split("_", 1)[1]
        user_states[user_id] = {"state": "awaiting_time", "issue_key": issue_key}

        buttons = [
            [
                InlineKeyboardButton("8 часов", callback_data="log_8"),
                InlineKeyboardButton("Другое число", callback_data="log_custom")
            ]
        ]

        try:
            await query.edit_message_reply_markup(reply_markup=None)
        except TelegramError:
            pass

        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text=f"Сколько часов залогировать в {issue_key}?\n"
                 f"Можете нажать кнопку или ввести число (1–8) вручную:",
            reply_markup=InlineKeyboardMarkup(buttons)
        )
        return

    if query.data == "log_custom":
        state = user_states.get(user_id)
        if not state or "issue_key" not in state:
            await query.answer("Проект не выбран.")
            return

        hour_buttons = []
        for i in range(1, 9):
            hour_buttons.append(
                InlineKeyboardButton(f"{i} ч.", callback_data=f"log_{i}")
            )

        button_rows = [hour_buttons[i:i+4] for i in range(0, len(hour_buttons), 4)]

        await context.bot.send_message(
            chat_id=query.message.chat.id,
            text="Выберите количество часов или введите вручную (1–8):",
            reply_markup=InlineKeyboardMarkup(button_rows)
        )
        return

    if query.data.startswith("log_"):
        time_str = query.data.split("_")[1]
        try:
            time_hours = int(time_str)
            if not (1 <= time_hours <= 8):
                raise ValueError("Неверное число")
        except Exception:
            await context.bot.send_message(
                chat_id=query.message.chat.id,
                text="Неверное количество часов."
            )
            return

        state = user_states.get(user_id)
        if not state or "issue_key" not in state:
            await context.bot.send_message(
                chat_id=query.message.chat.id,
                text="Проект не выбран."
            )
            return

        issue_key = state["issue_key"]

        with closing(sqlite3.connect(DB_PATH)) as conn:
            row = conn.execute(
                "SELECT jira_username FROM users WHERE tg_id=?", (user_id,)
            ).fetchone()

        if not row or not row[0]:
            await context.bot.send_message(
                chat_id=query.message.chat.id,
                text="Jira username не задан. Отправьте его текстом."
            )
            waiting_for_jira_username[user_id] = True
            return

        jira_username = row[0]

        try:
            await log_time_to_ticket(
                jira_server=JIRA_SERVER,
                token=JIRA_BOT_TOKEN,
                worker=jira_username,
                issue_key=issue_key,
                time_hours=time_hours
            )
            await context.bot.send_message(
                chat_id=query.message.chat.id,
                text=f"{time_hours} ч. залогировано ✔\nВнести ещё — /report"
            )
        except Exception as exc:
            await context.bot.send_message(
                chat_id=query.message.chat.id,
                text=f"Ошибка: {exc}"
            )

        user_states.pop(user_id, None)
        return

    logger.warning("Неизвестный callback_data: %s", query.data)


async def send_reminders(context: CallbackContext):
    today = _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=3)))  # UTC+3 — Москва
    if today.weekday() >= 5:  # 5 = суббота, 6 = воскресенье
        return

    with closing(sqlite3.connect(DB_PATH)) as conn:
        rows = conn.execute(
            "SELECT tg_id FROM users WHERE notifications_enabled=1"
        ).fetchall()

    for (tg_id,) in rows:
        keyboard = InlineKeyboardMarkup(
            [[InlineKeyboardButton("Зарепортить время", callback_data="report_time")]]
        )
        await context.bot.send_message(
            chat_id=tg_id,
            text="⏰ Пора репортить время!",
            reply_markup=keyboard,
        )


# ------------------------------------------------------
# Main entry point
# ------------------------------------------------------
def main() -> None:
    init_db()

    app = ApplicationBuilder().token(TG_BOT_TOKEN).build()
    job_queue = app.job_queue
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("off", off))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("report", report_command))
    # app.add_handler(MessageHandler(filters.COMMAND, unknown_command))
    app.add_handler(CommandHandler("jira", jira_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(CallbackQueryHandler(button_handler))

    # ежедневный пуш (UTC+3 — Москва)
    job = job_queue.run_repeating(
        send_reminders,
        interval=86400,
        first=_dt.datetime.combine(
            _dt.datetime.now(_dt.timezone(_dt.timedelta(hours=3))).date(),
            _dt.time(hour=18, minute=30),
            tzinfo=_dt.timezone(_dt.timedelta(hours=3))
        ),
        name="daily_reminder"
    )

    job.job.misfire_grace_time = 60

    logger.info("Бот запущен.")
    app.run_polling()


if __name__ == "__main__":
    main()