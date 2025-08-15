import asyncio
import os
import requests
import yt_dlp
from flask import Flask, request
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton

FFMPEG_PATH = "/usr/bin/ffmpeg"  # Render має свій ffmpeg (або можна додати пакет)

TOKEN = os.getenv("BOT_TOKEN")
YT_API = os.getenv("YT_API")

bot = Bot(token=TOKEN)
dp = Dispatcher()

class MusicStates(StatesGroup):
    waiting_for_track_name = State()

reply_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Search Track")]],
    resize_keyboard=True,
    one_time_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer("Привіт! Натисни кнопку, щоб шукати пісню 🎵", reply_markup=reply_kb)

@dp.message(lambda message: message.text == "Search Track")
async def ask_track_name(message: types.Message, state: FSMContext):
    await message.answer("Введіть назву пісні:")
    await state.set_state(MusicStates.waiting_for_track_name)

@dp.message(MusicStates.waiting_for_track_name)
async def search_music(message: types.Message, state: FSMContext):
    query = message.text.strip()
    if not query:
        await message.answer("Введіть назву пісні ще раз:")
        return

    await state.clear()
    await message.answer(f"🎵 Шукаю: {query}\n⏳ Завантажую аудіо...")

    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&q={query}&key={YT_API}&maxResults=1"
    res = requests.get(url).json()

    if not res.get("items"):
        await message.answer("Пісню не знайдено 😔")
        return

    video = res["items"][0]
    video_id = video["id"]["videoId"]
    title = video["snippet"]["title"]
    thumbnail_url = video["snippet"]["thumbnails"]["high"]["url"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    thumbnail_path = "thumb.jpg"
    with open(thumbnail_path, "wb") as f:
        f.write(requests.get(thumbnail_url).content)

    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': 'song.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'mp3',
            'preferredquality': '192',
        }],
        'ffmpeg_location': FFMPEG_PATH,
        'quiet': True
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except Exception as e:
        await message.answer(f"Помилка при завантаженні: {e}")
        return

    if os.path.exists("song.mp3") and os.path.exists("thumb.jpg"):
        audio_file = FSInputFile("song.mp3")
        thumb_file = FSInputFile("thumb.jpg")

        await bot.send_audio(
            chat_id=message.chat.id,
            audio=audio_file,
            title=title,
            thumbnail=thumb_file
        )

        os.remove("song.mp3")
        os.remove("thumb.jpg")
    else:
        await message.answer("Не вдалося завантажити пісню 😔")

# Flask для Render
app = Flask(__name__)

@app.route(f"/webhook/{TOKEN}", methods=["POST"])
def webhook():
    data = request.get_json()
    asyncio.run(dp.process_update(types.Update(**data)))
    return "ok", 200

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
