import os
from datetime import datetime
from typing import Optional

from playwright.async_api import async_playwright

_publish_url = "https://podcasters.spotify.com/pod/dashboard/episodes"


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
):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        # change language to English
        await context.add_cookies(
            [
                {
                    "name": "sp_locale",
                    "value": "en",
                    "url": "https://podcasters.spotify.com/",
                }
            ]
        )
        await context.grant_permissions(
            ["clipboard-read", "clipboard-write", "accessibility-events"]
        )

        page = await context.new_page()
        # ログイン
        await page.goto(url)
        await page.get_by_role("button", name="Continue", exact=True).click()
        await page.get_by_role("textbox", name="Enter your email").fill(email)
        await page.get_by_role("textbox", name="Enter your password").fill(password)
        await page.get_by_role("button", name="Log in", exact=True).click()
        # エピソードの追加
        await page.get_by_role("link", name="New Episode").click()
        async with page.expect_file_chooser() as fc_info:
            await page.get_by_role("button", name="Select a file", exact=True).click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(audio_file)
        # 配信の詳細を設定
        await page.get_by_role("textbox", name="Title (required)", exact=True).fill(
            title
        )
        await page.get_by_role("textbox", name="", exact=True).fill(description)
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
        explicit_group = page.get_by_role("group", name="Explicit content (required)")
        if explicit:
            # エピソードのタイプ
            await explicit_group.get_by_role(
                "radio", name="Yes", exact=True
            ).set_checked(True, force=True)
        else:
            await explicit_group.get_by_role(
                "radio", name="No", exact=True
            ).set_checked(True, force=True)

        promotional_group = page.get_by_role(
            "group", name="Promotional content (required)"
        )
        if promotional:
            await promotional_group.get_by_role(
                "radio", name="Yes", exact=True
            ).set_checked(True, force=True)
        else:
            await promotional_group.get_by_role(
                "radio", name="No", exact=True
            ).set_checked(True, force=True)
        additional_detail = page.get_by_role(
            "button", name="Additional details (optional)"
        )
        # サムネイル差し替え時のボタンがcookieバナーに被って押せないので
        # 先にcookie ボタンの削除
        await page.get_by_label("Cookie banner").get_by_label("Close").click()
        # サムネイルを差し替え
        if thumbnail:
            if os.path.exists(thumbnail):
                await additional_detail.click()
                async with page.expect_file_chooser() as fc_info:
                    await page.get_by_role(
                        "button", name="Episode cover art Change"
                    ).click()
                file_chooser = await fc_info.value
                await file_chooser.set_files(thumbnail)
                thumbnail_dialog = page.get_by_role("dialog", name="image uploader")
                # 確定
                await thumbnail_dialog.get_by_role("button", name="Save").click()

            else:
                print(
                    "Skip thumbnail replacement because the file does not exist.:{thumbnail}"
                )

        await page.get_by_role("button", name="Next").click()
        # 投票機能など
        await page.get_by_role("button", name="Next").click()
        if is_publish:
            # 公開
            await page.get_by_role("button", name="Publish").click()

            await page.wait_for_url(_publish_url)
            await page.get_by_role("button", name="Copy link to your episode").click()
            share_url = await page.evaluate("navigator.clipboard.readText()")
        else:
            print("Skip publish")
            share_url = "Not Published."
        await page.close()
        await context.close()
        await browser.close()
    return share_url
