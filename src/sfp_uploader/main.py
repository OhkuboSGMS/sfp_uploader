import os
from datetime import datetime
from random import random
from typing import Optional

from playwright.async_api import async_playwright
_publish_url = "https://creators.spotify.com/pod/dashboard/episodes"
_start_url = "https://creators.spotify.com/pod/dashboard/episode/wizard"


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
):
    async with async_playwright() as p:
        # 自分が使っているChromeを使う場合
        # browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        # context = browser.contexts[0]
        # page = context.pages[0]
        browser = await p.chromium.launch(headless=False,channel='chrome')
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
        )
        context.set_default_timeout(timeout=timeout)
        # change language to English
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
        # ログイン
        await page.goto(url)

        if not skip_login:
            await page.get_by_role(
                "button", name="Continue with Spotify", exact=True
            ).click()
            # Spotifyのログインのlocale判定がAnchorとは異なり、日本語で表示される、変更方法が不明なため、日本語でログインする
            await page.get_by_role("textbox", name="メールアドレスまたはユーザー名").fill(
                email
            )
            await page.wait_for_timeout(2000)

            await page.get_by_role("button", name="次へ", exact=True).click()
            await page.wait_for_timeout(1000)
            await page.get_by_role("button", name="パスワードでログイン", exact=True).click()

            await page.get_by_role("textbox", name="パスワード").fill(
                password
            )
            await page.wait_for_timeout(1000)
            await page.get_by_role("button", name="ログイン", exact=True).click()
            # await page.get_by_role("button", name="Continue to the app", exact=True).click()
            # 何故かもう一度ボタンを押す必要があるので、もう一度押す
            if page.url == "https://podcasters.spotify.com/pod/login?spotifyautherror=1":
                print("認証失敗!")
                return
            await page.get_by_role("link", name="New Episode").click()
        # ネットワークのリクエストがアイドル状態になるまで待機
        await page.wait_for_load_state("load")

        # Upload
        async with page.expect_file_chooser() as fc_info:
            await page.get_by_role("button", name="Select a file", exact=True).click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(audio_file)

        # 配信の詳細を設定 (Episode Details)
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
        if explicit:
            # エピソードのタイプ
            await explicit_group.get_by_role(
                "checkbox", name="Yes", exact=True
            ).set_checked(True, force=True)

        promotional_group = page.get_by_role(
            "group", name="Promotional content (required)"
        )
        if promotional:
            await promotional_group.get_by_role(
                "radio", name="No", exact=True
            ).check(force=True)
        additional_detail = page.get_by_role(
            "button", name="Additional details (optional)"
        )
        # サムネイル差し替え時のボタンがcookieバナーに被って押せないので
        # 先にcookie ボタンの削除
        if not skip_login:
            await page.get_by_label("Cookie banner").get_by_label("Close").click()
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

        await page.get_by_role("button", name="Next").click()
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
        # # 投票機能など
        # await page.get_by_role("button", name="Next").click()
        # await page.wait_for_timeout(2000)
        # if is_publish:
        # 公開
        await page.get_by_role("button", name="Publish").click()
        #old :"https://creators.spotify.com/pod/dashboard/episodes"
        #new https://creators.spotify.com/pod/show/6MbtpFOYhvAgZDoj0w2wkc/episodes
        await page.wait_for_url("**/episodes")
        # 共有ボタンが出てくるまで待つ
        await page.wait_for_load_state("load")
        await page.get_by_role("button", name="Copy").click(force=True)
        share_url = await page.evaluate("async () => await navigator.clipboard.readText()")
        await page.wait_for_timeout(1000)
        # else:
        #     print("Skip publish")
        #     share_url = "Not Published."
        await page.close()
        await context.close()
        await browser.close()
    return share_url
