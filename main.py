import asyncio
import os
import PIL.Image
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import ContentType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message, callback_query
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.utils.chat_action import ChatActionSender
from aiogram.enums import ChatAction

from config import (API_TOKEN, GOOGLE_API_KEY_list)
from Handlers import (load_settings, get_user_model, set_user_model, load_conversation_history,
                      save_conversation_history, delete_folder)

bot = Bot(token=API_TOKEN)
default = DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher()

if not os.path.exists('media'):
    os.makedirs('media')

module_config = {
    "temperature": 0.9,
    "max_output_tokens": 4000
}

generation_config = {
    "temperature": module_config.get("temperature", 0.9),
    "max_output_tokens": module_config.get("max_output_tokens", 4000)
}

settings = load_settings()

stop_generation = False

@dp.message(Command("start"))
async def cmd_start(message: Message):
    main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
        [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")],
    ])
    await message.answer(
        "👋 Добро пожаловать! ✨\n\n🤖 Я — большая языковая модель, и у меня есть две версии: gemini-1.5-pro и gemini-1.5-flash.\n\n🧠 gemini-1.5-pro — для решения сложных задач, требующих глубокого анализа. 🤯\n⚡ gemini-1.5-flash — быстрая и эффективная версия для простых вопросов. 💨\n\n☝️  gemini-1.5-flash имеет больший лимит запросов. 😉\n\n🧹 Не забывайте очищать историю для начала нового диалога или при отправке большого сообщения. \n\n✨ Готов ответить на ваши вопросы! ✨",
        reply_markup=main_keyboard)


@dp.callback_query(lambda c: c.data in ["Del_history", "Change_model", "Gemini-1.5-flash", "Gemini-1.5-pro", "break_generation"])
async def handle_button_click(callback_query: types.CallbackQuery):
    main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
        [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")],
    ])
    match callback_query.data:
        case "Del_history":
            await clear_history(callback_query.message)
        case "Change_model":
            await change_model(callback_query.message)
        case "Gemini-1.5-flash":
            await set_user_model(settings, callback_query.from_user.id, "gemini-1.5-flash")
            await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        text="⚡ Gemini-1.5-flash", reply_markup=main_keyboard)
        case "Gemini-1.5-pro":
            await set_user_model(settings, callback_query.from_user.id, "gemini-1.5-pro")
            await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        text="🧠 Gemini-1.5-pro", reply_markup=main_keyboard)
        case "break_generation":
            global stop_generation
            stop_generation = True


@dp.message(Command("Change_model"))
async def change_model(message: Message):
    user_id = message.chat.id if message.chat.id is not None else message.from_user.id
    current_model = get_user_model(settings, user_id)
    if current_model == 'gemini-1.5-flash':
        main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡  Gemini-1.5-flash ✅", callback_data="Gemini-1.5-flash")],
            [InlineKeyboardButton(text="🧠 Gemini-1.5-pro", callback_data="Gemini-1.5-pro")]
        ])
    elif current_model == 'gemini-1.5-pro':
        main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🧠 Gemini-1.5-pro ✅ ", callback_data="Gemini-1.5-pro")],
            [InlineKeyboardButton(text="⚡  Gemini-1.5-flash", callback_data="Gemini-1.5-flash")]
        ])
    await message.answer("Выберете модель ⚙️", reply_markup=main_keyboard)


@dp.message(Command("clear"))
async def clear_history(message: types.Message):
    if message.chat.id is None:
        history_json = f'{callback_query.from_user.id}.json'
        media_dir = f'media/{callback_query.from_user.id}'
    else:
        history_json = f'{message.chat.id}.json'
        media_dir = f'media/{message.chat.id}'

    with open(history_json, 'w') as file:
        file.truncate(0)
    delete_folder(media_dir)
    await message.answer("🧹 История очищена")


@dp.message()
async def handle_message(message: Message):
    global stop_generation
    main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛑 Прекратить генерацию", callback_data="break_generation")],
    ])
    msg = await message.answer("Пожалуйста, подождите, идет обработка запроса", reply_markup=main_keyboard)
    async with ChatActionSender(action=ChatAction.TYPING, chat_id=message.chat.id, bot=bot):
        await asyncio.sleep(0.01)
        try:
            for GOOGLE_API in GOOGLE_API_KEY_list:
                if stop_generation:
                    main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
                        [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")]
                    ])
                    await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                text="⚠️ Генерация остановлена", reply_markup=main_keyboard)
                    stop_generation = False
                    break
                try:
                    genai.configure(api_key=GOOGLE_API)
                    history_json = f'{message.chat.id}.json'
                    if not os.path.exists(history_json):
                        open(history_json, 'w').close()
                    conversation_history = load_conversation_history(history_json)

                    if message.content_type == ContentType.TEXT:
                        text = message.text
                        if len(text) > 4000:
                            main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
                                [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")]
                            ])
                            await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                        text="❌ Максимальная длина сообщения 4000 символов", reply_markup=main_keyboard)
                            break
                        conversation_history.append({"role": "user", "parts": [{"text": text}]})
                    elif message.content_type == ContentType.PHOTO:
                        text = message.caption
                        if text is None:
                            main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
                                [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")]
                            ])
                            await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                        text="❌ Введите подпись к изображению", reply_markup=main_keyboard)
                            break
                        if len(text) > 1000:
                            main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
                                [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")]
                            ])
                            await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                        text="❌ Максимальная длина подписи фото 1000 символов", reply_markup=main_keyboard)
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
                        text = message.caption
                        if text is None:
                            main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
                                [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")]
                            ])
                            await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                        text="❌ Введите подпись к документу", reply_markup=main_keyboard)
                            break
                        if len(text) > 1000:
                            main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
                                [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")]
                            ])
                            await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                        text="❌ Максимальная длина подписи файла 1000 символов", reply_markup=main_keyboard)
                            break
                        if not message.document.mime_type == "application/pdf":
                            main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                                [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
                                [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")]
                            ])
                            await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                        text="❌ Поддерживается только pdf", reply_markup=main_keyboard)
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
                        upload_file_s = genai.upload_file(file_name)
                        conversation_history.append({"role": "user", "parts": [{"text": text}]})

                    user_id = message.from_user.id
                    model_name = get_user_model(settings, user_id)
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        generation_config=generation_config
                    )

                    if message.content_type == ContentType.TEXT:
                        chat_session = model.start_chat(history=conversation_history)
                        response = chat_session.send_message(text)
                    elif message.content_type == ContentType.PHOTO:
                        response = model.generate_content([text, image])
                    elif message.content_type == ContentType.DOCUMENT:
                        response = model.generate_content([text, upload_file_s])

                    conversation_history.append({"role": "model", "parts": [{"text": response.text}]})
                    save_conversation_history(conversation_history, history_json)

                    main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                        [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
                        [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")]
                    ])
                    await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                text=response.text, reply_markup=main_keyboard,
                                                parse_mode=ParseMode.MARKDOWN)
                    break
                except Exception as e:
                    print(e)
        except Exception as e:
            print(e)
            main_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
                [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")]
            ])
            await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                        text="❌ Произошла ошибка", reply_markup=main_keyboard)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
