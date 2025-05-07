class CommunicationService:
    def __init__(self, personality_config):
        self.personality = personality_config
        # Placeholder for voice integration
        self.voice_service = None

    def set_voice_service(self, voice_service):
        self.voice_service = voice_service

    def notify(self, message: str, channel: str = "dashboard", priority: str = "normal"):
        # TODO: Synthesize and route communication based on channel/priority
        # If channel is 'voice', use voice_service.speak
        if channel == "voice" and self.voice_service:
            return self.voice_service.speak(message)
        # For dashboard/text, return message as-is (stub)
        return {"status": "ok", "channel": channel, "message": message, "priority": priority} 