# AIzaSyD6I4OJ7vNIo9bukOmPBdCJZMbINFXDKxU
import re
from googleapiclient.discovery import build
from urllib.parse import urlparse
from datetime import datetime, timedelta

# Replace with your API key
API_KEY = "AIzaSyD6I4OJ7vNIo9bukOmPBdCJZMbINFXDKxU"

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
    
    # Define the last year date range
    today = datetime.utcnow()
    one_year_ago = today - timedelta(days=365)
    
    # Fetch the uploads playlist for the channel
    playlist_request = youtube.channels().list(
        part="contentDetails",
        id=channel_id
    )
    playlist_response = playlist_request.execute()
    uploads_playlist_id = playlist_response["items"][0]["contentDetails"]["relatedPlaylists"]["uploads"]
    
    # Retrieve all videos from the playlist
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

    # Fetch video details and filter by published date
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

    # Sort by views and return the top 4
    top_videos = sorted(video_details, key=lambda x: x["views"], reverse=True)[:4]
    return top_videos

if __name__ == "__main__":
    youtube_url = input("Enter the YouTube channel URL: ")
    try:
        channel_id = extract_channel_id_from_url(youtube_url)
        if channel_id:
            top_videos = get_top_videos(channel_id)
            print("\nTop 4 Videos in the Last Year:")
            for video in top_videos:
                print(f"- Title: {video['title']}")
                print(f"  Views: {video['views']}")
                print(f"  Comments: {video['comments']}")
                print(f"  Likes: {video['likes']}")
                print(f"  Thumbnail URL: {video['thumbnail']}")
                print(f"  Duration: {video['duration']}")
                print(f"  Published Date: {video['published_date']}")
                print(f"  Video URL: {video['url']}\n")
        else:
            print("Could not retrieve the Channel ID.")
    except Exception as e:
        print(f"Error: {e}")
