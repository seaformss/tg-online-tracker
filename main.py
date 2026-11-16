"""Telegram Online Tracker - простая версия.

Всё настраивается при первом запуске (ключи, юзернеймы), данные сохраняются
в config.json рядом со скриптом. Смена онлайна пишется в консоль и в
online_log.csv.
"""
import asyncio
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

from telethon import TelegramClient
from telethon.errors import ApiIdInvalidError, FloodWaitError
from telethon.tl.functions.users import GetUsersRequest
from telethon.tl.types import UserStatusOffline, UserStatusOnline

BASE = Path(__file__).resolve().parent
CONFIG_FILE = BASE / "config.json"
LOG_FILE = BASE / "online_log.csv"
SESSION_FILE = str(BASE / "tracker")  # создаст tracker.session

MIN_INTERVAL = 10  # чаще опрашивать нельзя: Telegram включит ограничение


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def ask_config():
    print("Первый запуск. Настройки сохранятся в config.json.")
    print("Ключи api_id и api_hash берутся на https://my.telegram.org/apps\n")
    while True:
        try:
            api_id = int(input("api_id (число): ").strip())
            break
        except ValueError:
            print("Нужно число, попробуйте ещё раз.")
    api_hash = input("api_hash: ").strip()
    raw = input("Юзернеймы через запятую (без @, например ivan_petrov, anna_s): ")
    usernames = [u.strip().lstrip("@") for u in raw.split(",") if u.strip()]
    cfg = {
        "api_id": api_id,
        "api_hash": api_hash,
        "usernames": usernames,
        "pairs": [],  # например [["ivan_petrov", "anna_s"]]
        "interval": 20,  # секунд между проверками (минимум 10)
    }
    CONFIG_FILE.write_text(json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\nСохранено в config.json (удалите этот файл, чтобы настроить заново).\n")
    return cfg


def load_config():
    if not CONFIG_FILE.exists():
        return ask_config()
    try:
        cfg = json.loads(CONFIG_FILE.read_text(encoding="utf-8"))
        for key in ("api_id", "api_hash", "usernames"):
            if key not in cfg:
                raise KeyError(key)
        cfg["api_id"] = int(cfg["api_id"])
        return cfg
    except Exception as e:
        print(f"config.json повреждён ({e}). Удалите его и запустите заново.")
        sys.exit(1)


def describe(status):
    """Возвращает (состояние, время последнего визита)."""
    if isinstance(status, UserStatusOnline):
        return "online", ""
    if isinstance(status, UserStatusOffline):
        return "offline", status.was_online.astimezone().strftime("%Y-%m-%d %H:%M:%S")
    return "hidden", ""  # «недавно», «на этой неделе» и т.п. - точного статуса нет


def display_name(user, fallback):
    parts = [getattr(user, "first_name", None) or "", getattr(user, "last_name", None) or ""]
    return " ".join(p for p in parts if p) or fallback


LABELS = {
    "online": "в сети",
    "offline": "не в сети",
    "hidden": "статус скрыт (недавно / давно)",
}


def log_row(name, display, state, seen):
    new_file = not LOG_FILE.exists()
    with open(LOG_FILE, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new_file:
            w.writerow(["время", "username", "имя", "состояние", "был(а) в сети"])
        w.writerow([now(), name, display, state, seen])


async def run():
    cfg = load_config()
    interval = max(MIN_INTERVAL, int(cfg.get("interval", 20)))
    pairs = [tuple(p) for p in cfg.get("pairs", []) if len(p) == 2]

    client = TelegramClient(SESSION_FILE, cfg["api_id"], cfg["api_hash"])
    # При первом входе спросит номер телефона и код из Telegram.
    async with client:
        print("Подключено к Telegram.\n")
        inputs = {}
        for name in cfg["usernames"]:
            try:
                inputs[name] = await client.get_input_entity(name)
            except Exception as e:
                print(f"Не нашёл пользователя '{name}': {e}")
        if not inputs:
            print("Некого отслеживать. Проверьте юзернеймы в config.json.")
            return

        names = list(inputs)
        print(f"Слежу за: {', '.join(names)}. Проверка каждые {interval} сек. Остановка: Ctrl+C.\n")
        last = {}
        last_pair = {}

        while True:
            try:
                users = await client(GetUsersRequest([inputs[n] for n in names]))
            except FloodWaitError as e:
                print(f"[{now()}] Telegram просит подождать {e.seconds} сек. Жду.")
                await asyncio.sleep(e.seconds + 5)
                continue
            except Exception as e:
                print(f"[{now()}] Ошибка: {e}. Повтор через 30 сек.")
                await asyncio.sleep(30)
                continue

            states = {}
            for name, user in zip(names, users):
                state, seen = describe(getattr(user, "status", None))
                states[name] = state
                if last.get(name) != state:
                    last[name] = state
                    display = display_name(user, name)
                    extra = f" (был(а): {seen})" if seen else ""
                    print(f"[{now()}] {display} (@{name}): {LABELS[state]}{extra}")
                    log_row(name, display, state, seen)

            for a, b in pairs:
                if a in states and b in states and states[a] == states[b] and states[a] in ("online", "offline"):
                    key = (a, b)
                    if last_pair.get(key) != states[a]:
                        last_pair[key] = states[a]
                        word = "в сети" if states[a] == "online" else "не в сети"
                        print(f"[{now()}] {a} и {b} оба сейчас {word}")
                else:
                    last_pair.pop((a, b), None)

            await asyncio.sleep(interval)


def main():
    try:
        asyncio.run(run())
    except KeyboardInterrupt:
        print("\nОстановлено.")
    except ApiIdInvalidError:
        print("api_id или api_hash неверные. Удалите config.json и введите ключи заново.")


if __name__ == "__main__":
    main()
