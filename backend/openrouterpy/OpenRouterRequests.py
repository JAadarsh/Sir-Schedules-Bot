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

    try:
        http_response = requests.post(
            url=OPENROUTER_URL,
            headers={
                'Authorization': f'Bearer {OR_TOKEN}',
                'Content-Type': 'application/json',
            },
            data=json.dumps(payload),
        )
        http_response.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise RuntimeError(f'OpenRouter API request failed: {str(e)}')
    
    try:
        response_data = http_response.json()
    except json.JSONDecodeError as e:
        raise RuntimeError(f'Failed to parse OpenRouter response: {str(e)}')
    
    try:
        assistant_message = response_data['choices'][0]['message']
        return assistant_message.get('content', '')
    except (KeyError, IndexError) as e:
        raise RuntimeError(f'Unexpected OpenRouter response structure: {str(e)}')