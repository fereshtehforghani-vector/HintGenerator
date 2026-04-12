from urllib import response

import gradio as gr
import requests
import subprocess
import os
import uuid

# TODO: Change my authentication token - ideally the user should be able to be authenticated from the front-end in their own way
def get_auth_token():
    return "eyJhbGciOiJSUzI1NiIsImtpZCI6ImIzZDk1Yjk1ZmE0OGQxODBiODVmZmU4MDgyZmNmYTIxNzRiMDQ2NjciLCJ0eXAiOiJKV1QifQ.eyJpc3MiOiJodHRwczovL2FjY291bnRzLmdvb2dsZS5jb20iLCJhenAiOiIzMjU1NTk0MDU1OS5hcHBzLmdvb2dsZXVzZXJjb250ZW50LmNvbSIsImF1ZCI6IjMyNTU1OTQwNTU5LmFwcHMuZ29vZ2xldXNlcmNvbnRlbnQuY29tIiwic3ViIjoiMTE3OTMyMDkzODg2MzMwOTI5NTIyIiwiaGQiOiJ2ZWN0b3JpbnN0aXR1dGUuYWkiLCJlbWFpbCI6Im1pcnphLmFobWFkaUB2ZWN0b3JpbnN0aXR1dGUuYWkiLCJlbWFpbF92ZXJpZmllZCI6dHJ1ZSwiYXRfaGFzaCI6ImkyZExwYXZOdnRiWVdkVDFsb0JiVkEiLCJpYXQiOjE3NzYwMjA0MjUsImV4cCI6MTc3NjAyNDAyNX0.QcgNCkqXgy4c_lY_rZeSza7vpmW9og5pX468UA5r-53Xkqh7JllOYmCXCsjTEGLdnwFjrghkBPZg8TJEJXVsNaRNInD5epqJf4Xfe9hqRhKFR6FwGbhiiOc2GMgtETNWw7PPt-MZHOLKfahI2oi2pP1D98xKvVrPnuP3lizqM0isbpJsuaunQuU5e877kC3fGIb-X4gk5XlI7Af_oDDx3yJ1Kl-SlLx8GtffMpFfwK3ZhkI3mtHBOGSsdLzbqVyY8GCf_X0neLjtQSJPkpbO3v4tvY4L81bHRCRKWuJ56cMpMGIeZ5PjpjWv976qUex8mPkhKlwUaB-ua1Kjf9ZAaw"

# Once the user submits a message to the Gradio chatbot, this function is called. It takes in the user's message (which includes the query text and optionally a file) and the current chat display (which is a list of all previous messages in the conversation).
def handle_request(message: dict, chat_display: list, conversation_id: str):
    try:
        query = message["text"]
        file = message["files"][0] if message["files"] else None

        # Get auth token and send request to Cloud Function, along with the user's query, file type, and file data (if they exist)
        token = get_auth_token()
        headers = {"Authorization": f"Bearer {token}"}
        data = {
            "query": query,
            "conversation_id": conversation_id
        }

        # If the user attached a file, include it in the request to the Cloud Function.
        if file:
            with open(file, "rb") as f:
                response = requests.post(
                    "https://core-runtime-loop-773402166266.us-central1.run.app", # This is the actual URL of the deployed Cloud Function 
                    headers=headers, # metadata about the request
                    data=data, # the user's query and conversation ID
                    files={"file": (os.path.basename(file), f)} # the attached file
                )
                
        # If the user did not attach a file, just send the query and conversation ID to the Cloud Function.
        else:
            response = requests.post(
                "https://core-runtime-loop-773402166266.us-central1.run.app", # This is the actual URL of the deployed Cloud Function 
                headers=headers,
                data=data
            )

        # Parse the response from the Cloud Function, which is the AI model's answer to the user's query. Then, update the chat   display with the user's message and the AI's response.
        print("RAW RESPONSE:", response.text)
        result = response.json()
        answer = result.get("response", result.get("error", "Unknown error"))

        chat_display.append({"role": "user", "content": query})
        chat_display.append({"role": "assistant", "content": answer})

        return chat_display, chat_display, conversation_id

    except Exception as e:
        chat_display.append({"role": "user", "content": message["text"]})
        chat_display.append({"role": "assistant", "content": f"Error: {str(e)}"})
        return chat_display, chat_display, conversation_id

# Use Gradio for the demo as the front end - TODO: change later
with gr.Blocks() as demo:
    gr.Markdown("# 🤖 Zebra Robotics AI Tutor")

    chat_display = gr.State([])
    conversation_id = gr.State(str(uuid.uuid4()))

    chatbot = gr.Chatbot(height=500, show_label=False)

    chat_input = gr.MultimodalTextbox(
        placeholder="Describe your problem and optionally attach a screenshot or .cpp file...",
        file_types=[".png", ".jpg", ".jpeg", ".webp", ".cpp"],
        show_label=False
    )

    chat_input.submit(
        fn=handle_request,
        inputs=[chat_input, chat_display, conversation_id],
        outputs=[chatbot, chat_display, conversation_id]
    )

if __name__ == "__main__":
    demo.launch(theme=gr.themes.Soft())
