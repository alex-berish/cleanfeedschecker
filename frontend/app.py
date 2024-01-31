import streamlit as st
import openai
from openai import OpenAI
import os
import time
import tempfile
from PIL import Image

def init():
    if "messages" not in st.session_state:
        st.session_state.messages = []

    if "run" not in st.session_state:
        st.session_state.run = None

    if "thread_id" not in st.session_state:
        st.session_state.thread_id = None

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
        # Send the user's message
        client.beta.threads.messages.create(
            thread_id=st.session_state.thread_id,
            role="user",
            content=prompt,
        )

        # Start a run to process the message
        st.session_state.run = client.beta.threads.runs.create(
            thread_id=st.session_state.thread_id,
            assistant_id=assistant_option,
            tools=[{"type": "code_interpreter"}, {"type": "retrieval"}],
        )
        
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

        # Display the chat after getting a response
        if st.session_state.run.status == "completed": 
            chat_display(client)




def chat_display(client):
    # Get the latest messages for the thread
    st.session_state.messages = client.beta.threads.messages.list(
        thread_id=st.session_state.thread_id
    ).data

    # Display messages
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
                        temp_file = tempfile.NamedTemporaryFile(delete=False)
                        temp_file.write(image_data)
                        temp_file.close()
                        image = Image.open(temp_file.name)
                        st.image(image)
                    else:
                        st.markdown(content)

def main():
    st.title('ClaireGPT 2.0 📈')
    st.caption('For all your cover letter needs...')
    st.divider()
    st.sidebar.title('ClaireGPT 2.0')

    # Fetch API key from st.secrets
    api_key = st.secrets["openai_api_key"]

    if api_key:
        client = OpenAI(api_key=api_key)
        assistant_option = config(client)
        if assistant_option:
            if st.session_state.thread_id is None:
                st.session_state.thread_id = client.beta.threads.create().id
                print(st.session_state.thread_id)
            chat_prompt(client, assistant_option)
    else:
        st.error("OpenAI API key not found in secrets. Please set it as a secret.")

if __name__ == '__main__':
    init()
    main()
