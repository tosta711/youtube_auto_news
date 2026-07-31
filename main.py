import os
import feedparser
import requests
from openai import OpenAI
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import ffmpeg

# -------------------------
# APIキー（環境変数から取得）
# -------------------------
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
YOUTUBE_API_KEY = os.getenv("YOUTUBE_API_KEY")
ELEVEN_API_KEY = os.getenv("ELEVEN_API_KEY")
VOICE_ID = os.getenv("VOICE_ID")

client = OpenAI(api_key=OPENAI_API_KEY)

# -------------------------
# ① 最新ニュース取得（Yahoo経済）
# -------------------------
def get_latest_news():
    url = "https://news.yahoo.co.jp/rss/topics/business.xml"
    feed = feedparser.parse(url)

    if not feed.entries:
        raise Exception("RSSフィードが取得できませんでした")

    latest = feed.entries[0]

    title = getattr(latest, "title", "タイトル不明")
    summary = getattr(latest, "summary", getattr(latest, "description", "内容不明"))

    return title, summary

# -------------------------
# ② 台本生成（OpenAI v1 API）
# -------------------------
def generate_script(title, summary):
    prompt = f"""
あなたは投資系YouTubeチャンネルの台本ライターです。
以下の最新経済ニュースの要点をもとに、10分の解説動画台本を作成してください。

【ニュース要約】
タイトル：{title}
内容：{summary}

【動画構成】
① 導入（45秒）
② ニュース概要（2分）
③ 深掘り①（2分）
④ 深掘り②（2分）
⑤ 今後の見通し（2分）
⑥ まとめ（45秒）

【条件】
・ですます調
・専門用語は必ず噛み砕いて説明
・数字・データを積極的に使う
・初心者にもわかりやすく
・2000〜2500字
・煽り禁止、断定禁止
"""

    res = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "user", "content": prompt}]
    )

    return res.choices[0].message.content

# -------------------------
# ③ 音声生成（ElevenLabs）
# -------------------------
def generate_voice(text):
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"
    headers = {"xi-api-key": ELEVEN_API_KEY}
    payload = {"text": text}

    res = requests.post(url, json=payload, headers=headers)

    if res.status_code != 200:
        raise Exception(f"ElevenLabs音声生成エラー: {res.text}")

    if len(res.content) < 1000:
        raise Exception("ElevenLabs音声が異常に短い（失敗の可能性）")

    with open("voice.mp3", "wb") as f:
        f.write(res.content)

# -------------------------
# ④ 背景画像（固定画像）
# -------------------------
def generate_background():
    img = requests.get("https://i.imgur.com/3ZQ3ZQF.png")

    if img.status_code != 200:
        raise Exception("背景画像の取得に失敗しました")

    with open("background.png", "wb") as f:
        f.write(img.content)

# -------------------------
# ⑤ 動画生成（ffmpeg PATH 明示）
# -------------------------
def generate_video():
    background = ffmpeg.input("background.png", loop=1)
    audio = ffmpeg.input("voice.mp3")

    (
        ffmpeg
        .output(
            background,
            audio,
            "output.mp4",
            vcodec="libx264",
            acodec="aac",
            shortest=None
        )
        .run(cmd="/usr/bin/ffmpeg")
    )

# -------------------------
# ⑥ YouTube投稿
# -------------------------
def upload_to_youtube(title, description):
    youtube = build("youtube", "v3", developerKey=YOUTUBE_API_KEY)

    try:
        request = youtube.videos().insert(
            part="snippet,status",
            body={
                "snippet": {
                    "title": title,
                    "description": description,
                    "tags": ["投資", "経済", "ニュース", "株式"],
                },
                "status": {"privacyStatus": "public"},
            },
            media_body=MediaFileUpload("output.mp4")
        )
        response = request.execute()
        print(response)

    except Exception as e:
        raise Exception(f"YouTube投稿エラー: {e}")

# -------------------------
# メイン処理
# -------------------------
def main():
    title, summary = get_latest_news()
    script = generate_script(title, summary)
    generate_voice(script)
    generate_background()
    generate_video()
    upload_to_youtube(title, script)

if __name__ == "__main__":
    main()
