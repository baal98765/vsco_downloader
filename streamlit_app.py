import streamlit as st
from vsco_downloader import download as vsco_download
import instaloader
import requests
import os
import shutil
import asyncio
import instaloader
from zipfile import ZipFile
import io
import re
import zipfile
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

# Asynchronous function to download a single post
async def async_download_post(post, folder_path):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, lambda: L.download_post(post, target=folder_path))

# Function to create a zip file
def create_zip_file(folder_path, zip_name):
    with ZipFile(zip_name, 'w') as zipf:
        for root, _, files in os.walk(folder_path):
            for file in files:
                file_path = os.path.join(root, file)
                zipf.write(file_path, os.path.relpath(file_path, folder_path))
    return zip_name

# Streamlit Instagram Tab
def instagram_page():
    # Add custom CSS for Instagram font (you can adjust this to any Instagram-like font you like)
    add_custom_css()
    
    # Add Instagram Logo at the top
    insta_logo_url = "https://upload.wikimedia.org/wikipedia/commons/9/95/Instagram_logo_2022.svg"  # Instagram logo URL
    st.image(insta_logo_url, width=200, caption="Instagram")  # Adjust width and caption as needed
    
    # Instagram title with a custom font (you can adjust the font style in the CSS)
    st.markdown("<h1 style='text-align: center; font-family: \"Instagram Sans\", sans-serif;'>📸 Instagram Downloader</h1>", unsafe_allow_html=True)
    
    st.markdown(
        "<p style='text-align: center; font-family: \"Instagram Sans\", sans-serif;'>Download and enjoy Instagram posts effortlessly!</p>",
        unsafe_allow_html=True,
    )
    
    # Input field for Instagram Username
    username = st.text_input(
        "Enter Instagram Username",
        placeholder="e.g., natgeo",
        help="Type the username of the Instagram profile you want to download posts from.",
    )

    if st.button("📥 Download Posts"):
        if username:
            st.info(f"Fetching posts for {username}... Please wait a moment.")
            folder_path = f"{username}"
            os.makedirs(folder_path, exist_ok=True)

            try:
                # Load the profile
                profile = instaloader.Profile.from_username(L.context, username)
                total_posts = profile.mediacount

                if total_posts > 400:
                    st.warning("⚠️ Post limit exceeded. Please select an account with fewer than 400 posts.")
                    return

                posts = list(profile.get_posts())[:400]

                # Async download posts
                async def download_posts():
                    tasks = [async_download_post(post, folder_path) for post in posts]
                    await asyncio.gather(*tasks)

                asyncio.run(download_posts())

                # Display media in a grid layout
                media_files = [
                    os.path.join(folder_path, f) for f in os.listdir(folder_path)
                    if f.endswith(('jpg', 'jpeg', 'png', 'mp4'))
                ]

                # Create a number of columns based on the media count
                cols = st.columns(3)  # Adjust 3 to the number of columns you want
                col_idx = 0

                for media_file in media_files:
                    with cols[col_idx]:
                        if media_file.endswith(('jpg', 'jpeg', 'png')):
                            st.image(media_file, caption=os.path.basename(media_file), width=300)  # Specify width here
                        elif media_file.endswith('mp4'):
                            st.video(media_file)  # Use default behavior for video

                    col_idx += 1
                    if col_idx == 3:  # Reset column index to 0 after every 3 images
                        col_idx = 0

                # "Download All" button
                zip_name = f"{username}_all_media.zip"
                zip_file_path = create_zip_file(folder_path, zip_name)
                with open(zip_file_path, "rb") as f:
                    st.download_button(
                        label="💾 Download All Media",
                        data=f,
                        file_name=os.path.basename(zip_file_path),
                        mime="application/zip"
                    )

                # Clean up
                os.remove(zip_file_path)
                shutil.rmtree(folder_path)
                st.success(f"🎉 All posts from {username} downloaded successfully!")
            except Exception as e:
                st.error(f"❌ An error occurred: {e}")
        else:
            st.warning("⚠️ Please enter a username.")


# Function to fetch JSON data for a Snapchat username
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
