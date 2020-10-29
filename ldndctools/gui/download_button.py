import uuid
import re


# inspired by: https://gist.github.com/chad-m/6be98ed6cf1c4f17d09b7f6e5ca2978f
def download_button(
    filename: str, uri: str, button_text: str = "Click to download dataset"
) -> str:
    button_uuid = str(uuid.uuid4()).replace("-", "")
    button_id = re.sub("\d+", "", button_uuid)

    custom_css = f""" 
        <style>
            #{button_id} {{
                background-color: rgb(255, 255, 255);
                color: rgb(38, 39, 48);
                padding: 0.25em 0.38em;
                position: relative;
                text-decoration: none;
                border-radius: 4px;
                border-width: 1px;
                border-style: solid;
                border-color: rgb(230, 234, 241);
                border-image: initial;
    
            }} 
            #{button_id}:hover {{
                border-color: rgb(246, 51, 102);
                color: rgb(246, 51, 102);
            }}
            #{button_id}:active {{
                box-shadow: none;
                background-color: rgb(246, 51, 102);
                color: white;
                }}
        </style> """

    return (
        f'{custom_css} <a download="{filename}" id="{button_id}" href="{uri}">'
        f"{button_text}</a><br></br>"
    )
