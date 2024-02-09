from datetime import datetime
from typing import Optional

from playwright.async_api import async_playwright


async def publish(url: str, email: str, password: str, audio_file: str, title: str, description: str,
                  schedule: Optional[datetime] = None, explicit: bool = False):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        # change language to English
        await context.add_cookies([{
            "name": "sp_locale",
            "value": "en",
            "url": "https://podcasters.spotify.com/"
        }])
        await context.grant_permissions(['clipboard-read', 'clipboard-write', 'accessibility-events'])

        page = await context.new_page()
        await page.goto(url)

        await page.get_by_role("button", name="Continue", exact=True).click()
        await page.get_by_role("textbox", name="Enter your email").fill(email)
        await page.get_by_role("textbox", name="Enter your password").fill(password)
        await page.get_by_role("button", name="Log in", exact=True).click()
        await page.get_by_role("link", name="New Episode").click()
        async with page.expect_file_chooser() as fc_info:
            await page.get_by_role("button", name="Select a file").click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(audio_file)
        # 配信の詳細
        await page.get_by_role("textbox", name="Title (required)", exact=True).fill(title)
        await page.get_by_role("textbox", name="", exact=True).fill(description)
        # スケジュール
        if schedule:
            # Schedule
            await page.get_by_role("radio", name="Schedule").set_checked(True, force=True)
            mdy = schedule.strftime("%m/%d/%Y")
            await page.get_by_role("textbox", name="Date").fill(mdy, force=True)
            await page.get_by_role("textbox", name="Hour picker").fill(schedule.strftime("%H"), force=True)
            await page.get_by_role("textbox", name="Minute picker").fill(schedule.strftime("%M"), force=True)
            await page.get_by_role("combobox", name="Meridiem picker").select_option(schedule.strftime("%p"),
                                                                                     force=True)
        else:
            # Publish now
            await page.get_by_role("radio", name="Now").set_checked(True, force=True)
        if explicit:
            # エピソードのタイプ
            await page.get_by_role("radio", name="Yes").set_checked(True, force=True)
        else:
            await page.get_by_role("radio", name="No").set_checked(True, force=True)

        # cookie ボタンの削除
        await page.get_by_label("Cookie banner").get_by_label("Close").click()
        await page.get_by_role("button", name="Next").click()
        # 投票機能など
        await page.get_by_role("button", name="Next").click()
        # 公開
        await page.get_by_role("button", name="Publish").click()

        await page.wait_for_url("https://podcasters.spotify.com/pod/dashboard/episodes")
        await page.get_by_role("button", name="Copy link to your episode").click()
        share_url = await page.evaluate("navigator.clipboard.readText()")
        await page.close()
        await context.close()
        await browser.close()
    return share_url
