""" 
This file contains the logic for calling the model API. It constructs the system prompt, formats the user input (including handling different file types), sends the request to the model, and returns the response. The main function here is call_model(), which takes in the user's query and any associated file data, builds the appropriate messages for the model, and retrieves the model's reply.
"""

from openai import OpenAI

# TODO: Move this to Secret Manager once permissions are sorted
OPENAI_API_KEY = "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"

client = OpenAI(api_key=OPENAI_API_KEY)

SYSTEM_PROMPT = """
<goal> 
You are the AI tutoring assistant for Zebra Robotics, a robotics tutoring company for elementary, middle, and high school students. Your role is to help students debug LEGO SPIKE / Scratch-like block code using screenshots and optional prompts. Your job is to guide thinking — not fix the code for them. 
</goal> 

<format_rules>
- Use a friendly, natural tutor voice (warm, conversational, encouraging).
- Sound like a real human tutor speaking to a child.
- Use Socratic style: ask 1 guiding question + suggest 1 simple thing to try next.
- Keep it concise and age-appropriate.
- Refer specifically to visible details (block names, numbers, ports, sensors, event/start blocks, order of blocks).
</format_rules>

<restrictions> 
- Do NOT give the full corrected solution. 
- Do NOT list a full replacement sequence of blocks. 
- Maximum 3 sentences total. 
</restrictions> 

<reasoning_process>
1.\tCarefully examine the screenshot.
2.\tConsider the student's prompt (if provided).
3.\tIdentify the most likely single issue.
4.\tProvide a hint that helps the student discover it themselves.
</reasoning_process>
"""

# This function calls the model API - it passes in the query, file_type, and file_data - constructing the overall prompt which is then sent to the model API
def call_model(query: str, file_type: str = None, file_data: str = None):

    # Construct the system message or system prompt
    system_message = {
        "role": "system",
        "content": SYSTEM_PROMPT
    }

    # CASE 1: No file provided (just text input) - just passes in the text to the model
    if file_type is None:
        messages = [
            system_message,
            {"role": "user", "content": query}
        ]

    # CASE 2: Image input (for block code screenshots)
    elif file_type == "image":
        messages = [
            system_message,
            {
                "role": "user",
                "content": [
                    # The first part of the 'content' is the user query as text
                    {"type": "text", "text": query}, 
                    # The second part of the 'content' is the image (which is now a Cloud Storage signed URL)
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": file_data # This is the Cloud Storage signed URL that is to be passed to model
                        }
                    }
                ]
            }
        ]

    # CASE 3: C++ code input
    elif file_type == "cpp":
        messages = [
            system_message,
            {
                "role": "user",
                "content": f"{query}\n\nHere is my C++ code:\n```cpp\n{file_data}\n```"
            }
        ]

    else:
        raise ValueError(f"Unsupported file_type: {file_type}")

    # Send the request to OpenAI's chat completion API 
    response = client.chat.completions.create(
        model="gpt-4o", # model being used (multimodal, supports images + text)
        messages=messages, # full conversation (system + user input)
        max_tokens=1000 # max length of the model's response
    )

    # Extract and return the model's reply
    return response.choices[0].message.content
