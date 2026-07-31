import os
import json
import feedparser
from openai import OpenAI
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials

# ============================
# OpenAI クライアント
# ============================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# ============================
# YouTube OAuth2 認証
# ============================
def get_youtube_service():
    oauth_json = os.getenv("YOUTUBE_OAUTH_JSON")
    data = json.loads(oauth_json)

    scopes = ["https://www.googleapis.com/auth/youtube.upload"]

    with open("temp_credentials.json", "w") as f:
        json.dump(data, f)

    flow = InstalledAppFlow.from_client_secrets_file(
        "temp_credentials.json", scopes=scopes
    )

    creds = flow.run_local_server(port=0)

    return build("youtube", "v3", credentials=creds)

# ============================
# ニュース取得
# ============================
def fetch_news(rss_url):
    feed = feedparser.parse(rss_url)
    items = []

    for entry in feed.entries[:5]:
        summary = None

        if hasattr(entry, "summary"):
            summary = entry.summary
        elif hasattr(entry, "description"):
            summary = entry.description
        else:
            summary = entry.title

        items.append({
            "title": entry.title,
            "summary": summary,
            "link": entry.link
        })

    return items

# ============================
# 要約生成
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
# スクリプト生成
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
    youtube = get_youtube_service()

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

    items = fetch_news(rss_url)
    summary = summarize_news(items)
    script = generate_script(summary)
    voice_file = generate_voice(script)
    upload_to_youtube("今日のAIニュース", summary, voice_file)

if __name__ == "__main__":
    main()
