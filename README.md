# sfp-uploader

Publish Podcast with Playwright.

```shell
python -m sfp_uploader <url> <e-mail> <password> <audio_file_path>
```


## 既存のブラウザで実行する
cmd で
```shell
"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"  --remote-debugging-port=9222  --user-data-dir=C:\tmp
```

python で
```python
 browser = await p.chromium.connect_over_cdp("http://localhost:9222")
 context = browser.contexts[0]
 page = context.pages[0]
```

https://scrapbox.io/ohbarye/Playwright%E3%81%A7%E6%97%A2%E5%AD%98%E3%81%AEChrome_profile%E3%82%92%E4%BD%BF%E3%81%A3%E3%81%9F%E8%87%AA%E5%8B%95%E5%8C%96