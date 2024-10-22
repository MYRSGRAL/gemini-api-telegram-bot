import json
import os
from config import DEFAULT_MODEL
import asyncio

def load_settings():
    if not os.path.exists('settings.json'):
        with open('settings.json', 'w') as file:
            json.dump({}, file, ensure_ascii=False, indent=4)  # Initialize as an empty dictionary
    try:
        with open('settings.json', 'r') as file:
            return json.load(file)
    except Exception as e:
        print(e)
        return {}

def save_settings(settings):
    with open('settings.json', 'w') as file:
        json.dump(settings, file, ensure_ascii=False, indent=4)

def get_user_model(settings, user_id):
    return settings.get(str(user_id), DEFAULT_MODEL)

async def set_user_model(settings, user_id, model_name):
    settings[str(user_id)] = model_name
    save_settings(settings)
    await asyncio.sleep(0.1)
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
