"""This contains the codes which are used for Prolific dataset collection.

1. Show terms and conditions
  - The worker will not be compensated if they do not complete the conversation for both two systems.
  - The interface might not work on some browsers (e.g., Safari). Please close the task as soon as you found your browser is not compatible; we cannot compensate any incomplete tasks.
  - Sometimes, the system response takes ~1 min. Please be patient and do not submit your message multiple times.
  - Please at least have 5 turns of conversation for each system.
  - Provide a feedbakc on why you choose the system you did.
  - Then show the button "I accept the terms and conditions:"
2. When user presses "Frustrated" or "Satisfied", without having a conversation of specified 5 turns, the app will show them a pop-up that says "Please have at least N turns of conversation before finishing the conversation"
3. When user finishes giving the feedback, the app will show the completion code "XXXXX" to the user, then finish the conversation. (never move to the new session)
"""

import streamlit as st
import json
from datetime import datetime
import asyncio
from utils import upload_feedback_to_hf
from streamlit import secrets

N_USER_TURNS_REQUIRED = 0  # or whatever number you've set

async def write_prolific_id(prolific_id: str):
    data = {
        "id": datetime.now().isoformat(),
        "user_id": st.session_state["user_id"],
        "prolific_id": prolific_id,
        "timestamp": datetime.now().isoformat()
    }
    await upload_feedback_to_hf(data, csv_filename="prolific_ids.csv")

def show_terms_and_conditions() -> bool:
    print('DEBUG: show_terms_and_conditions called')
    terms_container = st.empty()
    
    with terms_container.container():
        terms = """
        Terms and Conditions:
        - IMPORTANT: This task is incompatible with certain browsers (e.g., Safari) and settings.
        If you are unable to access the page or send messages, it indicates that your settings are not compatible with this task.
        Please close the task immediately upon discovering that your browser is incompatible, as we are unable to compensate for any incomplete tasks.
        - Be aware that system responses can take up to approximately one minute. Please be patient and refrain from submitting your message multiple times.
        """
        
        st.markdown(terms)
        
        prolific_id = st.text_input("Enter your Prolific ID:")
        
        if st.button("I accept the terms and conditions", disabled=not prolific_id):
            asyncio.run(write_prolific_id(prolific_id))
            terms_container.empty()
            return True
    return False

def check_user_num_turns(messages):
    print('DEBUG: check_user_num_turns called')
    user_turns = sum(1 for message in messages if message["role"] == "user")
    return user_turns >= N_USER_TURNS_REQUIRED


def show_completion_code(placeholder):
    print('DEBUG: show_completion_code called')
    completion_code = secrets.prolific.prolific_completion_code
    with placeholder.container():
        st.markdown("# Thank you for participating!")
        st.markdown("## Your completion code is:")
        st.markdown(f"### {completion_code}")
        st.markdown("Please copy this code and submit it on Prolific.")
    print('DEBUG: Completion message should be displayed')