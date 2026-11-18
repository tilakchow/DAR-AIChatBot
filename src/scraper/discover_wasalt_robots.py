import sys
import os
import json

sys.path.insert(0, os.path.abspath('.'))

from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('https://wasalt.sa/robots.txt', wait_until='domcontentloaded')
    text = page.evaluate("() => document.body.innerText")
    print("Wasalt robots.txt content:")
    print(text)
    browser.close()
