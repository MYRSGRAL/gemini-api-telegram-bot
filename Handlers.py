import json
import os
import sqlite3
import google.generativeai as genai

from config import DEFAULT_MODEL, Default_send_model_name, Default_temperature_user, Default_only_ru, Default_parse_mode

conn = sqlite3.connect('usr_settings.db', check_same_thread=False)
cursor = conn.cursor()
cursor.execute('''
    CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER,
        model TEXT,
        send_model_name INTEGER,
        temperature_user INTEGER,
        only_ru INTEGER,
        parse_mode INTEGER
    )
''')
conn.commit()


def check_user_account(user_id):
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    existing_user = cursor.fetchone()
    send_model_name = 1 if Default_send_model_name is True else 0
    only_ru = 1 if Default_only_ru is True else 0
    parse_mode = 1 if Default_parse_mode is True else 0
    if not existing_user:
        cursor.execute("INSERT INTO users (send_model_name, model, user_id, temperature_user, only_ru, parse_mode) VALUES (?, ?, ?, ?, ?, ?)",
                       (send_model_name, DEFAULT_MODEL, user_id, Default_temperature_user, only_ru, parse_mode))
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


def get_user_temperature(user_id):
    check_user_account(user_id)
    cursor.execute("SELECT temperature_user FROM users WHERE user_id = ?", (user_id,))
    temperature_user = cursor.fetchone()
    return temperature_user[0]

def get_user_only_ru(user_id):
    check_user_account(user_id)
    cursor.execute("SELECT only_ru FROM users WHERE user_id = ?", (user_id,))
    only_ru = cursor.fetchone()
    only_ru = True if only_ru[0] == 1 else False
    return only_ru

def get_user_parse_mode(user_id):
    check_user_account(user_id)
    cursor.execute("SELECT parse_mode FROM users WHERE user_id = ?", (user_id,))
    parse_mode = cursor.fetchone()
    parse_mode = True if parse_mode[0] == 1 else False
    return parse_mode

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


async def set_user_temperature(user_id, temperature):
    check_user_account(user_id)
    cursor.execute("UPDATE users SET temperature_user = ? WHERE user_id = ?", (temperature, user_id))
    conn.commit()
    return True

async def set_user_only_ru(user_id):
    check_user_account(user_id)
    only_ru = get_user_only_ru(user_id)
    only_ru_db = 1 if only_ru is False else 0
    cursor.execute("UPDATE users SET only_ru = ? WHERE user_id = ?", (only_ru_db, user_id))
    conn.commit()
    return True

async def set_user_parse_mode(user_id):
    check_user_account(user_id)
    parse_mode = get_user_parse_mode(user_id)
    parse_mode_db = 1 if parse_mode is False else 0
    cursor.execute("UPDATE users SET parse_mode = ? WHERE user_id = ?", (parse_mode_db, user_id))
    conn.commit()
    return True

def load_conversation_history(history_json):
    try:
        if os.path.getsize(history_json) == 0:
            return []
        with open(history_json, 'r', encoding='utf-8') as file:
            history = json.load(file)
            if not isinstance(history, list):
                history = []
            return history
    except FileNotFoundError:
        return []


def save_conversation_history(history, history_json):
    with open(history_json, 'w', encoding='utf-8') as file:
        json.dump(history, file, ensure_ascii=False, indent=4)


def delete_folder(folder_path):
    try:
        for root, dirs, files in os.walk(folder_path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder_path)
    except:
        pass

async def download_and_upload_file(bot, file_id, file_type, user_id, file_name):
    file_info = await bot.get_file(file_id)
    file_path = file_info.file_path
    media_dir = f'media/{user_id}'
    if not os.path.exists(media_dir):
        os.makedirs(media_dir)
    file_name = f'{media_dir}/{file_name}'
    await bot.download_file(file_path, file_name)
    uploaded_file = genai.upload_file(file_name)
    return uploaded_file