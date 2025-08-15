import asyncio
import os
import requests
import yt_dlp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton
from Bot_api import Bot_Token
from YT_api import Api_Token

FFMPEG_PATH = r"E:\Sound Music\ffmpeg-2025-07-10-git-82aeee3c19-essentials_build\bin\ffmpeg.exe"

bot = Bot(token=Bot_Token)
dp = Dispatcher()

class MusicStates(StatesGroup):
    waiting_for_track_name = State()

# Reply клавіатура з кнопкою "Search Track"
reply_kb = ReplyKeyboardMarkup(
    keyboard=[[KeyboardButton(text="Search Track")]],
    resize_keyboard=True,
    one_time_keyboard=True
)

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Привіт! Натисни кнопку, щоб шукати пісню 🎵",
        reply_markup=reply_kb
    )

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

    await state.clear()  # очищаємо стан
    await message.answer(f"🎵 Шукаю: {query}\n⏳ Завантажую аудіо...")

    # Пошук на YouTube
    url = f"https://www.googleapis.com/youtube/v3/search?part=snippet&type=video&q={query}&key={Api_Token}&maxResults=1"
    res = requests.get(url).json()

    if not res.get("items"):
        await message.answer("Пісню не знайдено 😔")
        return

    video = res["items"][0]
    video_id = video["id"]["videoId"]
    title = video["snippet"]["title"]
    thumbnail_url = video["snippet"]["thumbnails"]["high"]["url"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # Завантаження обкладинки
    thumbnail_path = "thumb.jpg"
    with open(thumbnail_path, "wb") as f:
        f.write(requests.get(thumbnail_url).content)

    # yt-dlp
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

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))
