import asyncio
import json
import logging
import os
import PIL.Image
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import ContentType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message, callback_query

from config import API_TOKEN, GOOGLE_API_KEY_list


bot = Bot(token=API_TOKEN)
dp = Dispatcher()

if not os.path.exists('media'):
    os.makedirs('media')

DEFAULT_MODEL = 'gemini-1.5-flash'


def load_settings():
    try:
        with open('settings.json', 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        return {}


def save_settings(settings):
    with open('settings.json', 'w') as file:
        json.dump(settings, file, ensure_ascii=False, indent=4)


settings = load_settings()


def get_user_model(user_id):
    return settings.get(str(user_id), DEFAULT_MODEL)


def set_user_model(user_id, model):
    settings[str(user_id)] = model
    save_settings(settings)


history_json = None


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


@dp.message(Command("start"))
async def cmd_start(message: Message):
    registration_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Сменить модель", callback_data="Change_model")]
    ])
    await message.answer("Салам \nДадада это тот самый бот вашего всемогущего господина \n \nУ бота есть две модели gemini-1.5-pro и gemini-1.5-flash\ngemini-1.5-pro для более сложных задач \ngemini-1.5-flash более быстая и для простых задач \nУ модели gemini-1.5-flash больше запросов",
                         reply_markup=registration_keyboard)


@dp.callback_query(
    lambda c: c.data in ["Del_history", "Change_model"])
async def handle_button_click(callback_query: types.CallbackQuery):
    match callback_query.data:
        case "Del_history":
            await Clear_history(callback_query.message)
        case "Change_model":
            user_id = callback_query.from_user.id
            current_model = get_user_model(user_id)
            new_model = 'gemini-1.5-pro' if current_model == 'gemini-1.5-flash' else 'gemini-1.5-flash'
            set_user_model(user_id, new_model)
            registration_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Очистить историю", callback_data="Del_history")],
                [InlineKeyboardButton(text="Сменить модель", callback_data="Change_model")]
            ])
            await callback_query.message.answer(f"Модель изменена на  {new_model}", reply_markup=registration_keyboard)


def delete_folder(folder_path):
    try:
        for root, dirs, files in os.walk(folder_path, topdown=False):
            for name in files:
                os.remove(os.path.join(root, name))
            for name in dirs:
                os.rmdir(os.path.join(root, name))
        os.rmdir(folder_path)
    except Exception as e:
        pass


@dp.message(Command("clear"))
async def Clear_history(message: types.Message):
    if message.chat.id is None:
        history_json = f'{callback_query.from_user.id}.json'
        media_dir = f'media/{callback_query.from_user.id}'
    else:
        history_json = f'{message.chat.id}.json'
        media_dir = f'media/{message.chat.id}'

    with open(history_json, 'w') as file:
        file.truncate(0)
    delete_folder(media_dir)
    await message.answer("Истроия очищена")


@dp.message()
async def handle_message(message: Message):
    for GOOGLE_API in GOOGLE_API_KEY_list:
        try:
            genai.configure(api_key=GOOGLE_API)
            history_json = f'{message.chat.id}.json'
            if not os.path.exists(history_json):
                open(history_json, 'w').close()
            conversation_history = load_conversation_history(history_json)

            if message.content_type == ContentType.TEXT:
                text = message.text
                if len(text) > 4000:
                    registration_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Очистить историю", callback_data="Del_history")],
                        [InlineKeyboardButton(text="Сменить модель", callback_data="Change_model")]
                    ])
                    await message.answer("Максимальная длина сообщения 4000 символов", reply_markup=registration_keyboard)
                    break
                conversation_history.append({"role": "user", "parts": [{"text": text}]})
            elif message.content_type == ContentType.PHOTO:
                caption = message.caption
                text = caption
                if len(text) > 1000:
                    registration_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Очистить историю", callback_data="Del_history")],
                        [InlineKeyboardButton(text="Сменить модель", callback_data="Change_model")]
                    ])
                    await message.answer("Максимальная длина подписи фото 1000 символов",
                                         reply_markup=registration_keyboard)
                    break
                photo = message.photo[-1]
                file_info = await bot.get_file(photo.file_id)
                file_path = file_info.file_path
                telegram_id = message.from_user.id
                media_dir = f'media/{telegram_id}'
                if not os.path.exists(media_dir):
                    os.makedirs(media_dir)
                file_name = f'{media_dir}/{photo.file_id}.jpg'
                await bot.download_file(file_path, file_name)
                image = PIL.Image.open(file_name)
                if image is None:
                    raise ValueError("Failed to open image")
                conversation_history.append({"role": "user", "parts": [{"text": text}]})
            elif message.content_type == ContentType.DOCUMENT:
                caption = message.caption
                text = caption
                if len(text) > 1000:
                    registration_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Очистить историю", callback_data="Del_history")],
                        [InlineKeyboardButton(text="Сменить модель", callback_data="Change_model")]
                    ])
                    await message.answer("Максимальная длина подписи файла 1000 символов",
                                         reply_markup=registration_keyboard)
                    break
                document = message.document
                file_info = await bot.get_file(document.file_id)
                file_path = file_info.file_path
                telegram_id = message.from_user.id
                media_dir = f'media/{telegram_id}'
                if not os.path.exists(media_dir):
                    os.makedirs(media_dir)
                file_name = f'{media_dir}/{document.file_name}'
                await bot.download_file(file_path, file_name)
                if not message.document.mime_type == "application/pdf":
                    upload_file_s = genai.upload_file(file_name)
                    conversation_history.append({"role": "user", "parts": [{"text": text}]})
                    registration_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Очистить историю", callback_data="Del_history")],
                        [InlineKeyboardButton(text="Сменить модель", callback_data="Change_model")]
                    ])
                    await message.answer("Поддерживается только pdf", reply_markup=registration_keyboard)
                    break

            user_id = message.from_user.id
            model_name = get_user_model(user_id)
            model = genai.GenerativeModel(model_name)

            if message.content_type == ContentType.TEXT:
                chat_session = model.start_chat(history=conversation_history)
                response = chat_session.send_message(text)
            elif message.content_type == ContentType.PHOTO:
                if caption is None:
                    registration_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Очистить историю", callback_data="Del_history")],
                        [InlineKeyboardButton(text="Сменить модель", callback_data="Change_model")]
                    ])
                    await message.answer("Пожалуйста, введите подпись к изображению",
                                         reply_markup=registration_keyboard)
                    break
                else:
                    text = caption
                    response = model.generate_content([text, image])
            elif message.content_type == ContentType.DOCUMENT:
                if caption is None:
                    registration_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="Очистить историю", callback_data="Del_history")],
                        [InlineKeyboardButton(text="Сменить модель", callback_data="Change_model")]
                    ])
                    await message.answer("Пожалуйста, введите подпись к изображению",
                                         reply_markup=registration_keyboard)
                else:
                    text = caption
                    response = model.generate_content([text, upload_file_s])

            conversation_history.append({"role": "model", "parts": [{"text": response.text}]})
            save_conversation_history(conversation_history, history_json)

            registration_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="Очистить историю", callback_data="Del_history")],
                [InlineKeyboardButton(text="Сменить модель", callback_data="Change_model")]
            ])
            await message.answer(response.text, reply_markup=registration_keyboard)
            break

        except Exception as e:
            print(e)
            pass


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
