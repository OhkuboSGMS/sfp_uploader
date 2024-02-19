import asyncio
import tempfile
from sfp_uploader.main import publish
from pydub import AudioSegment
import os
from dotenv import load_dotenv


async def main():
    load_dotenv()
    if "PODCAST_URL" not in os.environ:
        raise ValueError("PODCAST_URL is not set")
    if "PODCAST_EMAIL" not in os.environ:
        raise ValueError("PODCAST_EMAIL is not set")
    if "PODCAST_PASSWORD" not in os.environ:
        raise ValueError("PODCAST_PASSWORD is not set")

    ten_second_silence = AudioSegment.silent(duration=10000, frame_rate=44100)
    temp_file = os.path.abspath("test.mp3")
    ten_second_silence.export(temp_file, format="mp3")

    share_url = await publish(
        os.environ["PODCAST_URL"],
        os.environ["PODCAST_EMAIL"],
        os.environ["PODCAST_PASSWORD"],
        temp_file,
        "test",
        "test"
    )
    os.unlink(temp_file)
    print(share_url)

    asyncio.run(main())
