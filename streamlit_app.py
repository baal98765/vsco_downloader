#!/usr/bin/env python3

# VSCO Downloader GUI
# 2024 (c) Micha Johannes Birklbauer
# https://github.com/michabirklbauer/
# micha.birklbauer@gmail.com

"""
#####################################################
##                                                 ##
##            -- STREAMLIT MAIN APP --             ##
##                                                 ##
#####################################################
"""

import streamlit as st
from vsco_downloader import download as d

# main page content
def main_page():

    title = st.title("VSCO Downloader")

    general_description = \
    """
    VSCO Downloader is a simple script to extract raw image and video paths from [VSCO](https://www.vsco.co/) posts.
    """
    description = st.markdown(general_description)

    header_1 = st.subheader("Extract Post Media", divider = "rainbow")

    url_input = st.text_input("VSCO Post URLs (comma-separated):",
                             placeholder = "https://vsco.co/scarlettmccarthyy/media/673a69d397d0f92b0954ce43, https://vsco.co/user2/media/12345",
                             help = "Comma-separated list of VSCO post URLs from which media should be extracted.")

    l1, l2, center_button, r1, r2 = st.columns(5)

    with center_button:
        download = st.button("Download!", type = "primary", use_container_width = True)

    if download:
        # Split the input string by commas and process each URL
        urls = [url.strip() for url in url_input.split(',')]  # Split by comma and remove any extra spaces
        media_urls = []
        for url in urls:
            media_urls.extend(d(url, True, False))  # Fetch media URLs for each input URL
        header_2 = st.subheader("Extracted Post Media", divider = "rainbow")
        display_media_urls = st.markdown("\n".join([f"- Found media URL: [{media_url}]({media_url})" for media_url in media_urls]))

# side bar and main page loader
def main():

    about_str = \
    """
    VSCO Downloader is a simple script to extract raw image and video paths from [VSCO](https://www.vsco.co/) posts.
    """

    st.set_page_config(page_title = "VSCO Downloader",
                       page_icon = ":camera:",
                       layout = "wide",
                       initial_sidebar_state = "expanded",
                       menu_items = {"Get Help": "https://github.com/michabirklbauer/vsco_downloader/discussions",
                                     "Report a bug": "https://github.com/michabirklbauer/vsco_downloader/issues",
                                     "About": about_str}
                       )

    title = st.sidebar.title("VSCO Downloader")

    div_1 = st.sidebar.subheader("", divider = "rainbow")

    logo = st.sidebar.image(".streamlit/ico/download-icon.png",
                            caption = "VSCO Downloader is a simple script to extract raw image and video paths from VSCO posts.")

    div_2 = st.sidebar.subheader("", divider = "rainbow")

    info_str = ""
    info_str += "- **Contact:**  \n  [TTKgroups](https://t.me/TTKgroups)\n"
    info = st.sidebar.markdown(info_str)

    main_page()

if __name__ == "__main__":

    main()
