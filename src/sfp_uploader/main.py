from playwright.async_api import async_playwright
from playwright.sync_api import sync_playwright


async def publish_async(url: str, email: str, password: str, audio_file: str, title: str, description: str):
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        await context.grant_permissions(['clipboard-read', 'clipboard-write', 'accessibility-events'])

        page = await context.new_page()
        await page.goto(url)

        await page.get_by_role("button", name="続行").click()
        await page.locator(selector="#email").fill(email)
        await page.locator(selector="#password").fill(password)
        await page.get_by_role("button", name="ログイン").click()
        await page.get_by_role("link", name="新しいエピソード").click()

        async with page.expect_file_chooser() as fc_info:
            await page.get_by_role("button", name="ファイルを選択").click()
        file_chooser = await fc_info.value
        await file_chooser.set_files(audio_file)
        # 配信の詳細
        await page.locator("#title-input").fill(title)
        await page.locator("div[role='textbox']").fill(description)
        await page.locator('input[type="radio"][id="publish-date-now"]').set_checked(True, force=True)
        await page.locator('input[type="radio"][id="no-explicit-content"]').set_checked(True, force=True)
        # cookie ボタンの削除
        await page.locator("#onetrust-close-btn-container > button").click()
        await page.get_by_role("button", name="次へ").click()
        # 投票機能など
        await page.get_by_role("button", name="次へ").click()
        # 公開
        await page.get_by_role("button", name="公開する").click()
        await page.wait_for_url("https://podcasters.spotify.com/pod/dashboard/episodes")
        await page.get_by_role("button", name="リンクをコピー").click()
        share_url = await page.evaluate("navigator.clipboard.readText()")
        await page.close()
        await context.close()
        await browser.close()
    return share_url


def publish(url: str, email: str, password: str, audio_file: str, title: str, description: str):
    # p = sync_playwright().start()
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context()
        context.grant_permissions(['clipboard-read', 'clipboard-write', 'accessibility-events'])

        page = context.new_page()
        page.goto(url)

        page.get_by_role("button", name="続行").click()
        page.locator(selector="#email").fill(email)
        page.locator(selector="#password").fill(password)
        page.get_by_role("button", name="ログイン").click()
        page.get_by_role("link", name="新しいエピソード").click()
        with page.expect_file_chooser() as fc_info:
            page.get_by_role("button", name="ファイルを選択").click()
        file_chooser = fc_info.value
        file_chooser.set_files(audio_file)
        # 配信の詳細
        page.locator("#title-input").fill(title)
        page.locator("div[role='textbox']").fill(description)
        page.locator('input[type="radio"][id="publish-date-now"]').set_checked(True, force=True)
        page.locator('input[type="radio"][id="no-explicit-content"]').set_checked(True, force=True)
        # cookie ボタンの削除
        page.locator("#onetrust-close-btn-container > button").click()
        page.get_by_role("button", name="次へ").click()
        # 投票機能など
        page.get_by_role("button", name="次へ").click()
        # 公開
        page.get_by_role("button", name="公開する").click()
        page.wait_for_url("https://podcasters.spotify.com/pod/dashboard/episodes")
        page.get_by_role("button", name="リンクをコピー").click()
        share_url = page.evaluate("navigator.clipboard.readText()")
        page.close()
        context.close()
        browser.close()
    return share_url
