import sys
import os
import logging
from logging import getLogger

from flask import Flask, render_template, request, jsonify, session
from persona_interface.crs_handler import CRSResponseGenerator
from persona_interface.wikipedia_api import wikipedia_search_process

# Suppress watchdog messages
getLogger('watchdog.observers.inotify_buffer').setLevel(logging.WARNING)

app = Flask(__name__)
app.secret_key = 'dev'  # Required for session management

# Initialize the CRSResponseGenerator
response_generator = CRSResponseGenerator("kbrd_redial")

@app.route('/')
def index():
    # Initialize an empty dialogue history when a new session starts
    session['dialogue_history'] = []
    session['all_recommendations'] = []
    return render_template('index.html')

@app.route('/chat', methods=['POST'])
def chat():
    message = request.json['message']
    
    # Retrieve the dialogue history and recommendations from the session
    dialogue_history = session.get('dialogue_history', [])
    all_recommendations = session.get('all_recommendations', [])
    
    # Calculate the current turn number (starting from 1)
    # Turn number is counted for each utterance, not pair
    current_turn = len(dialogue_history) + 1
    
    # Generate a response using the CRSResponseGenerator
    response, top_recommendations_names = response_generator.generate_response(dialogue_history, message)
    
    # Update the dialogue history
    dialogue_history.append(message)
    dialogue_history.append(response)
    session['dialogue_history'] = dialogue_history
    
    # The next turn will be for the system response
    system_turn = current_turn + 1
    
    # Add new recommendations to the list of all recommendations
    new_recommendations = []
    for item in top_recommendations_names:
        wiki_results = wikipedia_search_process(item)
        new_recommendations.append({
            'turn': system_turn,
            'item': item,
            'wiki_title': wiki_results['title'] if wiki_results else None,
            'wiki_url': wiki_results['url'] if wiki_results else None
        })
    all_recommendations.extend(new_recommendations)
    session['all_recommendations'] = all_recommendations
    
    return jsonify({
        'response': response,
        'recommendations': all_recommendations
    })

if __name__ == '__main__':
    app.run(debug=True)