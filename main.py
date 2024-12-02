import asyncio
import os
import PIL.Image
import google.generativeai as genai
from aiogram import Bot, Dispatcher, types
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ChatAction
from aiogram.enums import ParseMode
from aiogram.filters import Command
from aiogram.filters.state import State, StatesGroup, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.types import ContentType
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.types import Message
from aiogram.utils.chat_action import ChatActionSender

from Handlers import (check_user_account, get_user_model, get_user_send_model_name, set_user_model,
                      set_user_send_model_name, get_user_temperature, set_user_temperature,
                      load_conversation_history, save_conversation_history, delete_folder, get_user_only_ru,
                      set_user_only_ru, download_and_upload_file)
from config import (API_TOKEN, GOOGLE_API_KEY_list)
from skysmart.answer_module import SkyAnswers

bot = Bot(token=API_TOKEN)
default = DefaultBotProperties(parse_mode=ParseMode.MARKDOWN)
dp = Dispatcher()


class Waitusertemperature(StatesGroup):
    usr_temperature = State()


if not os.path.exists('media'):
    os.makedirs('media')

start_menu_text = "👋 Добро пожаловать! ✨\n\n🤖 Я — большая языковая модель, и у меня есть две версии: gemini-1.5-pro и gemini-1.5-flash.\n\n🧠 gemini-1.5-pro — для решения сложных задач, требующих глубокого анализа. 🤯\n⚡ gemini-1.5-flash — быстрая и эффективная версия для простых вопросов. 💨\n\n☝️  gemini-1.5-flash имеет больший лимит запросов. 😉\n\n🧹 Не забывайте очищать историю для начала нового диалога или при отправке большого сообщения. \n\n✨ Готов ответить на ваши вопросы! ✨"
start_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
    [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
    [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")],
    [InlineKeyboardButton(text="💻 Настройки", callback_data="Settings_menu")]
])


async def get_keyboard_for_settings_menu(user_id):
    temperature_now = get_user_temperature(user_id)
    settings_menu_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")],
        [InlineKeyboardButton(text=f"🌡️ Temperature ({temperature_now})", callback_data="Temperature_user")],
    ])
    if get_user_send_model_name(user_id):
        send_m_n = InlineKeyboardButton(text="Название модели после ответа ✅", callback_data="user_send_model_name")
    else:
        send_m_n = InlineKeyboardButton(text="Название модели после ответа", callback_data="user_send_model_name")
    if get_user_only_ru(user_id):
        only_russian = InlineKeyboardButton(text="Только на русском ✅", callback_data="Only_russian")
    else:
        only_russian = InlineKeyboardButton(text="Только на русском", callback_data="Only_russian")
    settings_menu_keyboard.inline_keyboard.append([send_m_n])
    settings_menu_keyboard.inline_keyboard.append([only_russian])
    settings_menu_keyboard.inline_keyboard.append(
        [InlineKeyboardButton(text="⏩ На главную", callback_data="start_menu")])
    return settings_menu_keyboard


stop_generation = False


@dp.message(Command("start"))
async def cmd_start(message: Message):
    check_user_account(message.chat.id)
    await message.answer(start_menu_text, reply_markup=start_menu_keyboard)


@dp.callback_query(
    lambda c: c.data in ["Del_history", "Change_model", "Gemini-1.5-flash", "Gemini-1.5-pro", "break_generation",
                         "user_send_model_name", "Settings_menu", "start_menu",
                         "Temperature_user", "Gemini-1.5-flash-8b", "Only_russian"])
async def handle_button_click(callback_query: types.CallbackQuery, state: FSMContext):
    global stop_generation
    callback_query_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
        [InlineKeyboardButton(text="⚙️ Изменить модель", callback_data="Change_model")],
        [InlineKeyboardButton(text="💻 Настройки", callback_data="Settings_menu")]
    ])
    match callback_query.data:
        case "Del_history":
            await clear_history(callback_query.message)
        case "Change_model":
            await change_model(callback_query.message)
        case "Gemini-1.5-flash":
            await set_user_model(callback_query.from_user.id, "gemini-1.5-flash")
            await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        text="⚡ Gemini-1.5-flash", reply_markup=callback_query_keyboard)
        case "Gemini-1.5-pro":
            await set_user_model(callback_query.from_user.id, "gemini-1.5-pro")
            await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        text="🧠 Gemini-1.5-pro", reply_markup=callback_query_keyboard)
        case "Gemini-1.5-flash-8b":
            await set_user_model(callback_query.from_user.id, "gemini-1.5-flash-8b")
            await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        text="⚡ Gemini-1.5-flash-8b", reply_markup=callback_query_keyboard)
        case "break_generation":
            stop_generation = True
            await clear_history(callback_query.message)
        case "user_send_model_name":
            await set_user_send_model_name(callback_query.from_user.id)
            user_send_model_name_keyboard = await get_keyboard_for_settings_menu(callback_query.from_user.id)
            await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        text="💻 Настройки:", reply_markup=user_send_model_name_keyboard)
        case "Settings_menu":
            await settings_menu(callback_query.message)
        case "start_menu":
            await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        text=start_menu_text, reply_markup=start_menu_keyboard)
        case "Temperature_user":
            await state.set_state(Waitusertemperature.usr_temperature)
            await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        text="Напишите temperature от 0 до 2.0")
        case "Only_russian":
            await set_user_only_ru(callback_query.from_user.id)
            user_send_model_name_keyboard = await get_keyboard_for_settings_menu(callback_query.from_user.id)
            await bot.edit_message_text(chat_id=callback_query.message.chat.id,
                                        message_id=callback_query.message.message_id,
                                        text="💻 Настройки:", reply_markup=user_send_model_name_keyboard)
            await clear_history(callback_query.message)


@dp.message(StateFilter(Waitusertemperature.usr_temperature))
async def set_temperature(message: Message, state: FSMContext):
    user_id = message.chat.id if message.chat.id is not None else message.from_user.id
    try:
        tempr = float(message.text)
        if tempr < 0 or tempr > 2:
            await message.answer("Введите значение от 0 до 2.0", reply_markup=start_menu_keyboard)
        else:
            await set_user_temperature(user_id, tempr)
            await state.clear()
            await settings_menu(message)
    except:
        await message.answer("Введите корректное значение температуры", reply_markup=start_menu_keyboard)


@dp.message(Command("change_model"))
async def change_model(message: Message):
    user_id = message.chat.id if message.chat.id is not None else message.from_user.id
    current_model = get_user_model(user_id)
    change_model_keyboard = InlineKeyboardMarkup(inline_keyboard=[])
    if current_model == 'gemini-1.5-flash':
        change_model_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Gemini-1.5-flash ✅", callback_data="Gemini-1.5-flash")],
            [InlineKeyboardButton(text="⚡ Gemini-1.5-flash-8b", callback_data="Gemini-1.5-flash-8b")],
            [InlineKeyboardButton(text="🧠 Gemini-1.5-pro", callback_data="Gemini-1.5-pro")],
        ])
    elif current_model == 'gemini-1.5-pro':
        change_model_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Gemini-1.5-flash", callback_data="Gemini-1.5-flash")],
            [InlineKeyboardButton(text="⚡ Gemini-1.5-flash-8b", callback_data="gemini-1.5-flash-8b")],
            [InlineKeyboardButton(text="🧠 Gemini-1.5-pro ✅ ", callback_data="Gemini-1.5-pro")]
        ])
    elif current_model == 'gemini-1.5-flash-8b':
        change_model_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⚡ Gemini-1.5-flash", callback_data="Gemini-1.5-flash")],
            [InlineKeyboardButton(text="⚡ Gemini-1.5-flash-8b ✅", callback_data="gemini-1.5-flash-8b")],
            [InlineKeyboardButton(text="🧠 Gemini-1.5-pro", callback_data="Gemini-1.5-pro")]
        ])

    await message.answer("Выберете модель ⚙️", reply_markup=change_model_keyboard)


@dp.message(Command("settings_menu"))
async def settings_menu(message: Message):
    user_id = message.chat.id if message.chat.id is not None else message.from_user.id
    settings_menu_keyboard = await get_keyboard_for_settings_menu(user_id)
    await message.answer("💻 Настройки:", reply_markup=settings_menu_keyboard)


@dp.message(Command("clear"))
async def clear_history(message: types.Message):
    if message.chat.id is None:
        history_json = f'{message.from_user.id}.json'
        media_dir = f'media/{message.from_user.id}'
        user_id = message.from_user.id
    else:
        history_json = f'{message.chat.id}.json'
        media_dir = f'media/{message.chat.id}'
        user_id = message.chat.id
    prompt_json = f'prompt/ru.json'
    with open(history_json, 'w', encoding='utf-8') as file:
        file.truncate(0)
    delete_folder(media_dir)
    if get_user_only_ru(user_id) is True:
        with open(prompt_json, 'r', encoding='utf-8') as file:
            data = file.read()
        with open(history_json, 'w', encoding='utf-8') as file:
            file.write(data)
    await message.answer("🧹 История очищена")


@dp.message()
async def handle_message(message: Message):
    if message.text and ("https://edu.skysmart.ru/student/" in message.text or
                         "http://edu.skysmart.ru/student/" in message.text or
                         "edu.skysmart.ru/student/" in message.text):
        try:
            task_hash = message.text
            if "https://edu.skysmart.ru/student/" in task_hash:
                task_hash = task_hash.replace("https://edu.skysmart.ru/student/", "")
            elif "http://edu.skysmart.ru/student/" in task_hash:
                task_hash = task_hash.replace("http://edu.skysmart.ru/student/", "")
            elif "edu.skysmart.ru/student/" in task_hash:
                task_hash = task_hash.replace("edu.skysmart.ru/student/", "")
            answers_module = SkyAnswers(task_hash)
            answers = await answers_module.get_answers()
            for solution in answers:
                task_message = f"Задание #{solution['task_number']} - {solution['question']}\n"
                for answer in solution['answers']:
                    task_message += f'   Ответ: {answer}\n'
                await message.answer(task_message)
                await asyncio.sleep(0.5)
            await message.answer("✅ Все задания обработаны.")
        except Exception as e:
            print(e)
            await message.answer("❌ Произошла ошибка")

    else:
        global stop_generation
        stop_generation_keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🛑 Прекратить генерацию", callback_data="break_generation")],
        ])
        msg = await message.answer("💬 Пожалуйста, подождите, идет обработка запроса",
                                   reply_markup=stop_generation_keyboard)
        async with ChatActionSender(action=ChatAction.TYPING, chat_id=message.chat.id, bot=bot):
            await asyncio.sleep(0.10)
            message_keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="🧹 Очистить историю", callback_data="Del_history")],
                [InlineKeyboardButton(text="💻 Настройки", callback_data="Settings_menu")],
                [InlineKeyboardButton(text="⏩ На главную", callback_data="start_menu")]
            ])
            try:
                for GOOGLE_API in GOOGLE_API_KEY_list:
                    if stop_generation:
                        await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                    text="⚠️ Генерация остановлена", reply_markup=message_keyboard)
                        stop_generation = False
                        break
                    try:
                        genai.configure(api_key=GOOGLE_API)
                        history_json = f'{message.chat.id}.json'
                        if not os.path.exists(history_json):
                            open(history_json, 'w', encoding='utf-8').close()
                        conversation_history = load_conversation_history(history_json)
                        if message.content_type == ContentType.TEXT:
                            text = message.text
                            if len(text) > 4000:
                                await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                            text="❌ Максимальная длина сообщения 4000 символов",
                                                            reply_markup=message_keyboard)
                                break
                            conversation_history.append({"role": "user", "parts": [{"text": text}]})
                        elif message.content_type == ContentType.PHOTO:
                            text = message.caption
                            if text is None:
                                await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                            text="❌ Введите подпись к изображению",
                                                            reply_markup=message_keyboard)
                                break
                            if len(text) > 1000:
                                await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                            text="❌ Максимальная длина подписи фото 1000 символов",
                                                            reply_markup=message_keyboard)
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
                                await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                            text="❌ Введите подпись к документу",
                                                            reply_markup=message_keyboard)
                                break
                            if len(text) > 1000:
                                await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                            text="❌ Максимальная длина подписи файла 1000 символов",
                                                            reply_markup=message_keyboard)
                                break
                            if not message.document.mime_type == "application/pdf":
                                await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                            text="❌ Поддерживается только pdf",
                                                            reply_markup=message_keyboard)
                                break
                            document = message.document
                            uploaded_document = await download_and_upload_file(bot, document.file_id, 'pdf',
                                                                               message.from_user.id, document.file_name)
                            conversation_history.append({"role": "user", "parts": [{"text": text}]})
                        elif message.content_type == ContentType.VIDEO:
                            text = message.caption
                            if text is None:
                                await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                            text="❌ Введите подпись к видео",
                                                            reply_markup=message_keyboard)
                                break
                            if len(text) > 1000:
                                await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                            text="❌ Максимальная длина подписи видео 1000 символов",
                                                            reply_markup=message_keyboard)
                                break
                            video = message.video
                            uploaded_video = await download_and_upload_file(bot, video.file_id, 'mp4',
                                                                            message.from_user.id,
                                                                            f'{video.file_id}.mp4')

                            while uploaded_video.state.name == "PROCESSING":
                                uploaded_video = genai.get_file(uploaded_video.name)

                            conversation_history.append({"role": "user", "parts": [{"text": text}]})

                        user_id = message.from_user.id

                        generation_config = {
                            "temperature": get_user_temperature(user_id),
                            "max_output_tokens": 4000,
                        }

                        model_name = get_user_model(user_id)
                        model = genai.GenerativeModel(
                            model_name=model_name,
                            generation_config=generation_config
                        )
                        if not stop_generation:
                            if message.content_type == ContentType.TEXT:
                                chat_session = model.start_chat(history=conversation_history)
                                response = chat_session.send_message(text)
                            elif message.content_type == ContentType.PHOTO:
                                response = model.generate_content([text, image])
                            elif message.content_type == ContentType.DOCUMENT:
                                response = model.generate_content([text, uploaded_document])
                            elif message.content_type == ContentType.VIDEO:
                                response = model.generate_content([text, uploaded_video])

                            conversation_history.append({"role": "model", "parts": [{"text": response.text}]})
                            save_conversation_history(conversation_history, history_json)
                        if not stop_generation:
                            await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                                        text=response.text, reply_markup=message_keyboard,
                                                        parse_mode=ParseMode.MARKDOWN)
                        if get_user_send_model_name(user_id) is True:
                            await message.answer(f"{model_name} сгенерировала ответ")
                        break
                    except Exception as e:
                        print(e)
            except Exception as e:
                print(e)
                await bot.edit_message_text(chat_id=message.chat.id, message_id=msg.message_id,
                                            text="❌ Произошла ошибка", reply_markup=message_keyboard)


async def main():
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
