# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

sfp-uploader is a Playwright-based automation tool that publishes podcast episodes to Spotify for Podcasters (creators.spotify.com). It automates the full upload workflow: login, audio file upload, episode metadata entry, optional scheduling, and retrieving the share URL.

## Build & Development Commands

- **Package manager**: Rye (`rye sync` to install dependencies)
- **Lint/Format**: `rye run check` (runs `ruff check --select I --fix` then `ruff format`)
- **Run directly**: `python -m sfp_uploader --email EMAIL --password PASS --audio_file_path FILE --title TITLE --description DESC`
- **Test upload** (generates silent audio, requires `.env` with `PODCAST_URL`, `PODCAST_EMAIL`, `PODCAST_PASSWORD`): `rye run test_upload`
- **Playwright browsers**: `playwright install chromium` (required before first run)

## Architecture

Single-module package at `src/sfp_uploader/`:

- **main.py** — Core `publish()` async function. Launches a headed Chrome via Playwright, handles Spotify login (Japanese locale UI), uploads audio, fills episode details (title, description, explicit/promotional flags, thumbnail, schedule), publishes, and copies the share URL from clipboard.
- **__main__.py** — CLI entrypoint with argparse. Wraps `publish()` with command-line arguments.
- **test_upload.py** — Script entrypoint (`test_upload` console script) that generates a 10-second silent MP3 via pydub and publishes it using env vars.

## Key Details

- The Spotify login flow uses **Japanese locale** role selectors (e.g., `"メールアドレスまたはユーザー名"`, `"ログイン"`). Keep these exact strings when modifying login code.
- Spotify's site uses two domains: `podcasters.spotify.com` (legacy) and `creators.spotify.com` (current). Cookies are set for both.
- Browser runs **headed** (not headless) — required for the clipboard API used to retrieve share URLs.
- Default timeout is 30s; CLI sets 360s. Timeouts are in milliseconds.
