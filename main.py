import requests
import json
import time
import os
import subprocess
import threading
from flask import Flask, Response
from yt_dlp import YoutubeDL

os.system("curl ifconfig.me")
app = Flask(__name__)

# Global variables
headlines = []
headline_index = 0
frame_time = 1 / 30  # Assuming 30 FPS for the video
video_queue = []
video_urls = [
    "https://www.youtube.com/watch?v=227EQhL4tAw",
    "https://www.youtube.com/watch?v=dQw4w9WgXcQ",
    "https://www.youtube.com/watch?v=227EQhL4tAw"
    # Add more video URLs as needed
]

# Fetch Distrowatch headlines
def fetch_headlines():
    url = "https://raw.githubusercontent.com/OpenStatsLab/distrowatch-parsed/main/parsed/news.json"
    response = requests.get(url)
    data = response.json()
    headlines = [item["title"] for item in data]
    return headlines

# Download video using yt-dlp
def download_video(url):
    ydl_opts = {
        'format': 'bestvideo+bestaudio/best',
        'quiet': True,
        'outtmpl': '%(id)s.%(ext)s',
        'merge_output_format': 'mp4'
    }
    with YoutubeDL(ydl_opts) as ydl:
        info_dict = ydl.extract_info(url, download=False)
        formats = info_dict.get('formats', [info_dict])
        video_url = next((f['url'] for f in reversed(formats) if f['video_ext'] != 'none'), None)
        audio_url = next((f['url'] for f in reversed(formats) if f['audio_ext'] != 'none'), None)
        return video_url, audio_url

# Generate video with headlines
def generate_video():
    global headlines, headline_index, frame_time, video_queue, video_urls
    headline_duration = 15  # Display each headline for 15 seconds
    headline_start_time = time.time()
    video_index = 0

    while True:
        current_time = time.time()

        if current_time - headline_start_time >= headline_duration:
            headline_index = (headline_index + 1) % len(headlines)
            headline_start_time = current_time
            
        headstr = "DISTROWATCH HEADLINES: "
        for headline in headlines:
            headstr += headline.replace(":", ",") + " - "
        
        # Get the next video in the queue or play the default video
        if video_queue:
            video_url, audio_url = video_queue.pop(0)
        else:
            if video_index >= len(video_urls):
                video_index = 0
            video_url, audio_url = download_video(video_urls[video_index])
            video_index += 1
        
        # FFmpeg command to add headlines and stream
        cmd = [
            'ffmpeg',
            '-re',
            '-i', video_url,
            '-i', audio_url,
            '-vf', f"scale=(iw*sar)*min(1280/(iw*sar)\,720/ih):ih*min(1280/(iw*sar)\,720/ih),setsar=1,pad=1280:720:'(ow-iw)/2':'(oh-ih)/2',drawtext=text='{headstr}':fontcolor=white:fontsize=24:x=w-mod(max(t-1\,0)*(w+tw)/25\,(w+tw)):y=h-line_h-10",
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-f', 'flv',
            '-'
        ]
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE)
        while True:
            data = process.stdout.read(1024)
            if not data:
                break
            yield data
        process.stdout.close()
        process.wait()

@app.route('/video_feed')
def video_feed():
    return Response(generate_video(), mimetype='video/mp4')

if __name__ == '__main__':
    # Fetch headlines once at the start
    headlines = fetch_headlines()
    
    # Download videos in a separate thread to avoid blocking
    def download_videos():
        global video_queue
        for url in video_urls:
            video_url, audio_url = download_video(url)
            video_queue.append((video_url, audio_url))

    threading.Thread(target=download_videos).start()
    threading.Thread(target=generate_video).start()
    app.run(host='0.0.0.0', port=5000)