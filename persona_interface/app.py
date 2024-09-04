import sys
import os
import logging
from logging import getLogger
import json
import uuid
from flask import Flask, render_template, request, jsonify, session
from persona_interface.crs_handler import CRSResponseGenerator
from persona_interface.wikipedia_api import wikipedia_search_process
from persona_interface.persona import get_persona_data, batch_call
import time
from datetime import datetime, timedelta

# Suppress watchdog messages
getLogger('watchdog.observers.inotify_buffer').setLevel(logging.WARNING)

app = Flask(__name__)
app.secret_key = 'dev'  # Required for session management

# Initialize the CRSResponseGenerator
response_generator = CRSResponseGenerator("kbrd_redial")

# New: In-memory storage for session data (replace with database in production)
session_storage = {}

# New: Function to update last accessed time for a session
def update_session_access_time(session_id):
    if session_id in session_storage:
        session_storage[session_id]['last_accessed'] = time.time()

# New: Cleanup function to remove old session data
def cleanup_old_sessions(max_age_minutes=30):
    current_time = time.time()
    sessions_to_remove = []
    
    for session_id, session_data in session_storage.items():
        last_accessed = session_data.get('last_accessed', 0)
        if current_time - last_accessed > max_age_minutes * 60:
            sessions_to_remove.append(session_id)
    
    for session_id in sessions_to_remove:
        del session_storage[session_id]
    
    print(f"Cleaned up {len(sessions_to_remove)} old sessions.")

@app.route('/')
def index():
    # Generate a unique session ID and store it in the session cookie
    session_id = str(uuid.uuid4())
    session['session_id'] = session_id
    
    # Initialize empty dialogue history and recommendations for this session
    session_storage[session_id] = {
        'dialogue_history': [],
        'all_recommendations': [],
        'last_accessed': time.time()
    }
    
    # Run cleanup before creating a new session
    cleanup_old_sessions()
    
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    message = request.json['message']
    session_id = session.get('session_id')
    
    if not session_id or session_id not in session_storage:
        return jsonify({'error': 'Invalid session'}), 400
    
    # Update last accessed time for this session
    update_session_access_time(session_id)
    
    # Retrieve the dialogue history and recommendations from the session storage
    dialogue_history = session_storage[session_id]['dialogue_history']
    all_recommendations = session_storage[session_id]['all_recommendations']
    
    # Calculate the current turn number (starting from 1)
    # Turn number is counted for each utterance, not pair
    current_turn = len(dialogue_history) + 1
    
    # Generate a response using the CRSResponseGenerator
    response, top_recommendations_names = response_generator.generate_response(dialogue_history, message)
    
    # Update the dialogue history
    dialogue_history.append(message)
    dialogue_history.append(response)
    session_storage[session_id]['dialogue_history'] = dialogue_history
    
    # The next turn will be for the system response
    system_turn = current_turn + 1
    
    # Add new recommendations to the list of all recommendations
    new_recommendations = []
    for item in top_recommendations_names:
        wiki_results = wikipedia_search_process(item)
        wiki_text = wiki_results['full_text'] if wiki_results else "No text found for this item in Wikipedia."
        
        persona_list = get_persona_data(ind=0)
        batch_results = batch_call(persona_list, wiki_text)
        
        new_recommendations.append({
            'turn': system_turn,
            'item': item,
            'wiki_title': wiki_results['title'] if wiki_results else None,
            'wiki_url': wiki_results['url'] if wiki_results else None,
            'persona_analysis': batch_results
        })
    all_recommendations.extend(new_recommendations)
    session_storage[session_id]['all_recommendations'] = all_recommendations
    
    return jsonify({
        'response': response,
        'recommendations': all_recommendations
    })

@app.route('/persona')
def get_persona():
    persona_list = get_persona_data(ind=0)
    return jsonify(persona_list)

if __name__ == '__main__':
    app.run(debug=True)