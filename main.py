import asyncio
import os
import requests
import yt_dlp
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import FSInputFile
from Bot_api import Bot_Token
from YT_api import Api_Token

# Шлях до ffmpeg
FFMPEG_PATH = r"E:\Sound Music\ffmpeg-2025-07-10-git-82aeee3c19-essentials_build\bin\ffmpeg.exe"

bot = Bot(token=Bot_Token)
dp = Dispatcher()

@dp.message(Command("start"))
async def start(message: types.Message):
    await message.answer(
        "Привіт! Напиши /music <назва пісні>, і я відправлю її у Telegram 🎵"
    )

@dp.message(Command("music"))
async def search_music(message: types.Message):
    query = message.text.replace("/music", "").strip()
    if not query:
        await message.answer("Введи назву пісні після /music")
        return

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

    await message.answer(f"🎵 Знайшов: {title}\n⏳ Завантажую аудіо...")

    # Завантаження обкладинки
    thumbnail_path = "thumb.jpg"
    thumb_data = requests.get(thumbnail_url).content
    with open(thumbnail_path, "wb") as f:
        f.write(thumb_data)

    # Налаштування yt-dlp з ffmpeg
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

    # Завантаження аудіо
    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([video_url])
    except Exception as e:
        await message.answer(f"Помилка при завантаженні: {e}")
        return

    # Відправка аудіо в Telegram
    if os.path.exists("song.mp3") and os.path.exists("thumb.jpg"):
        audio_file = FSInputFile("song.mp3")
        thumb_file = FSInputFile("thumb.jpg")

        await bot.send_audio(
            chat_id=message.chat.id,
            audio=audio_file,
            title=title,
            thumbnail=thumb_file  # правильно, не 'thumb'
        )

        # Видалення тимчасових файлів
        os.remove("song.mp3")
        os.remove("thumb.jpg")
    else:
        await message.answer("Не вдалося завантажити пісню 😔")

if __name__ == "__main__":
    asyncio.run(dp.start_polling(bot))

