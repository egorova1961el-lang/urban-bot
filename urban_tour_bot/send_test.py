import os
from pathlib import Path
import requests

ROOT = Path(__file__).parent
ENV = ROOT / '.env'
ADMIN_FILE = ROOT / 'admin_chat.txt'

def read_env(key: str):
    if ENV.exists():
        for line in ENV.read_text(encoding='utf-8').splitlines():
            if line.strip().startswith(key + "="):
                return line.split('=', 1)[1].strip()
    return os.getenv(key)


def main():
    token = read_env('TELEGRAM_BOT_TOKEN')
    chat = None
    if ADMIN_FILE.exists():
        chat = ADMIN_FILE.read_text(encoding='utf-8').strip()
    if not chat:
        chat = read_env('TELEGRAM_CHAT_ID')

    if not token or not chat:
        print('ERROR: missing TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID/admin_chat.txt')
        return

    text = (
        '📌 Тестовая заявка (авто)\n'
        '• Имя / компания / должность: Тест Тестов, Тестовая компания, Менеджер\n'
        '• Роль / профиль: Девелопер\n'
        '• Что интересно: программа, даты, партнёрство\n'
        '• Контакты: +7 900 000 00 00\n'
    )

    resp = requests.post(f'https://api.telegram.org/bot{token}/sendMessage', data={'chat_id': chat, 'text': text})
    print('HTTP', resp.status_code)
    print(resp.text)


if __name__ == '__main__':
    main()
