import argparse

from .main import publish

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Process URL, email, password, and audio file path.")

    parser.add_argument('--url', type=str, required=True, help='URL to process')
    parser.add_argument('--email', type=str, required=True, help='Email address')
    parser.add_argument('--password', type=str, required=True, help='Password')
    parser.add_argument('--audio_file_path', type=str, required=True, help='Path to the audio file')
    parser.add_argument('--title', '-t', type=str, required=True, help='Title of the data')
    parser.add_argument('--description', '-d', type=str, required=True, help='Description of the data')

    args = parser.parse_args()
    result = publish(args.url, args.email, args.password, args.audio_file_path, args.title, args.description)
    print(f"Share URL: {result}")
