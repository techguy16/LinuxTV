import os
import time
import requests
import schedule
import subprocess
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import threading

# GitHub URLs for daily updates
VIDEOS_URL = "https://raw.githubusercontent.com/techguy16/LinuxTV/refs/heads/main/videos.txt"
ADS_URL = "https://raw.githubusercontent.com/techguy16/LinuxTV/refs/heads/main/ads.txt"
NEWS_URL = "https://raw.githubusercontent.com/techguy16/LinuxTV/refs/heads/main/news.txt"

# HLS Output Directory
HLS_PATH = "hls"
os.makedirs(HLS_PATH, exist_ok=True)

# Global Variables
playlist = []
ads = []
news_text = ""

# Function to update video/ads/news list
def update_playlists():
    global playlist, ads, news_text
    try:
        playlist = requests.get(VIDEOS_URL).text.strip().split("\n")
        ads = requests.get(ADS_URL).text.strip().split("\n")
        news_text = requests.get(NEWS_URL).text.strip()
    except Exception as e:
        print(f"Failed to update playlists: {e}")

# Function to stream a YouTube video via HLS
def stream_youtube(url):
    command = [
        "yt-dlp", "-f", "best[height<=720]", "-o", "-", url,
        "|", "ffmpeg", "-re", "-i", "pipe:0",
        "-i", "tux.png",  # Load Tux image
        "-filter_complex", "overlay=W-w-10:H-h-10",  # Position Tux in the bottom-right
        "-c:v", "libx264", "-preset", "fast", "-b:v", "1500k",
        "-s", "1280x720", "-c:a", "aac", "-b:a", "128k",
        "-hls_time", "10", "-hls_list_size", "5",
        "-f", "hls", f"{HLS_PATH}/linuxTV.m3u8"
    ]
    subprocess.run(" ".join(command), shell=True)

# Function to show news with text overlay
def stream_news():
    command = [
        "ffmpeg", "-loop", "1", "-i", "news_bg.jpg",
        "-f", "lavfi", "-i", "anullsrc",
        "-i", "tux.png",  # Load Tux
        "-filter_complex", "drawtext=text='Linux News':fontcolor=white:fontsize=30:x=100:y=50,overlay=W-w-10:H-h-10",
        "-t", "3600", "-s", "1280x720", "-c:v", "libx264", "-c:a", "aac",
        "-hls_time", "10", "-hls_list_size", "5",
        "-f", "hls", f"{HLS_PATH}/linuxTV.m3u8"
    ]
    subprocess.run(command)

# Function to start the Python HTTP server
def start_http_server():
    os.chdir(HLS_PATH)
    server = HTTPServer(("0.0.0.0", 8080), SimpleHTTPRequestHandler)
    print("Server started at http://localhost:8080")
    server.serve_forever()

# Streaming loop
def start_stream():
    update_playlists()
    video_index, ad_index = 0, 0

    while True:
        now = time.localtime()

        # Show Linux news at 6 AM and 6 PM
        if now.tm_hour in [6, 18]:
            print("Streaming Linux News")
            stream_news()

        # Play next video in the playlist
        if video_index >= len(playlist):
            video_index = 0
        print(f"Streaming: {playlist[video_index]}")
        stream_youtube(playlist[video_index])
        video_index += 1

        # Insert an ad every 5 minutes
        if ad_index < len(ads):
            print(f"Streaming Ad: {ads[ad_index]}")
            stream_youtube(ads[ad_index])
            ad_index += 1
        else:
            ad_index = 0

# Schedule daily playlist updates
schedule.every().day.at("00:00").do(update_playlists)

# Start HTTP server in a separate thread
server_thread = threading.Thread(target=start_http_server, daemon=True)
server_thread.start()

# Start streaming
if __name__ == "__main__":
    start_stream()
