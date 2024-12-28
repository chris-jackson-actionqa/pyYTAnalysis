import os
import re
from flask import Flask, render_template, request, jsonify
from googleapiclient.discovery import build
from urllib.parse import urlparse
from datetime import datetime, timedelta

# Fetch the API key from environment variables
API_KEY = os.getenv("YOUTUBE_API_KEY")

if not API_KEY:
    raise EnvironmentError("YOUTUBE_API_KEY environment variable not set.")

app = Flask(__name__)

def iso8601_to_hh_mm_ss(iso_duration):
    """
    Convert ISO 8601 duration to hh:mm:ss format.
    """
    match = re.match(r'PT((?P<hours>\d+)H)?((?P<minutes>\d+)M)?((?P<seconds>\d+)S)?', iso_duration)
    if not match:
        return "00:00:00"
    hours = int(match.group("hours") or 0)
    minutes = int(match.group("minutes") or 0)
    seconds = int(match.group("seconds") or 0)
    return f"{hours:02}:{minutes:02}:{seconds:02}"

def extract_channel_id_from_url(url):
    """
    Extract the channel ID from a YouTube URL.
    """
    parsed_url = urlparse(url)
    if "youtube.com/channel/" in url:
        return parsed_url.path.split("/")[-1]
    elif "youtube.com/user/" in url or "youtube.com/c/" in url:
        username = parsed_url.path.split("/")[-1]
        return get_channel_id_by_username(username)
    elif "youtube.com/@" in url:
        handle = parsed_url.path.split("@")[-1]
        return get_channel_id_by_handle(handle)
    else:
        raise ValueError("Invalid YouTube channel URL format.")

def get_channel_id_by_username(username):
    """
    Retrieve the channel ID using the YouTube username.
    """
    youtube = build("youtube", "v3", developerKey=API_KEY)
    request = youtube.channels().list(
        part="id",
        forUsername=username
    )
    response = request.execute()
    return response["items"][0]["id"] if "items" in response and response["items"] else None

def get_channel_id_by_handle(handle):
    """
    Retrieve the channel ID using the YouTube handle.
    """
    youtube = build("youtube", "v3", developerKey=API_KEY)
    request = youtube.channels().list(
        part="id",
        forHandle=f"@{handle}"
    )
    response = request.execute()
    return response["items"][0]["id"] if "items" in response and response["items"] else None

def get_top_videos(channel_id):
    """
    Fetch the top 4 videos by views from the last year for the given channel.
    """
    youtube = build("youtube", "v3", developerKey=API_KEY)
    today = datetime.utcnow()
    one_year_ago = today - timedelta(days=365)

    playlist_request = youtube.channels().list(
        part="contentDetails",
        id=channel_id
    )
    playlist_response = playlist_request.execute()
    uploads_playlist_id = playlist_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]

    video_list = []
    next_page_token = None

    while True:
        playlist_items_request = youtube.playlistItems().list(
            part="snippet",
            playlistId=uploads_playlist_id,
            maxResults=50,
            pageToken=next_page_token
        )
        playlist_items_response = playlist_items_request.execute()
        for item in playlist_items_response["items"]:
            video_id = item["snippet"]["resourceId"]["videoId"]
            video_list.append(video_id)
        next_page_token = playlist_items_response.get("nextPageToken")
        if not next_page_token:
            break

    video_details = []
    for i in range(0, len(video_list), 50):
        video_ids = ",".join(video_list[i:i+50])
        video_request = youtube.videos().list(
            part="snippet,statistics,contentDetails",
            id=video_ids
        )
        video_response = video_request.execute()
        for video in video_response["items"]:
            published_at = datetime.strptime(video["snippet"]["publishedAt"], "%Y-%m-%dT%H:%M:%SZ")
            if published_at >= one_year_ago:
                duration = iso8601_to_hh_mm_ss(video["contentDetails"]["duration"])
                video_details.append({
                    "title": video["snippet"]["title"],
                    "views": int(video["statistics"]["viewCount"]),
                    "comments": int(video["statistics"].get("commentCount", 0)),
                    "likes": int(video["statistics"].get("likeCount", 0)),
                    "thumbnail": video["snippet"]["thumbnails"]["high"]["url"],
                    "url": f"https://www.youtube.com/watch?v={video['id']}",
                    "duration": duration,
                    "published_date": published_at.strftime("%Y-%m-%d")
                })

    return sorted(video_details, key=lambda x: x["views"], reverse=True)[:4]

@app.route('/')
def index():
    return render_template("index.html")

@app.route('/get_top_videos', methods=['POST'])
def get_top_videos_route():
    data = request.json
    youtube_url = data.get("youtube_url")
    try:
        channel_id = extract_channel_id_from_url(youtube_url)
        if channel_id:
            videos = get_top_videos(channel_id)
            return jsonify(videos)
        else:
            return jsonify({"error": "Could not retrieve the Channel ID."}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 400

if __name__ == '__main__':
    app.run(debug=True)
