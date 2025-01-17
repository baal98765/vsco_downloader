import streamlit as st
from vsco_downloader import download as vsco_download
import instaloader
import requests
import os
from typing import Optional, List
import yt_dlp
import shutil
from datetime import datetime
import asyncio
from zipfile import ZipFile
import time
import io
from io import BytesIO
import re
import urllib.request as ur
import traceback as tb
import zipfile
from concurrent.futures import ThreadPoolExecutor
import json
import requests
from bs4 import BeautifulSoup
import aiohttp
import aiofiles
from subprocess import Popen, PIPE


def display_media_in_grid(media_files, num_cols=4):
    """Displays media files in a grid layout."""
    cols = st.columns(num_cols)  # Number of columns for the grid
    for idx, media in enumerate(media_files):
        with cols[idx % num_cols]:  # Rotate through columns
            if media.lower().endswith(('.png', '.jpg', '.jpeg')):
                st.image(media, use_container_width=True)
            elif media.lower().endswith(('.mp4', '.mov')):
                st.video(media)

def run_gallery_dl(username):
    """Runs gallery-dl to download VSCO gallery for a given username."""
    command = ["gallery-dl", f"https://vsco.co/{username}/gallery", "-d", f"downloads/{username}"]
    process = Popen(command, stdout=PIPE, stderr=PIPE)
    stdout, stderr = process.communicate()
    return process.returncode, stdout.decode(), stderr.decode()

def create_zip_files(user_dir, max_size):
    """Creates zip files of downloaded media, limiting each zip to max_size."""
    part_index = 1
    current_zip_size = 0
    zip_files = []
    zip_filename = f"{user_dir}_media_part_{part_index}.zip"
    
    with zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, _, files in os.walk(user_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)

                if current_zip_size + file_size > max_size:
                    zip_files.append(zip_filename)
                    part_index += 1
                    zip_filename = f"{user_dir}_media_part_{part_index}.zip"
                    zipf = zipfile.ZipFile(zip_filename, "w", zipfile.ZIP_DEFLATED)
                    current_zip_size = 0

                zipf.write(file_path, os.path.relpath(file_path, user_dir))
                current_zip_size += file_size

        zip_files.append(zip_filename)  # Add the last zip file

    return zip_files


# Function to extract username from the VSCO URL
def extract_username(url):
    match = re.search(r"vsco\.co/([^/]+)/", url)
    return match.group(1) if match else "unknown_user"

# Function to download media and prepare for user download
def prepare_download(media_url):
    try:
        response = requests.get(media_url, stream=True)
        response.raise_for_status()
        file_extension = media_url.split('.')[-1]
        file_name = f"media.{file_extension}"
        return file_name, response.content
    except Exception as e:
        st.error(f"Failed to prepare download for: {media_url}. Error: {e}")
        return None, None


def get_gallery_urls(username):
    try:
        # Construct gallery URL for VSCO username
        gallery_url = f"https://vsco.co/{username}/gallery"
        request_header = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64)"}
        request = ur.Request(gallery_url, headers=request_header)
        data = ur.urlopen(request).read()

        # Extract the JSON state embedded in the HTML page
        data_cleaned_1 = str(data).split("<script>window.__PRELOADED_STATE__ =")[1]
        data_cleaned_2 = str(data_cleaned_1).split("</script>")[0]
        data_cleaned_3 = str(data_cleaned_2).strip()
        data_cleaned_4 = str(data_cleaned_3).replace("\\x", "\\u00")
        data_cleaned_5 = re.sub(r'(?<!\\)\\(?!["\\/bfnrt]|u[0-9a-fA-F]{4})', r'', data_cleaned_4)

        # Load the cleaned JSON data from the HTML page
        json_data = json.loads(data_cleaned_5)

        # Check if images exist in the data
        images = json_data.get("entities", {}).get("images", {})
        if not images:
            print("WARNING: No images found in gallery data!")
            return []

        # Collect all image URLs from the 'images' key in the JSON data
        media_urls = [image_data.get("responsiveUrl").replace("\\u002F", "/") for image_data in images.values() if image_data.get("responsiveUrl")]
        
        # Ensure all URLs start with 'https://'
        media_urls = [f"https://{url}" if not url.startswith("https://") else url for url in media_urls]
        
        # Limit the number of media URLs to 14 images (default limit on non-logged-in page)
        media_urls = media_urls[:14]  # Get only the first 14 images if available

        return media_urls

    except Exception as e:
        print(f"ERROR: An unexpected error occurred while fetching gallery URLs: {e}")
        return []
def vsco_page():
    st.title("VSCO Downloader")
    
    # Add VSCO logo at the top
    vsco_logo_url = "https://th.bing.com/th/id/OIP.E36Cq-gP4UrriuCW0kxRRQHaFK?rs=1&pid=ImgDetMain"  # URL for VSCO logo
    st.image(vsco_logo_url, width=200)  # Display logo with specified width

    general_description = """
    VSCO Downloader is a simple script to extract raw image and video paths from [VSCO](https://www.vsco.co/) posts.
    """
    st.markdown(general_description)

    # Create tabs for different sections
    tabs = st.tabs(["Extract Post Media", "User Gallery"])

    with tabs[0]:  # "Extract Post Media" tab
        st.subheader("Extract Post Media")

        url_input = st.text_input(
            "VSCO Post URLs (comma-separated):",
            placeholder="https://vsco.co/user1/media/12345, https://vsco.co/user2/media/12345",
            help="Comma-separated list of VSCO post URLs from which media should be extracted.",
        )

        # Center button to start download process
        l1, l2, center_button, r1, r2 = st.columns(5)

        with center_button:
            download = st.button("Download!", type="primary", use_container_width=True)

        if download:
            # Split the input string by commas and process each URL
            urls = [url.strip() for url in url_input.split(",")]
            media_urls = []
            for url in urls:
                media_urls.extend(vsco_download(url, True, False))  # Fetch media URLs for each input URL

            if media_urls:
                st.subheader("Extracted Post Media")

                # Determine ZIP file name using the first username found
                usernames = [extract_username(url) for url in urls]
                unique_usernames = list(set(usernames))  # Ensure unique usernames
                zip_name = f"{'_'.join(unique_usernames)}_vsco.zip"

                # Create a list of columns for the grid layout
                num_columns = 3  # You can adjust this number
                columns = st.columns(num_columns)

                # Display media in grid layout
                col_idx = 0  # To keep track of the column index
                for media_url in media_urls:
                    with columns[col_idx]:
                        # Display image or video
                        if media_url.endswith((".jpg", ".jpeg", ".png", ".gif")):
                            st.image(media_url, caption="Extracted Image", width=200)  # Adjust width as necessary
                        elif media_url.endswith((".mp4", ".mov", ".avi")):
                            st.video(media_url, caption="Extracted Video", format="video/mp4")

                    # Move to the next column
                    col_idx += 1
                    if col_idx >= num_columns:
                        col_idx = 0  # Reset column index after every 'num_columns' items

                # Prepare a ZIP file in memory for download
                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w") as zf:
                    for media_url in media_urls:
                        # Add media to the ZIP file
                        file_name, file_content = prepare_download(media_url)
                        if file_name and file_content:
                            zf.writestr(file_name, file_content)

                zip_buffer.seek(0)  # Rewind the buffer for download

                # Button to download the ZIP file
                st.download_button(
                    label="Download All Media",
                    data=zip_buffer,
                    file_name=zip_name,
                    mime="application/zip",
                )
            else:
                st.warning("No media found. Please check the URLs and try again.")

    with tabs[1]:  # "User Gallery" tab
        st.subheader("User Gallery")

        username_input = st.text_input(
            "Enter a VSCO Username:",
            placeholder="username",
            help="Provide a VSCO username to fetch their gallery.",
        )

        if username_input:
            st.info(f"Fetching gallery for username: {username_input}")

            # Run gallery-dl to download media
            returncode, stdout, stderr = run_gallery_dl(username_input)
            if returncode == 0:
                st.success("Gallery downloaded successfully!")

                # Path to downloaded media
                user_dir = f"downloads/{username_input}"
                max_zip_size = 50 * 1024 * 1024  # 50 MB

                # Create zip files
                zip_files = create_zip_files(user_dir, max_zip_size)

                # Display download links for zip files
                for idx, zip_file in enumerate(zip_files, start=1):
                    with open(zip_file, "rb") as f:
                        st.download_button(
                            label=f"Download Part {idx}",
                            data=f,
                            file_name=os.path.basename(zip_file),
                            mime="application/zip",
                        )
            else:
                st.error("Failed to fetch gallery. Please check the username.")
                st.error(stderr)
        with tabs[2]:  # "User Gallery Viewer" tab
        st.subheader("User Gallery Viewer")

        username_input = st.text_input(
            "Enter a VSCO Username to View Gallery:",
            placeholder="username",
            key="user_gallery_viewer"
        )

        if username_input:
            st.info(f"Fetching gallery for username: {username_input}")

            # Create a temporary directory for downloads
            with tempfile.TemporaryDirectory() as temp_dir:
                download_dir = os.path.join(temp_dir, username_input)
                os.makedirs(download_dir, exist_ok=True)

                # Run gallery-dl to download media
                returncode, stdout, stderr = run_gallery_dl(username_input, download_dir)
                if returncode == 0:
                    st.success("Gallery downloaded successfully!")

                    # List media files (limit to 100)
                    media_files = [
                        os.path.join(download_dir, f)
                        for f in os.listdir(download_dir)
                        if f.lower().endswith(('.png', '.jpg', '.jpeg', '.mp4', '.mov'))
                    ][:100]

                    if media_files:
                        st.write(f"Displaying the first {len(media_files)} posts:")
                        display_media_in_grid(media_files, num_cols=4)
                    else:
                        st.warning("No media found in the gallery.")
                else:
                    st.error("Failed to fetch gallery. Please check the username.")
                    st.error(stderr)
    # Sidebar with social link and description
    st.sidebar.title("Follow Us")
    st.sidebar.markdown("[Telegram](https://t.me/TTKgroups)")

    # Informative description in the sidebar
    st.sidebar.subheader("About This Site")
    st.sidebar.markdown("""
    This website is created by **TTKgroups**. You can use this tool to download media from various platforms like **VSCO**, **Instagram**, **Snapchat**, **Tiktok** and more coming soon!

    Stay tuned for additional features and support for more platforms!
    """)

class TikTokDownloader:
    def __init__(self, save_path: str = 'tiktok_videos'):
        self.save_path = save_path
        self.create_save_directory()

    def create_save_directory(self) -> None:
        """Create the save directory if it doesn't exist."""
        if not os.path.exists(self.save_path):
            os.makedirs(self.save_path)

    @staticmethod
    def validate_url(url: str) -> bool:
        """Validate if the provided URL is a TikTok URL."""
        tiktok_pattern = r'https?://((?:vm|vt|www)\.)?tiktok\.com/.*'
        return bool(re.match(tiktok_pattern, url))

    @staticmethod
    def get_username_video_url(username: str) -> str:
        """Construct TikTok video URL from username."""
        return f'https://www.tiktok.com/@{username}'

    @staticmethod
    def progress_hook(d: dict) -> None:
        """Hook to display download progress."""
        if d['status'] == 'downloading':
            progress = d.get('_percent_str', 'N/A')
            speed = d.get('_speed_str', 'N/A')
            eta = d.get('_eta_str', 'N/A')
            print(f"Downloading: {progress} at {speed} ETA: {eta}", end='\r')
        elif d['status'] == 'finished':
            print("\nDownload completed, finalizing...")

    def get_filename(self, video_url: str, custom_name: Optional[str] = None) -> str:
        """Generate filename for the video."""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        if custom_name:
            return f"{custom_name}_{timestamp}.mp4"
        return f"tiktok_{timestamp}.mp4"

    def download_video(self, video_url: str, custom_name: Optional[str] = None) -> Optional[str]:
        """Download a TikTok video."""
        if not self.validate_url(video_url):
            return None

        filename = self.get_filename(video_url, custom_name)
        output_path = os.path.join(self.save_path, filename)

        ydl_opts = {
            'outtmpl': output_path,
            'format': 'bestvideo+bestaudio/best',
            'noplaylist': True,
            'quiet': False,
            'progress_hooks': [self.progress_hook],
            'http_headers': {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            },
            'no_postoverwrites': True,
            'postprocessors': [
                {
                    'key': 'FFmpegVideoConvertor',
                    'preferedformat': 'mp4',
                }
            ],
        }

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([video_url])

            # Check the file size, skip if over 100MB
            if os.path.getsize(output_path) > 100 * 1024 * 1024:
                print(f"File {filename} is too large (>100MB), skipping.")
                os.remove(output_path)
                return None

            return output_path
        except yt_dlp.utils.DownloadError as e:
            print(f"Error downloading video: {str(e)}")
        except Exception as e:
            print(f"An unexpected error occurred: {str(e)}")

        return None

    def download_recent_videos(self, username: str, num_videos: int = 10) -> List[str]:
        """Download the latest videos from a user's TikTok profile."""
        video_urls = []
        profile_url = self.get_username_video_url(username)

        # Use yt_dlp to fetch the recent video URLs from the TikTok profile page
        ydl_opts = {
            'quiet': True,
            'extract_flat': True,
            'noplaylist': True,
            'force_generic_extractor': True,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            result = ydl.extract_info(profile_url, download=False)
            # Extract video URLs, limit to the first 'num_videos'
            for video in result['entries'][:num_videos]:
                video_urls.append(video['url'])

        # Download the videos, skipping large files
        downloaded_files = []
        for url in video_urls:
            file_path = self.download_video(url)
            if file_path:
                downloaded_files.append(file_path)

        return downloaded_files


# Helper function to download and display TikTok videos in a grid
def handle_tiktok_download(username: str, num_videos: int):
    downloader = TikTokDownloader()
    st.info(f"Fetching videos for TikTok user: @{username}...")
    try:
        video_files = downloader.download_recent_videos(username, num_videos=num_videos)
        if not video_files:
            st.warning("No videos downloaded. Check username or try again later.")
        else:
            st.success(f"Downloaded {len(video_files)} videos successfully!")

            # Display videos in a grid layout
            num_columns = 3  # Number of videos per row
            for i in range(0, len(video_files), num_columns):
                cols = st.columns(num_columns)  # Create columns for the row
                for col, file_path in zip(cols, video_files[i:i+num_columns]):
                    if file_path.endswith(".mp4"):
                        col.video(file_path, format="video/mp4")
                        col.caption(f"Video: {file_path.split('/')[-1]}")
    except Exception as e:
        st.error(f"An error occurred while downloading videos: {str(e)}")
# Helper function to download and display TikTok videos in a grid
def handle_tiktok_video_url(url: str):
    downloader = TikTokDownloader()
    st.info(f"Fetching video from URL: {url}...")
    try:
        # Download the video directly from the URL
        video_file = downloader.download_video(url)
        if not video_file:
            st.warning("No video downloaded. Check the URL or try again later.")
        else:
            st.success(f"Downloaded video successfully!")

            # Display the video
            st.video(video_file, format="video/mp4")
            st.caption(f"Video: {video_file.split('/')[-1]}")
    except Exception as e:
        st.error(f"An error occurred while downloading the video: {str(e)}")


# TikTok page with sub-tabs for URL input and username input
def tiktok_page():
    st.title("📹 TikTok Video Downloader")
    st.markdown(
        """
        This tool allows you to download a TikTok video directly from a URL or from a TikTok user profile.
        Simply enter the URL of the video or the username, then select the number of videos to fetch.
        """
    )

    # Sub-tab for username input
    with st.expander("👤 Enter TikTok Username"):
        username = st.text_input("TikTok Username", placeholder="e.g., tiktok_username")
    
    # Sub-tab for URL input
    with st.expander("🔗 Enter TikTok Video URL"):
        url = st.text_input("TikTok Video URL", placeholder="e.g., https://www.tiktok.com/@username/video/1234567890")

    # Select number of videos (only for username)
    num_videos = st.slider("Number of Videos to Download", min_value=1, max_value=10, value=1)

    # Determine which input is provided (username or URL)
    if st.button("📥 Fetch TikTok Videos"):
        if url and TikTokDownloader.validate_url(url):
            # If URL is provided, directly download the video
            handle_tiktok_video_url(url)
        elif username:
            # If a username is provided, download recent videos from that profile
            handle_tiktok_download(username, num_videos)
        else:
            st.warning("Please enter a valid TikTok username or URL.")
# Initialize instaloader object
L = instaloader.Instaloader()

# Define the session file path
session_file_path = "session-lil.wasson.fanpage"  # Update to match your actual session file path

# Ensure that the session file exists before loading
if os.path.exists(session_file_path):
    L.load_session_from_file("baal123487", session_file_path)  # Use correct file path
else:
    print("Session file not found!")

# Add custom CSS for Instagram theme
def add_custom_css():
    st.markdown(
        """
        <style>
        body {
            background: linear-gradient(to right, #feda75, #fa7e1e, #d62976, #962fbf, #4f5bd5);
            color: white;
            font-family: "Arial", sans-serif;
        }
        .css-18e3th9 {
            background-color: rgba(255, 255, 255, 0.1);
            border-radius: 10px;
        }
        .stButton button {
            background-color: #d62976;
            color: white;
            border: none;
            border-radius: 8px;
            padding: 10px 20px;
            font-size: 16px;
            font-weight: bold;
            cursor: pointer;
        }
        .stButton button:hover {
            background-color: #fa7e1e;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )




# Helper function to zip the files
def zip_files(file_paths, zip_name):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for file in file_paths:
            zip_file.write(file, os.path.basename(file))
    zip_buffer.seek(0)
    return zip_buffer
# Helper function to download Reels asynchronously
async def download_reel_async(reel, folder_path):
    await asyncio.to_thread(L.download_post, reel, target=folder_path)
# Function to download Reels
async def download_reels(username: str):
    try:
        st.info(f"Fetching Reels for {username}...")

        # Get profile object
        profile = instaloader.Profile.from_username(L.context, username)

        # Create a folder for reels
        folder_path = f"{username}_reels"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Fetch the Reels from the profile
        reels = profile.get_reels()  # Fetches all Reels posts of the profile
        reel_files = []

        # Create tasks for concurrent downloading of Reels media
        tasks = []
        for reel in reels:
            if reel.is_video:  # Make sure only videos are downloaded (Reels are videos)
                tasks.append(download_reel_async(reel, folder_path))

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Check for valid media files (only mp4)
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if file_path.endswith('mp4'):
                reel_files.append(file_path)

        if not reel_files:
            st.warning("No Reels found for this user.")
            return []

        return reel_files

    except Exception as e:
        st.error(f"An error occurred while fetching Reels: {e}")
        return []

# Helper function to download posts asynchronously
async def download_post_async(post, folder_path):
    await asyncio.to_thread(L.download_post, post, target=folder_path)

# Function to download user posts with date filtering
async def download_user_posts(username: str, since_date: datetime = None, until_date: datetime = None):
    try:
        st.info(f"Fetching posts from {username}...")

        # Get profile object
        profile = instaloader.Profile.from_username(L.context, username)

        # Get total number of posts
        total_posts = profile.mediacount
        if total_posts > 400:
            st.warning(f"Post limit exceeded! This user has {total_posts} posts. Maximum allowed is 400.")
            return []

        # Create a folder to store the downloaded posts
        folder_path = f"{username}_posts"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Fetch posts
        posts = list(profile.get_posts())

        # Filter posts based on date range
        if since_date:
            posts = [post for post in posts if post.date >= since_date]
        if until_date:
            posts = [post for post in posts if post.date <= until_date]

        # Limit to the first 400 posts after filtering
        posts = posts[:400]
        post_files = []

        # Create tasks for concurrent downloading
        tasks = []
        for post in posts:
            tasks.append(download_post_async(post, folder_path))

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Check for valid media files (images/videos)
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if file_path.endswith(('jpg', 'jpeg', 'png', 'mp4')):
                post_files.append(file_path)

        if not post_files:
            st.warning("No posts found for this user.")
            return []

        return post_files

    except Exception as e:
        st.error(f"An error occurred while fetching posts: {e}")

# Helper function to download stories asynchronously
async def download_story_async(item, folder_path):
    await asyncio.to_thread(L.download_storyitem, item, target=folder_path)

# Function to download user stories
async def download_user_stories(username: str):
    try:
        st.info(f"Fetching stories from {username}...")

        # Get profile object
        profile = instaloader.Profile.from_username(L.context, username)

        # Fetch user ID from the profile
        profile_id = profile.userid
        
        # Create a folder for stories
        folder_path = f"{username}_stories"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Download stories (instaloader's L.get_stories() function needs the profile ID)
        stories = L.get_stories(userids=[profile_id])
        story_files = []

        # Create tasks for concurrent downloading of story items
        tasks = []
        for story in stories:
            for item in story.get_items():
                tasks.append(download_story_async(item, folder_path))

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Check for valid media files (images/videos)
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if file_path.endswith(('jpg', 'jpeg', 'png', 'mp4')):
                story_files.append(file_path)

        if not story_files:
            st.warning("No stories found for this user.")
            return []

        return story_files

    except Exception as e:
        st.error(f"An error occurred while fetching stories: {e}")

# Helper function to download highlight media asynchronously
async def download_highlight_async(item, folder_path):
    await asyncio.to_thread(L.download_storyitem, item, target=folder_path)

# Function to download highlights
async def download_highlights(username: str):
    try:
        st.info(f"Fetching highlights for {username}...")

        # Get profile object
        profile = instaloader.Profile.from_username(L.context, username)

        # Create a folder for highlights
        folder_path = f"{username}_highlights"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Fetch the highlight containers
        highlights = L.get_highlights(profile)  # Correct method to fetch highlights
        highlight_files = []

        # Create tasks for concurrent downloading of highlight media
        tasks = []
        for highlight in highlights:
            for item in highlight.get_items():
                tasks.append(download_highlight_async(item, folder_path))

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Check for valid media files (images/videos)
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if file_path.endswith(('jpg', 'jpeg', 'png', 'mp4')):
                highlight_files.append(file_path)

        if not highlight_files:
            st.warning("No highlights found for this user.")
            return []

        return highlight_files

    except Exception as e:
        st.error(f"An error occurred while fetching highlights: {e}")


# Helper function to download tagged media asynchronously
async def download_tagged_async(post, folder_path):
    await asyncio.to_thread(L.download_post, post, target=folder_path)

# Function to download tagged media
async def download_tagged_media(username: str):
    try:
        st.info(f"Fetching tagged media for {username}...")

        # Get profile object
        profile = instaloader.Profile.from_username(L.context, username)

        # Get total number of posts
        total_posts = profile.mediacount
        if total_posts > 400:
            st.warning(f"Post limit exceeded! This user has {total_posts} posts. Maximum allowed is 400. Skipping tagged media fetch.")
            return []

        # Fetch tagged media
        tagged_posts = list(profile.get_tagged_posts())
        tagged_files = []

        # Create tasks for concurrent downloading of tagged media
        tasks = []
        for post in tagged_posts:
            tasks.append(download_tagged_async(post, f"{username}_tagged"))

        # Wait for all tasks to complete
        await asyncio.gather(*tasks)

        # Check for valid media files (images/videos)
        folder_path = f"{username}_tagged"
        for filename in os.listdir(folder_path):
            file_path = os.path.join(folder_path, filename)
            if file_path.endswith(('jpg', 'jpeg', 'png', 'mp4')):
                tagged_files.append(file_path)

        if not tagged_files:
            st.warning("No tagged media found for this user.")
            return []

        return tagged_files

    except Exception as e:
        st.error(f"An error occurred while fetching tagged media: {e}")
# Helper function to display media in a grid layout
def display_media_in_grid(media_files):
    cols = st.columns(3)  # Adjust this number to change the number of columns
    col_idx = 0

    # Display media as a grid
    for media_file in media_files:
        with cols[col_idx]:
            if media_file.endswith(('jpg', 'jpeg', 'png')):
                st.image(media_file, caption=os.path.basename(media_file), width=300)  # Specify width here
            elif media_file.endswith('mp4'):
                st.video(media_file)  # Use default behavior for video

        col_idx += 1
        if col_idx == 3:  # Reset column index to 0 after every 3 images (for the grid)
            col_idx = 0

# Streamlit UI
def instagram_page():
    reel_files = None    
    # Add custom CSS and other Streamlit UI components as needed

    # Input field for Instagram Username with a unique key
    username = st.text_input("Enter Instagram Username", placeholder="e.g., natgeo", key="username_input")

    # Date filter inputs
    since_input = st.date_input("Since", min_value=datetime(2010, 1, 1), max_value=datetime.today(), value=datetime(2015, 1, 1))
    until_input = st.date_input("Until", min_value=datetime(2010, 1, 1), max_value=datetime.today(), value=datetime.today())

    # Convert the date inputs to datetime objects
    since_date = datetime.combine(since_input, datetime.min.time())
    until_date = datetime.combine(until_input, datetime.min.time())

    # Add tabs for Posts, Stories, Tagged Media, and Highlights
    tabs = st.tabs(["📷 Posts", "📖 Stories", "🏷️ Tagged Media", "📚 Highlights", "🎥 Reels"])

    # Variables to store media files
    post_files, story_files, tagged_files, highlight_files = [], [], [], []

    # Posts Tab
    with tabs[0]:
        if username:
            if st.button("📥 Fetch Posts"):
                post_files = asyncio.run(download_user_posts(username, since_date, until_date))
                if post_files:
                    display_media_in_grid(post_files)

            if post_files:
                zip_buffer = zip_files(post_files, f"{username}_posts_media")
                st.download_button(
                    label="💾 Download All Posts Media",
                    data=zip_buffer,
                    file_name=f"{username}_posts_media.zip",
                    mime="application/zip"
                )

    # Stories Tab
    with tabs[1]:
        if username:
            if st.button("📥 Fetch Stories"):
                story_files = asyncio.run(download_user_stories(username))
                if story_files:
                    display_media_in_grid(story_files)

            if story_files:
                zip_buffer = zip_files(story_files, f"{username}_stories_media")
                st.download_button(
                    label="💾 Download All Stories Media",
                    data=zip_buffer,
                    file_name=f"{username}_stories_media.zip",
                    mime="application/zip"
                )

    # Tagged Media Tab
    with tabs[2]:
        if username:
            if st.button("📥 Fetch Tagged Media"):
                tagged_files = asyncio.run(download_tagged_media(username))
                if tagged_files:
                    display_media_in_grid(tagged_files)

            if tagged_files:
                zip_buffer = zip_files(tagged_files, f"{username}_tagged_media")
                st.download_button(
                    label="💾 Download All Tagged Media",
                    data=zip_buffer,
                    file_name=f"{username}_tagged_media.zip",
                    mime="application/zip"
                )

    # Highlights Tab
    with tabs[3]:
        if username:
            if st.button("📥 Fetch Highlights"):
                highlight_files = asyncio.run(download_highlights(username))
                if highlight_files:
                    display_media_in_grid(highlight_files)

            if highlight_files:
                zip_buffer = zip_files(highlight_files, f"{username}_highlights_media")
                st.download_button(
                    label="💾 Download All Highlights Media",
                    data=zip_buffer,
                    file_name=f"{username}_highlights_media.zip",
                    mime="application/zip"
                )
    # Highlights Tab
    with tabs[4]:
        if username:
            if st.button("📥 Fetch Reels"):
                reel_files = asyncio.run(download_reels(username))
                if reel_files:
                    display_media_in_grid(reel_files)

            # Only allow this block to run if reel_files is successfully assigned
            if reel_files:
                zip_buffer = zip_files(reel_files, f"{username}_reels_media")
                st.download_button(
                    label="💾 Download All Reels Media",
                    data=zip_buffer,
                    file_name=f"{username}_reels_media.zip",
                    mime="application/zip"
                )
    if not username:
        st.warning("Please enter a valid Instagram username.")

        
async def get_json(session, username):
    base_url = "https://story.snapchat.com/@"
    headers = {'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:94.0) Gecko/20100101 Firefox/103.0.2'}
    mix = base_url + username
    print(f"[DEBUG] Fetching URL: {mix}")

    async with session.get(mix, headers=headers) as response:
        if response.status == 404:
            return None
        elif not response.ok:
            return None

        content = await response.text()
        print(f"[DEBUG] HTML content fetched for {username}.")
        soup = BeautifulSoup(content, "html.parser")
        snap_data = soup.find(id="__NEXT_DATA__").string.strip()
        data = json.loads(snap_data)
        print(f"[DEBUG] Parsed JSON data for {username}.")
        return data

# Function to download media from Snapchat
async def download_media(json_dict, session):
    media_files = []
    try:
        for snap in json_dict["props"]["pageProps"]["story"]["snapList"]:
            file_url = snap["snapUrls"]["mediaUrl"]
            print(f"[DEBUG] Found file URL: {file_url}")

            if not file_url:
                continue

            file_type = None
            file_name = None

            # Ensure the media directory exists
            media_dir = os.getcwd()
            os.makedirs(media_dir, exist_ok=True)

            async with session.get(file_url, headers={'User-Agent': 'Mozilla/5.0'}) as response:
                print(f"[DEBUG] Downloading media from {file_url}")

                if response.status == 200:
                    file_type = response.headers.get('Content-Type', '')
                    file_name = response.headers.get('ETag', '').replace('"', '')

                    if "image" in file_type:
                        file_name += ".jpeg"
                        file_path = os.path.join(media_dir, file_name)

                        # Delete the existing file if it exists
                        if os.path.isfile(file_path):
                            os.remove(file_path)

                        # Download the image
                        async with aiofiles.open(file_path, 'wb') as f:
                            while True:
                                chunk = await response.content.read(1024)
                                if not chunk:
                                    break
                                await f.write(chunk)

                        media_files.append(file_path)
                        print(f"[DEBUG] Image downloaded and added: {file_name}")

                    elif "video" in file_type:
                        file_name += ".mp4"
                        file_path = os.path.join(media_dir, file_name)

                        # Delete the existing file if it exists
                        if os.path.isfile(file_path):
                            os.remove(file_path)

                        # Download the video
                        async with aiofiles.open(file_path, 'wb') as f:
                            while True:
                                chunk = await response.content.read(1024)
                                if not chunk:
                                    break
                                await f.write(chunk)

                        media_files.append(file_path)
                        print(f"[DEBUG] Video downloaded and added: {file_name}")
                else:
                    print("[DEBUG] Failed to download media.")
    except KeyError:
        print("[DEBUG] No stories found.")
    except Exception as e:
        print(f"[ERROR] An unexpected error occurred: {e}")

    return media_files

# Function to zip all media files
def zip_media(media_files, username):
    # Set the filename to TTK_{username}_Snaps.zip
    zip_filename = f"TTK_{username}_Snaps.zip"
    
    with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for media_file in media_files:
            zipf.write(media_file, os.path.basename(media_file))
            print(f"[DEBUG] Added {media_file} to zip.")
    
    return zip_filename


# Streamlit page to display Snapchat media
def snapchat_page():
    # Add custom CSS for Snapchat font (you can adjust this to any Snapchat-like font you like)
    add_custom_css()

    # Add Snapchat Logo at the top
    snapchat_logo_url = "https://postcron.com/en/blog/wp-content/uploads/2017/10/snapchat-logo.png"  # Snapchat logo URL
    st.image(snapchat_logo_url, width=200, caption="Snapchat")  # Adjust width and caption as needed

    # Snapchat title with a custom font (you can adjust the font style in the CSS)
    st.markdown("<h1 style='text-align: center; font-family: \"Snapchat\", sans-serif;'>👻 Snapchat Media Viewer</h1>", unsafe_allow_html=True)

    st.markdown(
        "<p style='text-align: center; font-family: \"Snapchat\", sans-serif;'>View and download Snapchat media effortlessly!</p>",
        unsafe_allow_html=True,
    )

    # Input field for Snapchat Username
    username = st.text_input("Enter Snapchat Username:")

    if st.button("Fetch Snaps"):
        if username:
            # Display a message indicating fetching snaps for the username
            st.markdown(f"<p style='font-family: \"Snapchat\", sans-serif; color: gray;'>Fetching snaps from <strong>{username}</strong>...</p>", unsafe_allow_html=True)

            async def display_media():
                async with aiohttp.ClientSession() as session:
                    json_data = await get_json(session, username)
                    if json_data:
                        media_files = await download_media(json_data, session)
                        if media_files:
                            # Display the media in a grid format
                            cols = st.columns(3)  # Adjust this number to control how many images/videos per row
                            for i, media_file in enumerate(media_files):
                                with cols[i % 3]:  # Ensure we cycle through columns
                                    if media_file.endswith(".jpeg"):
                                        st.image(media_file, caption="Image", use_container_width=True)
                                    elif media_file.endswith(".mp4"):
                                        st.write("Video")  # Display the caption
                                        st.video(media_file, format="video/mp4")
                            # Add a download button for the zip
                            zip_filename = zip_media(media_files, username)
                            with open(zip_filename, "rb") as f:
                                st.download_button(
                                    label="Download All Snaps",
                                    data=f,
                                    file_name=zip_filename,
                                    mime="application/zip"
                                )
                        else:
                            st.warning("No media found.")
                    else:
                        st.error(f"No stories found for username: {username}")

            asyncio.run(display_media())
        else:
            st.error("Please enter a valid Snapchat username.")


# Custom CSS for Snapchat font
def add_custom_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Work+Sans&display=swap');  /* Using a Snapchat-like font */
    body {
        font-family: 'Work Sans', sans-serif;
    }
    </style>
    """, unsafe_allow_html=True)
# Main Function with Navigation
def main():
    st.set_page_config(
        page_title="Multi-Downloader",
        page_icon=":globe_with_meridians:",
        layout="wide",
    )

    # Top menu bar with tabs
    tabs = st.tabs([
        "VSCO Downloader", 
        "Snapchat Downloader", 
        "TikTok Downloader"
    ])

    with tabs[0]:
        vsco_page()  # Ensure the vsco_page() function is defined elsewhere

    with tabs[1]:
        snapchat_page()  # Ensure the snapchat_page() function is defined elsewhere

    with tabs[2]:
        tiktok_page()  # TikTok downloader page added
    


if __name__ == "__main__":
    main()
