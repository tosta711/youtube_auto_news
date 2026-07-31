import os
import feedparser
from openai import OpenAI
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# ============================
# OpenAI クライアント
# ============================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================
# ニュース取得
# ============================
def fetch_news(rss_url):
    feed = feedparser.parse(rss_url)
    items = []
    for entry in feed.entries[:5]:
        items.append({
            "title": entry.title,
            "summary": entry.summary,
            "link": entry.link
        })
    return items

# ============================
# ニュース要約（OpenAI）
# ============================
def summarize_news(items):
    text = "\n".join([f"タイトル: {i['title']}\n概要: {i['summary']}" for i in items])
    prompt = f"以下のニュースを簡潔にまとめてください:\n{text}"

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content

# ============================
# スクリプト生成（OpenAI）
# ============================
def generate_script(summary):
    prompt = f"""
以下のニュース要約を元に、YouTube向けの読み上げスクリプトを作成してください。
自然で聞きやすい日本語で、丁寧に説明してください。

要約:
{summary}
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )
    return res.choices[0].message.content

# ============================
# 音声生成（OpenAI TTS）
# ============================
def generate_voice(script):
    print("OpenAI音声生成中...")

    response = client.audio.speech.create(
        model="gpt-4o-mini-tts",
        voice="alloy",
        input=script
    )

    output_path = "output_voice.mp3"
    with open(output_path, "wb") as f:
        f.write(response.read())

    return output_path

# ============================
# YouTube アップロード
# ============================
def upload_to_youtube(title, description, file_path):
    youtube = build("youtube", "v3", developerKey=os.getenv("YOUTUBE_API_KEY"))

    request_body = {
        "snippet": {
            "title": title,
            "description": description,
            "tags": ["ニュース", "自動生成", "AI"]
        },
        "status": {
            "privacyStatus": "public"
        }
    }

    media = MediaFileUpload(file_path, mimetype="audio/mp3", resumable=True)

    request = youtube.videos().insert(
        part="snippet,status",
        body=request_body,
        media_body=media
    )

    response = request.execute()
    print("YouTube アップロード完了:", response["id"])

# ============================
# メイン処理
# ============================
def main():
    rss_url = "https://news.yahoo.co.jp/rss/topics/top-picks.xml"

    print("ニュース取得中...")
    items = fetch_news(rss_url)

    print("要約生成中...")
    summary = summarize_news(items)

    print("スクリプト生成中...")
    script = generate_script(summary)

    print("音声生成中...")
    voice_file = generate_voice(script)

    print("YouTube アップロード中...")
    upload_to_youtube("今日のAIニュース", summary, voice_file)

    print("完了！")

if __name__ == "__main__":
    main()
