from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.utils.callback_data import CallbackData
import urllib.parse
import random
import requests
from io import BytesIO
from mtranslate import translate
import os
from background import keep_alive

# Замените 'YOUR_TOKEN_HERE' на ваш токен от BotFather
TOKEN = os.getenv('MY_API_KEY')
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

cb = CallbackData("image", "id")

styles = {
    "аниме": "%20anime-style,%20high%20quality",
    "реалистичный": "%20realistic-style,%20high%20quality,%20ultra-realism,%204K",
    "грустный": "%20high%20quality,%20dark%20colors,%20rain,%20sadness"
}

# Словарь для хранения текущего стиля пользователя
user_styles = {}
# Словарь для хранения данных запросов
requests_data = {}

@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_styles[message.from_user.id] = "аниме"
    caption = """
👋🏻 Привет! Тут каждый может создать свои аниме-арты потрясающего качества на основе самого передового генеративного ИИ.

Хочешь сразу к делу?
> Просто напиши, что желаешь увидеть. Мы поддерживаем все языки :)
Если нужно сделать портрет, начни с описания внешности.

Кстати, подпишись на канал, там ты сможешь найти множество артов от нашего сообщества 👇"""
    photo_path = 'photo_2024-04-11_23-23-00.jpg'
    keyboard = types.InlineKeyboardMarkup()
    url_button = types.InlineKeyboardButton(text="✅ПОДПИСАТЬСЯ", url="https://t.me/StableDifusionn")
    keyboard.add(url_button)

    # Отправляем фото с подписью и кнопкой
    await bot.send_photo(chat_id=message.chat.id, photo=open(photo_path, 'rb'), caption=caption, reply_markup=keyboard)

@dp.message_handler()
async def handle_text(message: types.Message):
    waiting_sticker = await message.reply_sticker(sticker="CAACAgIAAxkBAAEL5bhmGCm13g7EWQzC9BPrKybr_FdSGgACcEQAAiiDwUiKG_xm3DqU2TQE")
    await bot.send_chat_action(message.chat.id, 'upload_photo')
    seed = random.randint(1, 1000)
    user_style = user_styles.get(message.from_user.id, "аниме")
    request_id = str(random.randint(1000000, 9999999))
    requests_data[request_id] = (message.text, seed, user_style)
    await send_image(message, request_id)
    await waiting_sticker.delete()

async def send_image(message: types.Message, request_id: str):
    prompt, seed, style_key = requests_data[request_id]
    style_params = styles[style_key]  # Параметры стиля для URL
    translated_prompt = translate(prompt, 'en')
    encoded_prompt = urllib.parse.quote(translated_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}{style_params}?seed={seed}&width=720&height=720&model=turbo&nologo=true"
    response = requests.get(url)
    if response.status_code == 200:
        image_bytes = BytesIO(response.content)
        image_bytes.name = 'image.jpeg'
        inline_kb = types.InlineKeyboardMarkup(row_width=2)
        inline_kb.add(types.InlineKeyboardButton("🎨Сменить стиль", callback_data=cb.new(id=request_id)))
        inline_kb.add(types.InlineKeyboardButton("🔁Повторить", callback_data=cb.new(id=f"regenerate_{request_id}")))
        # Добавляем название стиля в подпись
        caption = f"🖌️Текущий стиль изображения: `{style_key}`\n🏛Твой запрос: `{prompt}`"
        message_to_delete = await bot.send_photo(message.chat.id, photo=image_bytes, caption=caption, reply_markup=inline_kb, parse_mode='Markdown')
        # Сохраняем message_id последнего сообщения для последующего удаления
        requests_data[request_id] = (prompt, seed, style_key, message_to_delete.message_id)
    else:
        await bot.send_message(message.chat.id, "❌Произошла ошибка")

@dp.callback_query_handler(cb.filter(), text_contains="regenerate_")
async def regenerate_image(callback_query: types.CallbackQuery, callback_data: dict):
    original_id = callback_data['id'].split('_')[1]
    if original_id in requests_data:
        prompt, seed, style_key, old_message_id = requests_data[original_id]
        await bot.delete_message(chat_id=callback_query.message.chat.id, message_id=old_message_id)
        waiting_sticker = await bot.send_sticker(chat_id=callback_query.message.chat.id, sticker="CAACAgIAAxkBAAEL5bhmGCm13g7EWQzC9BPrKybr_FdSGgACcEQAAiiDwUiKG_xm3DqU2TQE")
        # Генерируем новое изображение с новым seed
        new_seed = random.randint(1, 1000)
        new_request_id = str(random.randint(1000000, 9999999))
        requests_data[new_request_id] = (prompt, new_seed, style_key)
        await send_image(callback_query.message, new_request_id)
        await waiting_sticker.delete()
    else:
        await bot.send_message(callback_query.message.chat.id, "❌Произошла ошибка")

@dp.callback_query_handler(cb.filter(), text_contains="_")
async def change_style(callback_query: types.CallbackQuery, callback_data: dict):
    # Разделяем полученный id на request_id и новый стиль
    request_id, new_style = callback_data['id'].split('_')
    user_id = callback_query.from_user.id
    # Обновляем стиль пользователя в словаре
    user_styles[user_id] = new_style
    # Отправляем подтверждающее сообщение пользователю
    await bot.send_message(callback_query.message.chat.id, f"✅Вы успешно сменили режим на: `{new_style.upper()}`", parse_mode='Markdown')

@dp.callback_query_handler(cb.filter())
async def handle_image_style(callback_query: types.CallbackQuery, callback_data: dict):
    request_id = callback_data['id']
    if request_id in requests_data:
        prompt, seed, _, old_message_id = requests_data[request_id]
        markup = types.InlineKeyboardMarkup(row_width=3)
        for style_name in styles.keys():
            markup.add(types.InlineKeyboardButton(style_name.upper(), callback_data=cb.new(id=f"{request_id}_{style_name}")))
        await bot.send_message(callback_query.message.chat.id, "Выбери стиль генерации ⬇️", reply_markup=markup)
    else:
        await bot.send_message(callback_query.message.chat.id, "❌Произошла ошибка")

keep_alive()

if __name__ == '__main__':
    executor.start_polling(dp)
