import os
import time
import requests
from bs4 import BeautifulSoup
import openai
from telegram import Bot

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
TG_BOT_TOKEN = os.getenv("TG_BOT_TOKEN")
TG_CHANNEL_ID = os.getenv("TG_CHANNEL_ID")

OPENAI_MODEL = "gpt-3.5-turbo"
openai.api_key = OPENAI_API_KEY
bot = Bot(token=TG_BOT_TOKEN)

BASE_URL = "https://www.e1.ru"

def fetch_news_list():
    url = f"{BASE_URL}/news/"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    news_links = []
    for link in soup.select("a._2kJhZ"):
        href = link.get("href")
        if href and "/text/" in href:
            news_links.append(BASE_URL + href)
    return news_links

def fetch_article(url: str):
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    title = soup.find("h1")
    body = soup.find("div", {"itemprop": "articleBody"})
    return (
        title.get_text(strip=True) if title else "",
        body.get_text(separator="\n", strip=True) if body else "",
    )

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
    seen = set()
    while True:
        try:
            for link in fetch_news_list():
                if link in seen:
                    continue
                title, body = fetch_article(link)
                if not body:
                    continue
                rewritten = rewrite_text(title, body)
                send_to_telegram(f"{rewritten}\n\nИсточник: {link}")
                seen.add(link)
                time.sleep(5)
        except Exception as e:
            print("Ошибка:", e)
        time.sleep(600)

if __name__ == "__main__":
    main()
