import json
import os
import sqlite3

from config import DEFAULT_MODEL, Default_send_model_name

conn = sqlite3.connect('usr_settings.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER,
        model TEXT,
        send_model_name INTEGER
    )
''')
conn.commit()


def check_user_account(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()
    send_model_name = 1 if Default_send_model_name is True else 0
    if not existing_user:
        cursor.execute("INSERT INTO users (send_model_name, model, user_id) VALUES (?, ?, ?)",
                       (send_model_name, DEFAULT_MODEL, user_id))
        conn.commit()
    return True


def get_user_model(user_id):
    check_user_account(user_id)
    cursor.execute("SELECT model FROM users WHERE user_id = ?", (user_id,))
    model_name = cursor.fetchone()
    if not model_name:
        return DEFAULT_MODEL
    else:
        return model_name[0]


def get_user_send_model_name(user_id):
    check_user_account(user_id)
    cursor.execute("SELECT send_model_name FROM users WHERE user_id = ?", (user_id,))
    send_model_name = cursor.fetchone()
    send_model_name = True if send_model_name[0] == 1 else False
    return send_model_name


async def set_user_model(user_id, model_name):
    check_user_account(user_id)
    cursor.execute("UPDATE users SET model = ? WHERE user_id = ?", (model_name, user_id))
    conn.commit()
    return True


async def set_user_send_model_name(user_id):
    check_user_account(user_id)
    send_model_name = get_user_send_model_name(user_id)
    send_model_name_db = 1 if send_model_name is False else 0
    cursor.execute("UPDATE users SET send_model_name = ? WHERE user_id = ?", (send_model_name_db, user_id))
    conn.commit()
    return True


def load_conversation_history(history_json):
    try:
        if os.path.getsize(history_json) == 0:
            return []
        with open(history_json, 'r') as file:
            history = json.load(file)
            if not isinstance(history, list):
                history = []
            return history
    except FileNotFoundError:
        return []


def save_conversation_history(history, history_json):
    with open(history_json, 'w') as file:
        json.dump(history, file, ensure_ascii=False, indent=4)


def delete_folder(folder_path):
    try:
        for root, dirs, files in os.walk(folder_path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder_path)
    except Exception:
        pass
