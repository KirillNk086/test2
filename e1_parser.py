import json
import os
import time
from pathlib import Path

import openai
from telegram import Bot
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")

OPENAI_MODEL = "gpt-3.5-turbo"
openai.api_key = OPENAI_API_KEY
bot = Bot(token=TG_BOT_TOKEN)

BASE_URL = "https://www.e1.ru"

VISITED_FILE = Path("visited_news.json")


def load_seen() -> set:
    if VISITED_FILE.exists():
        with VISITED_FILE.open("r", encoding="utf-8") as fh:
            return set(json.load(fh))
    return set()


def save_seen(seen: set) -> None:
    with VISITED_FILE.open("w", encoding="utf-8") as fh:
        json.dump(sorted(seen), fh, ensure_ascii=False, indent=2)


def init_driver() -> webdriver.Chrome:
    options = Options()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    return webdriver.Chrome(options=options)

def fetch_news_list(driver: webdriver.Chrome):
    driver.get(f"{BASE_URL}/news/")
    links = []
    for elem in driver.find_elements(By.CSS_SELECTOR, "a._2kJhZ"):
        href = elem.get_attribute("href")
        if href and "/text/" in href:
            links.append(href)
    return links

def fetch_article(driver: webdriver.Chrome, url: str):
    driver.get(url)
    try:
        title = driver.find_element(By.TAG_NAME, "h1").text
    except Exception:
        title = ""
    try:
        body = driver.find_element(By.CSS_SELECTOR, "[itemprop='articleBody']").text
    except Exception:
        body = ""
    return title, body

def rewrite_text(title: str, body: str) -> str:
    prompt = (
        f"Перепиши и кратко перескажи новость на русском:\n\n"
        f"Заголовок: {title}\n\n"
        f"Текст:\n{body}"
    )
    response = openai.ChatCompletion.create(
        model=OPENAI_MODEL,
        messages=[{"role": "user", "content": prompt}],
        max_tokens=300,
        temperature=0.8,
    )
    return response["choices"][0]["message"]["content"].strip()

def send_to_telegram(text: str):
    bot.send_message(chat_id=TG_CHANNEL_ID, text=text, disable_web_page_preview=False)

def main():
    seen = load_seen()
    driver = init_driver()
    try:
        while True:
            try:
                for link in fetch_news_list(driver):
                    if link in seen:
                        continue
                    title, body = fetch_article(driver, link)
                    if not body:
                        continue
                    rewritten = rewrite_text(title, body)
                    send_to_telegram(f"{rewritten}\n\nИсточник: {link}")
                    seen.add(link)
                    save_seen(seen)
                    time.sleep(5)
            except Exception as e:
                print("Ошибка:", e)
            time.sleep(600)
    finally:
        driver.quit()

if __name__ == "__main__":
    main()
