#!/usr/bin/env bash
# Запуск для macOS / Linux: ./start.sh
cd "$(dirname "$0")" || exit 1

if ! command -v python3 >/dev/null 2>&1; then
    echo "Нужен Python 3. Установите его: https://www.python.org/downloads/"
    exit 1
fi

if [ ! -d .venv ]; then
    python3 -m venv .venv || exit 1
fi

if [ ! -f .venv/deps_ok ]; then
    echo "Ставлю зависимости, это один раз..."
    .venv/bin/python -m pip install --upgrade pip -q
    .venv/bin/python -m pip install -r requirements.txt || exit 1
    touch .venv/deps_ok
fi

.venv/bin/python main.py
