import streamlit as st
from vsco_downloader import download as vsco_download
import instaloader
import requests
import os
import shutil
import asyncio
import instaloader
from zipfile import ZipFile
import time
import io
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor
import json
import requests
from bs4 import BeautifulSoup
import aiohttp
import aiofiles

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

# Main page content
def vsco_page():
    st.title("VSCO Downloader")
    
    # Add VSCO logo at the top
    vsco_logo_url = "https://th.bing.com/th/id/OIP.E36Cq-gP4UrriuCW0kxRRQHaFK?rs=1&pid=ImgDetMain"  # URL for VSCO logo
    st.image(vsco_logo_url, width=200)  # Display logo with specified width

    general_description = """
    VSCO Downloader is a simple script to extract raw image and video paths from [VSCO](https://www.vsco.co/) posts.
    """
    st.markdown(general_description)

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
    
    # Sidebar with social link and description
    st.sidebar.title("Follow Us")
    st.sidebar.markdown("[Telegram](https://t.me/TTKgroups)")

    # Informative description in the sidebar
    st.sidebar.subheader("About This Site")
    st.sidebar.markdown("""
    This website is created by **TTKgroups**. You can use this tool to download media from various platforms like **VSCO**, **Instagram**, **Snapchat**, and more coming soon!

    Stay tuned for additional features and support for more platforms!
    """)

# Initialize instaloader object
L = instaloader.Instaloader()

# Define the session file path
session_file_path = "session-baal123487"  # Update to match your actual session file path

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

# Helper function to download posts asynchronously
async def download_post_async(post, folder_path):
    await asyncio.to_thread(L.download_post, post, target=folder_path)

# Function to download user posts
async def download_user_posts(username: str):
    try:
        st.info(f"Fetching posts from {username}...")

        # Get profile object
        profile = instaloader.Profile.from_username(L.context, username)

        # Create a folder to store the downloaded posts
        folder_path = f"{username}_posts"
        if not os.path.exists(folder_path):
            os.makedirs(folder_path)

        # Fetch posts
        posts = list(profile.get_posts())[:400]  # Limit to 400 posts for efficiency
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

# Helper function to download tagged media asynchronously
async def download_tagged_async(post, folder_path):
    await asyncio.to_thread(L.download_post, post, target=folder_path)

# Function to download tagged media
async def download_tagged_media(username: str):
    try:
        st.info(f"Fetching tagged media for {username}...")

        # Get profile object
        profile = instaloader.Profile.from_username(L.context, username)

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

# Instagram Page with Tabs for Posts, Stories, and Tagged Media
def instagram_page():
    # Add custom CSS for Instagram font
    add_custom_css()

    # Add Instagram Logo at the top
    insta_logo_url = "https://upload.wikimedia.org/wikipedia/commons/9/95/Instagram_logo_2022.svg"
    st.image(insta_logo_url, width=200, caption="Instagram")

    st.markdown("<h1 style='text-align: center; font-family: \"Instagram Sans\", sans-serif;'>📸 Instagram Downloader</h1>", unsafe_allow_html=True)

    st.markdown("<p style='text-align: center; font-family: \"Instagram Sans\", sans-serif;'>Download and enjoy Instagram media effortlessly!</p>", unsafe_allow_html=True)

    # Input field for Instagram Username
    username = st.text_input("Enter Instagram Username", placeholder="e.g., natgeo", key="username_input")

    # Add tabs for Posts, Stories, and Tagged Media
    tabs = st.tabs(["📷 Posts", "📖 Stories", "🏷️ Tagged Media"])

    # Variables to store media files
    post_files, story_files, tagged_files = [], [], []

    # Posts Tab
    with tabs[0]:
        if username:
            if st.button("📥 Fetch Posts"):
                post_files = asyncio.run(download_user_posts(username))
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
                                        st.video(media_file, caption="Video", format="video/mp4")
                            # Add a download button for the zip
                            zip_filename = zip_media(media_files)
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
    tabs = st.tabs(["VSCO Downloader", "Instagram Downloader", "Snapchat Downloader"])

    with tabs[0]:
        vsco_page()

    with tabs[1]:
        instagram_page()
    with tabs[2]:
        snapchat_page()

if __name__ == "__main__":
    main()
