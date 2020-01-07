import streamlit as st
import urllib, os
import requests
import json
import pandas as pd
import time
from typing import Union, Optional

from pathlib import Path

# Download a single file and make its content available as a string.
@st.cache(show_spinner=False)
def get_file_content_as_string(path):
    if Path(path).exists:
        return open(path).read()
    url = (
        "https://raw.githubusercontent.com/cwerner/ldndctools/i3_streamlit-ui/ldndctools/md/instructions.md"
        + path
    )
    response = urllib.request.urlopen(url)
    return response.read().decode("utf-8")


def main():
    readme_text = st.markdown(get_file_content_as_string("instructions.md"))

    # Once we have the dependencies, add a selector for the app mode on the sidebar.
    st.sidebar.title("What to do")
    app_mode = st.sidebar.selectbox(
        "Choose the app mode",
        ["Show instructions", "Run the app", "Show the source code"],
    )
    if app_mode == "Show instructions":
        st.sidebar.success('To continue select "Run the app".')
    elif app_mode == "Show the source code":
        readme_text.empty()
        st.code(get_file_content_as_string("app.py"))
    elif app_mode == "Run the app":
        readme_text.empty()
        run_the_app()


# This is the main app app itself, which appears when the user selects "Run the app".
def run_the_app():
    st.header("General")
    st.write("👈 Please select the region mode")

    # select endpoint
    st.sidebar.subheader("Mode")
    modes = ["site file", "high-res", "medium-res", "low-res"]
    mode = st.sidebar.radio("Select mode", modes, 0, key="model_select")

    if mode == "site file":
        uploaded_file = st.file_uploader("csv_file", type=["csv", "tsv", "txt"])

        if uploaded_file:
            df = pd.read_csv(uploaded_file)
            st.write(df)


if __name__ == "__main__":
    main()
