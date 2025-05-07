import os
import requests

class VoiceService:
    def __init__(self, personality_config):
        self.voice_id = personality_config.get("voice_id", "elevenlabs_default")
        self.voice_provider = personality_config.get("voice_provider", "elevenlabs")
        self.voice_settings = personality_config.get("voice_settings", {})
        self.elevenlabs_api_key = os.getenv("ELEVENLABS_API_KEY")
        self.openai_api_key = os.getenv("OPENAI_API_KEY")

    def speak(self, text: str):
        # For dashboard TTS replay, return text (browser will use SpeechSynthesis)
        return {"status": "ok", "voice": self.voice_id, "provider": self.voice_provider, "text": text, "audio_url": None}

    def speak_api(self, text: str):
        # Try ElevenLabs first
        if self.elevenlabs_api_key:
            try:
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{self.voice_id}"
                headers = {"xi-api-key": self.elevenlabs_api_key}
                data = {"text": text, **self.voice_settings}
                response = requests.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    audio_url = response.json().get("audio_url")
                    return {"status": "ok", "audio_url": audio_url, "provider": "elevenlabs"}
            except Exception as e:
                pass
        # Fallback: OpenAI TTS
        if self.openai_api_key:
            try:
                url = "https://api.openai.com/v1/audio/speech"
                headers = {"Authorization": f"Bearer {self.openai_api_key}"}
                data = {"input": text, "voice": "alloy", "model": "tts-1"}
                response = requests.post(url, json=data, headers=headers)
                if response.status_code == 200:
                    audio_url = response.json().get("audio_url")
                    return {"status": "ok", "audio_url": audio_url, "provider": "openai"}
            except Exception as e:
                pass
        # Fallback: browser TTS (handled client-side)
        return {"status": "fallback", "audio_url": None, "provider": "browser"} 