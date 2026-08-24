"""
Aadarsh Joshi 2026
"""

from dotenv import load_dotenv
import os
import json
import requests

load_dotenv()
OR_TOKEN = os.getenv('OPENROUTER')
OPENROUTER_URL = 'https://openrouter.ai/api/v1/chat/completions'
MODEL_NAME = 'liquid/lfm-2.5-1.2b-instruct:free' # MODEL_NAME = 'liquid/lfm-2.5-2.6b:free' test this later


def response(prompt: str, reasoning: bool = True) -> str:
    """Send a prompt to OpenRouter and return the assistant response as a string."""
    if not OR_TOKEN:
        raise ValueError('OPENROUTER environment variable is not set.')

    payload = {
        'model': MODEL_NAME,
        'messages': [
            {'role': 'user', 'content': f"Respond to this prompt very briefly in under 100 words with no special characters: {prompt}"}
        ],
    }

    if reasoning:
        payload['reasoning'] = {'enabled': True}

    response = requests.post(
        url=OPENROUTER_URL,
        headers={
            'Authorization': f'Bearer {OR_TOKEN}',
            'Content-Type': 'application/json',
        },
        data=json.dumps(payload),
    )
    response.raise_for_status()
    response_data = response.json()

    assistant_message = response_data['choices'][0]['message']
    return assistant_message.get('content', '') or ''