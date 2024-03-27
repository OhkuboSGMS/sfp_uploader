import argparse
import asyncio
from datetime import datetime

from sfp_uploader.main import publish

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process URL, email, password, and audio file path.")

    parser.add_argument('--url', type=str, required=True, help='URL to process')
    parser.add_argument('--email', type=str, required=True, help='Email address')
    parser.add_argument('--password', type=str, required=True, help='Password')
    parser.add_argument('--audio_file_path', type=str, required=True, help='Path to the audio file')
    parser.add_argument('--title', '-t', type=str, required=True, help='Title of the data')
    parser.add_argument('--description', '-d', type=str, required=True, help='Description of the data')
    parser.add_argument('--schedule', '-s', type=datetime.fromisoformat, help='Schedule of the data')
    parser.add_argument('--explicit', '-e', action="store_true", help='Explicit of the data')
    parser.add_argument('--promotional', '-p', action="store_true", help='Promotional of the data')
    parser.add_argument('--thumbnail', '-th', type=str, help='Path to the image file')
    parser.add_argument('--not_publish', '-np', action="store_false", help='Publish of the data')
    args = parser.parse_args()
    result = asyncio.run(
        publish(args.url, args.email, args.password, args.audio_file_path, args.title, args.description,
                args.schedule, args.explicit, args.promotional, args.thumbnail, args.not_publish))
    print(f"Share URL: {result}")
