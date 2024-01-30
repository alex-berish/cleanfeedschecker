import io
import openai
from openai import OpenAI

import streamlit as st
import pandas as pd
import os
import time
import tempfile
import requests
import csv
import json
from PIL import Image

def init():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "run" not in st.session_state:
        st.session_state.run = None

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None

def set_apikey():
    st.sidebar.header('Claire GPT 2.0')
    st.sidebar.markdown('Generate Cover Letters')
    st.sidebar.header('Configure')
    api_key = st.sidebar.text_input("Enter OpenAI API key (ask Alex)", type="password")

    return api_key

def config(client):
    my_assistants = client.beta.assistants.list(
        order="desc",
        limit="20",
    )
    assistants = my_assistants.data
    assistants_dict = {}
    for assistant in assistants:
        assistants_dict[assistant.name] = assistant.id
    print(assistants_dict)
    assistant_option = st.sidebar.selectbox("Select Assistant", options=list(assistants_dict.keys()))
    return assistants_dict[assistant_option]

def chat_prompt(client, assistant_option):
    if prompt := st.chat_input("Enter a job description here"):
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages = st.session_state.messages.append(client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt,
        ))

        # Including both "code_interpreter" and "retrieval" tools
        st.session_state.run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=assistant_option,
            tools=[{"type": "code_interpreter"}, {"type": "retrieval"}],
        )
        
        print(st.session_state.run)
        pending = False
        while st.session_state.run.status != "completed":
            if not pending:
                with st.chat_message("assistant"):
                    st.markdown("Claire is thinking...")
                pending = True
            time.sleep(3)
            st.session_state.run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=st.session_state.run.id,
            )
            
        if st.session_state.run.status == "completed": 
            st.empty()
            chat_display(client)


def chat_display(client):
    st.session_state.messages = client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id
    ).data

    for message in reversed(st.session_state.messages):
        if message.role in ["user", "assistant"]:
            with st.chat_message(message.role):
                for content in message.content:
                    if content.type == "text":
                        st.markdown(content.text.value)
                    elif content.type == "image_file":
                        image_file = content.image_file.file_id
                        image_data = client.files.content(image_file)
                        image_data = image_data.read()
                        #save image to temp file
                        temp_file = tempfile.NamedTemporaryFile(delete=False)
                        temp_file.write(image_data)
                        temp_file.close()
                        #display image
                        image = Image.open(temp_file.name)
                        st.image(image)
                    else:
                        st.markdown(content)

def main():
    st.title('ClaireGPT 2.0 📈')
    st.caption('For all your cover letter needs...')
    st.divider()
    api_key = set_apikey()
    if api_key:
        client = OpenAI(api_key=api_key)
        assistant_option = config(client)
        if assistant_option:
            if st.session_state.thread_id is None:
                st.session_state.thread_id = client.beta.threads.create().id
                print(st.session_state.thread_id)
            chat_prompt(client, assistant_option)
    else:
        st.warning("Please enter your OpenAI API key")

if __name__ == '__main__':
    init()
    main() 
