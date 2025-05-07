import os
import requests

class ChatService:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        self.gemini_api_key = os.getenv("GOOGLE_GEMINI_API_KEY")

    def chat(self, message: str, context: dict = None):
        # Try OpenAI first
        if self.openai_api_key:
            try:
                url = "https://api.openai.com/v1/chat/completions"
                headers = {"Authorization": f"Bearer {self.openai_api_key}"}
                data = {
                    "model": "gpt-4o",
                    "messages": [{"role": "user", "content": message}],
                    "max_tokens": 512
                }
                response = requests.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    return response.json()["choices"][0]["message"]["content"]
            except Exception as e:
                pass
        # Fallback: Anthropic Claude
        if self.anthropic_api_key:
            try:
                url = "https://api.anthropic.com/v1/messages"
                headers = {"x-api-key": self.anthropic_api_key, "anthropic-version": "2023-06-01"}
                data = {
                    "model": "claude-3-opus-20240229",
                    "max_tokens": 512,
                    "messages": [{"role": "user", "content": message}]
                }
                response = requests.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    return response.json()["content"][0]["text"]
            except Exception as e:
                pass
        # Fallback: Google Gemini (stub, as public API may differ)
        if self.gemini_api_key:
            try:
                url = "https://generativelanguage.googleapis.com/v1beta/models/gemini-pro:generateContent?key=" + self.gemini_api_key
                data = {"contents": [{"parts": [{"text": message}]}]}
                response = requests.post(url, json=data)
                if response.status_code == 200:
                    return response.json()["candidates"][0]["content"]["parts"][0]["text"]
            except Exception as e:
                pass
        return "Sorry, I couldn't process your request right now." 