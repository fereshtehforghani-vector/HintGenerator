""" 
This file is the entry point for the Cloud Function. It receives the incoming HTTPS request. Overall, it processes the file (if there is one), constructs the prompt, calls the model API, saves the conversation turn to the database, and sends the model's response back to the user interface.
"""

import functions_framework # Library made by google specifically for cloud functions - it handles HTTP, starting the web server that listens to requests on port 8080 (which is what GCP expects)
import json
from file_handler import process_file
from model import call_model
from store_conversation import save_conversation_turn


# This 'functions_framework' decorator registers the 'main' function as the HTTP handler - telling the web server when an HTTPS request comes in, call this function and pass in the 'request' object (user query + file). 
@functions_framework.http 
def main(request):
    # This function is triggered every time an HTTPS request hits the Cloud Function URL.
    # The 'request' object contains everything the user sent: the query text, file_type, and file_data.

    if request.method == "OPTIONS": # This whole conditional 'OPTIONS' block is checking if the Cloud Function's domain is allowed to receive requests from x domain
        headers = {
            # TODO - when real frontend is up, change '*' to actual_frontend_domain.com
            "Access-Control-Allow-Origin": "*", # Allow requests from ANY domain (local Gradio, established front end interface, etc.)
            "Access-Control-Allow-Methods": "POST", # Only allow POST requests (we're receiving data)
            "Access-Control-Allow-Headers": "Content-Type, Authorization", # Allow the Content-Type header which tells us the data is JSON (because the POST request is JSON)
        }
        return ("", 204, headers) 

    headers = {"Access-Control-Allow-Origin": "*"} 

    # After the above check is passed, actually pass in the incoming POST request 
    try:
        request_json = request.get_json(silent=True) # Converts the incoming JSON request into a Python dict

        if request_json:
            # Pull query and conversation_id from JSON body
            query = request_json.get("query", "")
            conversation_id = request_json.get("conversation_id", None)
            
        # This block will be used when the POST request is not in JSON format (which is the case when a file is attached, because the request has to be 'multipart/form-data' to send the file, and in that case the query and conversation_id are sent as form data, not JSON)
        else:
            # Pull query and conversation_id from form data (used when a file is attached)
            query = request.form.get("query", "")
            conversation_id = request.form.get("conversation_id", None)

        if not query:
            return (json.dumps({"error": "No query provided"}), 400, headers)

        file_type, file_data, stored_file_url = process_file(request) # Pass in the incoming request so the file_handler.py file can inspect the uploaded file, store images in Cloud Storage, and return the processed file payload to use in the model call

        response = call_model(query, file_type, file_data) # Pass in the query, file_type, and file_data to the model.py file, which constructs the prompt and calls the model API
        
        save_conversation_turn(conversation_id, query, response, stored_file_url) # Save the conversation turn (user query, AI response, and any file URL) to the database

        return (json.dumps({"response": response, "conversation_id": conversation_id, "stored_file_url": stored_file_url}), 200, headers) # Sends the AI model's response back to the user interface

    except Exception as e:
        return (json.dumps({"error": str(e)}), 500, headers) # error block, which displays the error if anything crashes
