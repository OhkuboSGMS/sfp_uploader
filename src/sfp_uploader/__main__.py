import argparse
import asyncio
from datetime import datetime

from sfp_uploader.main import publish

if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Publish podcast episodes to Spotify for Creators."
    )
    parser.add_argument(
        "--audio_file_path", type=str, required=True, help="Path to the audio file"
    )
    parser.add_argument(
        "--title", "-t", type=str, required=True, help="Title of the episode"
    )
    parser.add_argument(
        "--description", "-d", type=str, required=True, help="Description of the episode"
    )
    parser.add_argument("--email", type=str, default="", help="Email address (required for non-CDP login)")
    parser.add_argument("--password", type=str, default="", help="Password (required for non-CDP login)")
    parser.add_argument(
        "--url",
        type=str,
        required=False,
        help="URL to process",
        default="https://podcasters.spotify.com/pod/dashboard/episode/wizard",
    )
    parser.add_argument(
        "--schedule", "-s", type=datetime.fromisoformat, help="Schedule of the data"
    )
    parser.add_argument(
        "--explicit", "-e", action="store_true", help="Explicit of the data"
    )
    parser.add_argument(
        "--promotional", "-p", action="store_true", help="Promotional of the data"
    )
    parser.add_argument("--thumbnail", "-th", type=str, help="Path to the image file")
    parser.add_argument(
        "--not_publish", "-np", action="store_false", help="Publish of the data"
    )
    parser.add_argument("--html", action="store_true", help="HTML of the data")
    parser.add_argument(
        "--cdp_url",
        type=str,
        default="auto",
        help="CDP URL (default: 'auto' = launch/reuse Chrome automatically). "
             "Set to 'none' to use fresh browser with login flow.",
    )
    args = parser.parse_args()

    cdp_url = args.cdp_url
    if cdp_url == "none":
        cdp_url = None

    result = asyncio.run(
        publish(
            args.url,
            args.email,
            args.password,
            args.audio_file_path,
            args.title,
            args.description,
            args.schedule,
            args.explicit,
            args.promotional,
            "",#args.thumbnail,
            args.not_publish,
            args.html,
            skip_login=bool(cdp_url),
            timeout=360 * 1000,
            cdp_url=cdp_url,
        )
    )
    print(f"Share URL: {result}")
