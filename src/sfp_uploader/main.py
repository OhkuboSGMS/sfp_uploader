import logging
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from typing import Optional

from urllib.request import urlopen
from urllib.error import URLError

from playwright.async_api import Page, async_playwright

logger = logging.getLogger(__name__)

_publish_url = "https://creators.spotify.com/pod/dashboard/episodes"
_start_url = "https://creators.spotify.com/pod/dashboard/episode/wizard"

_screenshot_dir: Optional[str] = None
_screenshot_counter: int = 0


def _init_screenshot_dir(base_dir: Optional[str] = None):
    global _screenshot_dir, _screenshot_counter
    _screenshot_counter = 0
    if base_dir:
        _screenshot_dir = base_dir
    else:
        _screenshot_dir = os.path.join(os.getcwd(), "debug_screenshots")
    os.makedirs(_screenshot_dir, exist_ok=True)
    logger.info(f"Screenshots will be saved to: {_screenshot_dir}")


async def _screenshot(page: Page, step_name: str):
    global _screenshot_counter
    if _screenshot_dir is None:
        return
    _screenshot_counter += 1
    filename = f"{_screenshot_counter:03d}_{step_name}.png"
    filepath = os.path.join(_screenshot_dir, filename)
    await page.screenshot(path=filepath, full_page=True)
    logger.info(f"[STEP {_screenshot_counter}] {step_name} | url={page.url} | saved={filename}")


async def _save_error_info(page: Page, error: Exception):
    """エラー発生時にスクリーンショットとHTMLを保存する"""
    try:
        await _screenshot(page, "ERROR")
        if _screenshot_dir:
            html_path = os.path.join(_screenshot_dir, "error_page.html")
            content = await page.content()
            with open(html_path, "w", encoding="utf-8") as f:
                f.write(content)
            logger.info(f"Error HTML saved to: {html_path}")
    except Exception as e:
        logger.error(f"Failed to save error info: {e}")


_DEFAULT_CDP_PORT = 9222
_DEFAULT_USER_DATA_DIR = os.path.join(os.path.expanduser("~"), ".sfp_uploader", "chrome_profile")


def _find_chrome() -> Optional[str]:
    """Chromeの実行ファイルパスを探す"""
    candidates = [
        shutil.which("chrome"),
        shutil.which("google-chrome"),
        shutil.which("google-chrome-stable"),
        # Windows
        os.path.join(os.environ.get("PROGRAMFILES", ""), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", ""), "Google", "Chrome", "Application", "chrome.exe"),
        # macOS
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
    ]
    for c in candidates:
        if c and os.path.isfile(c):
            return c
    return None


def _is_cdp_running(port: int = _DEFAULT_CDP_PORT) -> bool:
    """CDPポートが応答するか確認"""
    try:
        with urlopen(f"http://localhost:{port}/json/version", timeout=2) as resp:
            return resp.status == 200
    except (URLError, OSError):
        return False


def launch_chrome(port: int = _DEFAULT_CDP_PORT, user_data_dir: Optional[str] = None) -> subprocess.Popen:
    """CDPデバッグポート付きでChromeを起動する"""
    chrome_path = _find_chrome()
    if not chrome_path:
        raise RuntimeError(
            "Chrome not found. Please install Google Chrome or pass cdp_url manually."
        )

    data_dir = user_data_dir or _DEFAULT_USER_DATA_DIR
    os.makedirs(data_dir, exist_ok=True)

    cmd = [
        chrome_path,
        f"--remote-debugging-port={port}",
        f"--user-data-dir={data_dir}",
    ]
    logger.info(f"Launching Chrome: {' '.join(cmd)}")
    proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    # CDPが応答するまで待つ
    for _ in range(30):
        if _is_cdp_running(port):
            logger.info(f"Chrome CDP ready on port {port}")
            return proc
        time.sleep(0.5)

    proc.kill()
    raise RuntimeError(f"Chrome launched but CDP did not respond on port {port}")


async def publish(
    url: str,
    email: str,
    password: str,
    audio_file: str,
    title: str,
    description: str,
    schedule: Optional[datetime] = None,
    explicit: bool = False,
    promotional: bool = False,
    thumbnail: Optional[str] = None,
    is_publish: bool = True,
    is_html: bool = False,
    skip_login: bool = False,
    timeout: int = 30 * 1000,
    screenshot_dir: Optional[str] = None,
    cdp_url: Optional[str] = None,
):
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )
    _init_screenshot_dir(screenshot_dir)
    chrome_proc = None
    if cdp_url == "auto":
        # CDPポートが既に空いていればそのまま接続、なければChromeを起動
        if _is_cdp_running(_DEFAULT_CDP_PORT):
            logger.info("Existing Chrome CDP found, reusing")
        else:
            chrome_proc = launch_chrome(_DEFAULT_CDP_PORT)
        cdp_url = f"http://localhost:{_DEFAULT_CDP_PORT}"

    async with async_playwright() as p:
        if cdp_url:
            # 既存のChromeに接続（ログイン済みセッションを利用）
            logger.info(f"Connecting to existing Chrome via CDP: {cdp_url}")
            browser = await p.chromium.connect_over_cdp(cdp_url)
            context = browser.contexts[0]
            context.set_default_timeout(timeout=timeout)
            # locale cookieを英語に設定
            await context.add_cookies(
                [
                    {
                        "name": "sp_locale",
                        "value": "en",
                        "url": "https://podcasters.spotify.com/",
                    },
                    {
                        "name": "sp_locale",
                        "value": "en",
                        "url": "https://creators.spotify.com/",
                    }
                ]
            )
            page = await context.new_page()
        else:
            browser = await p.chromium.launch(headless=False, channel='chrome')
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
            )
            context.set_default_timeout(timeout=timeout)
            await context.add_cookies(
                [
                    {
                        "name": "sp_locale",
                        "value": "en",
                        "url": "https://podcasters.spotify.com/",
                    },
                    {
                        "name": "sp_locale",
                        "value": "en",
                        "url": "https://creators.spotify.com/",
                    }
                ]
            )
            await context.grant_permissions(
                ["clipboard-read", "clipboard-write"]
            )
            page = await context.new_page()

        # コンソールログ収集
        page.on("console", lambda msg: logger.info(f"[CONSOLE {msg.type}] {msg.text}"))
        page.on("pageerror", lambda err: logger.error(f"[PAGE ERROR] {err}"))

        try:
            if not skip_login and not cdp_url:
                # ログインフロー（非CDPモード）
                login_url = "https://creators.spotify.com/pod/login"
                logger.info(f"Navigating to login page: {login_url}")
                await page.goto(login_url, wait_until="domcontentloaded")
                await page.wait_for_timeout(3000)
                await _screenshot(page, "01_login_page")

                login_button = page.get_by_role(
                    "button", name="Continue with Spotify", exact=True
                )
                await login_button.wait_for(state="visible", timeout=30000)
                await login_button.click()
                await page.wait_for_timeout(1000)
                await _screenshot(page, "02_spotify_login_page")

                logger.info("Filling email")
                email_input = page.get_by_role("textbox", name="メールアドレス")
                if await email_input.count() == 0:
                    email_input = page.get_by_role("textbox", name="メールアドレスまたはユーザー名")
                await email_input.fill(email)
                await page.wait_for_timeout(2000)

                await page.get_by_role("button", name="続行", exact=True).click()
                await page.wait_for_timeout(2000)
                await _screenshot(page, "03_after_continue")

                password_login_btn = page.get_by_role("button", name="パスワードでログイン", exact=True)
                if await password_login_btn.count() > 0 and await password_login_btn.is_visible():
                    await password_login_btn.click()
                    await page.wait_for_timeout(1000)

                password_input = page.get_by_role("textbox", name="パスワード")
                await password_input.wait_for(state="visible", timeout=30000)
                await password_input.fill(password)
                await page.wait_for_timeout(1000)
                await _screenshot(page, "04_password_filled")

                login_submit = page.get_by_role("button", name="ログイン", exact=True)
                if await login_submit.count() == 0:
                    login_submit = page.get_by_role("button", name="続行", exact=True)
                await login_submit.click()
                await page.wait_for_timeout(5000)
                await _screenshot(page, "05_after_login")

                # reCAPTCHAチャレンジの検出 → 手動介入
                if "challenge.spotify.com" in page.url:
                    logger.info(
                        "reCAPTCHA detected! Please solve the CAPTCHA in the browser, "
                        "then press 'Resume' in Playwright Inspector."
                    )
                    await page.pause()
                    await page.wait_for_timeout(3000)
                    await _screenshot(page, "05b_after_captcha")

                # ダッシュボードへの遷移を待つ
                await page.wait_for_url("**/dashboard/**", timeout=60000)
                await _screenshot(page, "06_dashboard")

            # wizardページへ遷移
            logger.info(f"Navigating to: {url}")
            await page.goto(url, wait_until="domcontentloaded")
            await page.wait_for_timeout(5000)
            await _screenshot(page, "07_wizard_page")
            # ネットワークのリクエストがアイドル状態になるまで待機
            await page.wait_for_load_state("load")
            await _screenshot(page, "07_upload_page_loaded")

            # Upload
            logger.info(f"Uploading audio file: {audio_file}")
            async with page.expect_file_chooser() as fc_info:
                await page.get_by_role("button", name="Select a file", exact=True).click()
            file_chooser = await fc_info.value
            await file_chooser.set_files(audio_file)
            await page.wait_for_timeout(2000)
            await _screenshot(page, "08_file_selected")

            # 配信の詳細を設定 (Episode Details)
            logger.info(f"Filling title: {title}")
            await page.get_by_role("textbox", name="Title (required)", exact=True).fill(
                title
            )
            # htmlスイッチを設定(デフォルトはオフなので is_html=Trueの場合のみスイッチをオンにする)
            if is_html:
                await page.get_by_role("checkbox", name="HTML", exact=True).set_checked(
                    True, force=True
                )
                # htmlスイッチを押すとtextboxも変わる
                await page.get_by_role(
                    "textbox",
                    name="What else do you want your audience to know?",
                    exact=True,
                ).fill(description)
            else:
                await page.get_by_role("textbox", name="", exact=True).fill(description)

            explicit_group = page.get_by_role("group", name="Explicit content (required)")
            if explicit and await explicit_group.count() > 0:
                await explicit_group.get_by_role(
                    "checkbox", name="Yes", exact=True
                ).set_checked(True, force=True)

            promotional_group = page.get_by_role(
                "group", name="Promotional content (required)"
            )
            if promotional and await promotional_group.count() > 0:
                await promotional_group.get_by_role(
                    "radio", name="No", exact=True
                ).check(force=True)
            await _screenshot(page, "09_details_filled")
            # await additional_detail.click()
            # サムネイルを差し替え
            if thumbnail:
                if os.path.exists(thumbnail):
                    async with page.expect_file_chooser() as fc_info:
                        await page.get_by_role("button", name="Change").first.click()
                    file_chooser = await fc_info.value
                    await file_chooser.set_files(thumbnail)
                    # thumbnail_dialog = page.get_by_role("dialog", name="image uploader")
                    # 確定
                    await page.get_by_role("button", name="Save").click()

                else:
                    print(
                        "Skip thumbnail replacement because the file does not exist.:{thumbnail}"
                    )

            # Cookieバナーを閉じる
            try:
                cookie_close = page.locator("#onetrust-close-btn-container button")
                if await cookie_close.count() > 0 and await cookie_close.is_visible():
                    await cookie_close.click(force=True)
                    logger.info("Cookie banner closed")
                    await page.wait_for_timeout(500)
            except Exception as e:
                logger.info(f"Cookie banner close skipped: {e}")

            await _screenshot(page, "10_before_next")

            # ページ内のボタンを探索してNextに相当するものを見つける
            buttons = await page.get_by_role("button").all()
            button_info = []
            for b in buttons:
                name = await b.text_content()
                vis = await b.is_visible()
                button_info.append(f"{name!r} (visible={vis})")
            logger.info(f"Available buttons on details page: {button_info}")

            # "Next" または "Review" ステップへの遷移ボタンを探す
            next_button = page.get_by_role("button", name="Next")
            if await next_button.count() == 0:
                # 新UIでは "Review" リンクかもしれない
                next_button = page.get_by_role("link", name="Review")
            if await next_button.count() == 0:
                # さらにフォールバック
                next_button = page.get_by_role("button").filter(has_text="Next")
            logger.info("Clicking next/review button")
            await next_button.scroll_into_view_if_needed()
            await next_button.click(force=True)
            await page.wait_for_timeout(2000)
            await _screenshot(page, "11_schedule_page")
            # schedule
            # スケジュール
            if schedule:
                # Schedule
                await page.get_by_role("radio", name="Schedule").set_checked(
                    True, force=True
                )
                mdy = schedule.strftime("%m/%d/%Y")
                await page.get_by_role("textbox", name="Date").fill(mdy, force=True)
                await page.get_by_role("textbox", name="Hour picker").fill(
                    schedule.strftime("%H"), force=True
                )
                await page.get_by_role("textbox", name="Minute picker").fill(
                    schedule.strftime("%M"), force=True
                )
                await page.get_by_role("combobox", name="Meridiem picker").select_option(
                    schedule.strftime("%p"), force=True
                )
            else:
                # Publish now
                await page.get_by_role("radio", name="Now", exact=True).set_checked(
                    True, force=True
                )
            await page.wait_for_timeout(2000)
            await _screenshot(page, "12_before_publish")
            # # 投票機能など
            # await page.get_by_role("button", name="Next").click()
            # await page.wait_for_timeout(2000)
            # if is_publish:
            # Publish前のURLからエピソードIDを取得
            # URL例: .../episode/{episode_id}/wizard
            pre_publish_url = page.url
            episode_id_match = re.search(r"/episode/([^/]+)/wizard", pre_publish_url)
            episode_id = episode_id_match.group(1) if episode_id_match else None
            logger.info(f"Episode ID from wizard URL: {episode_id}")

            # 公開
            logger.info("Clicking 'Publish'")
            await page.get_by_role("button", name="Publish").click()
            await page.wait_for_url("**/episodes")
            await page.wait_for_load_state("load")
            await page.wait_for_timeout(3000)
            await _screenshot(page, "13_published")

            # Share URLを取得
            share_url = None

            # 方法1: clipboard.writeText をフックしてCopyボタンの値をキャプチャ
            has_clipboard = await page.evaluate("() => !!(navigator.clipboard && navigator.clipboard.writeText)")
            if has_clipboard:
                await page.evaluate("""() => {
                    window.__clipboardCapture = null;
                    const orig = navigator.clipboard.writeText.bind(navigator.clipboard);
                    navigator.clipboard.writeText = function(text) {
                        window.__clipboardCapture = text;
                        return orig(text);
                    };
                }""")
                copy_btn = page.get_by_label("Copy", exact=True)
                if await copy_btn.count() > 0:
                    await copy_btn.first.click(force=True)
                    await page.wait_for_timeout(1000)
                    captured = await page.evaluate("() => window.__clipboardCapture")
                    if captured and ("http" in str(captured) or "spotify" in str(captured)):
                        share_url = captured
                        logger.info(f"Share URL from clipboard hook: {share_url}")

            # 方法2: エピソードIDからSpotify share URLを構築
            if not share_url and episode_id:
                share_url = f"https://open.spotify.com/episode/{episode_id}"
                logger.info(f"Share URL constructed from episode ID: {share_url}")

            # 方法3: フォールバック
            if not share_url:
                share_url = page.url
                logger.info(f"Using page URL as fallback: {share_url}")

            logger.info(f"Share URL: {share_url}")
            await page.wait_for_timeout(1000)
            await _screenshot(page, "14_share_url_copied")
        except Exception as e:
            logger.error(f"Error during publish: {e}")
            await _save_error_info(page, e)
            raise
        finally:
            await page.close()
            if not cdp_url:
                await context.close()
                await browser.close()
    return share_url
