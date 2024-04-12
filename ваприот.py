from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
from aiogram.utils.callback_data import CallbackData
import urllib.parse
import random
import requests
from io import BytesIO
from mtranslate import translate

# Замените 'YOUR_TOKEN_HERE' на ваш токен от BotFather
TOKEN = '6466934577:AAFUolEJwW9ggIuBIsicjW40BBoYxoM1KGs'
bot = Bot(token=TOKEN)
dp = Dispatcher(bot)

cb = CallbackData("image", "prompt", "seed", "style")

styles = {
    "аниме": "%20anime-style,%20high%20quality",
    "реалистичный": "%20realistic-style,%20high%20quality,%20ultra-realism,%204K",
    "грустный": "%20high%20quality,%20dark%20colors,%20rain,%20sadness"
}

# Словарь для хранения текущего стиля пользователя
user_styles = {}

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
    url_button = types.InlineKeyboardButton(text="✅ПОДПИСАТЬСЯ", url="https://t.me/kaprw")
    keyboard.add(url_button)

    # Отправляем фото с подписью и кнопкой
    await bot.send_photo(chat_id=message.chat.id, photo=open(photo_path, 'rb'), caption=caption, reply_markup=keyboard)

@dp.message_handler()
async def handle_text(message: types.Message):
    waiting_sticker = await message.reply_sticker(sticker="CAACAgIAAxkBAAEL5bhmGCm13g7EWQzC9BPrKybr_FdSGgACcEQAAiiDwUiKG_xm3DqU2TQE")
    await bot.send_chat_action(message.chat.id, 'upload_photo')
    seed = random.randint(1, 1000)
    # Получаем стиль пользователя из словаря
    user_style = user_styles.get(message.from_user.id, "аниме")
    await send_image(message, message.text, seed, user_style)
    await waiting_sticker.delete()

async def send_image(message: types.Message, prompt: str, seed: int, style_key: str):
    style = styles[style_key]
    translated_prompt = translate(prompt, 'en')
    encoded_prompt = urllib.parse.quote(translated_prompt)
    url = f"https://image.pollinations.ai/prompt/{encoded_prompt}{style}?seed={seed}&width=720&height=720&model=turbo&nologo=true"
    response = requests.get(url)
    if response.status_code == 200:
        image_bytes = BytesIO(response.content)
        image_bytes.name = 'image.jpeg'
        inline_kb = types.InlineKeyboardMarkup(row_width=2)
        inline_kb.add(types.InlineKeyboardButton("Сменить стиль", callback_data=cb.new(prompt=prompt, seed=seed, style='change_style')))
        caption = f"🏛Запрос: `{prompt}`"
        await bot.send_photo(message.chat.id, photo=image_bytes, caption=caption, reply_markup=inline_kb, parse_mode='Markdown')
    else:
        await bot.send_message(message.chat.id, "Не удалось загрузить изображение.")

@dp.callback_query_handler(cb.filter(style='change_style'))
async def change_style(callback_query: types.CallbackQuery, callback_data: dict):
    prompt = callback_data['prompt']
    seed = callback_data['seed']
    markup = types.InlineKeyboardMarkup(row_width=3)
    markup.add(types.InlineKeyboardButton("АНИМЕ", callback_data=cb.new(prompt=prompt, seed=seed, style="аниме")))
    markup.add(types.InlineKeyboardButton("РЕАЛИСТИЧНЫЙ", callback_data=cb.new(prompt=prompt, seed=seed, style="реалистичный")))
    markup.add(types.InlineKeyboardButton("ГРУСТНЫЙ", callback_data=cb.new(prompt=prompt, seed=seed, style="грустный")))
    await bot.send_message(callback_query.message.chat.id, "Сменить режим ⬇️", reply_markup=markup)

@dp.callback_query_handler(cb.filter())
async def handle_image_style(callback_query: types.CallbackQuery, callback_data: dict):
    prompt = callback_data['prompt']
    seed = callback_data['seed']
    new_style = callback_data['style']
    # Обновляем стиль пользователя в словаре
    user_styles[callback_query.from_user.id] = new_style
    await bot.send_message(callback_query.message.chat.id, f"✅Вы успешно сменили режим на: `{new_style}`", parse_mode='Markdown')

if __name__ == '__main__':
    executor.start_polling(dp)