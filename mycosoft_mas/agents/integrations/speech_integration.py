import os
import asyncio
import azure.cognitiveservices.speech as speechsdk
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SpeechIntegration:
    """Handles speech-to-text and text-to-speech integration"""
    
    def __init__(self, config=None):
        self.config = config or self._load_default_config()
        self._init_speech_config()
    
    def _load_default_config(self):
        """Load default configuration"""
        return {
            "azure_speech_key": os.getenv("AZURE_SPEECH_KEY"),
            "azure_speech_region": os.getenv("AZURE_SPEECH_REGION"),
            "voice_name": os.getenv("AZURE_SPEECH_VOICE", "en-US-JennyNeural")
        }
    
    def _init_speech_config(self):
        """Initialize speech configuration"""
        self.speech_config = speechsdk.SpeechConfig(
            subscription=self.config["azure_speech_key"],
            region=self.config["azure_speech_region"]
        )
        
        # Set voice
        self.speech_config.speech_synthesis_voice_name = self.config["voice_name"]
    
    async def speech_to_text(self, audio_source=None):
        """
        Convert speech to text
        
        Args:
            audio_source: Audio source to use (default: microphone)
            
        Returns:
            Recognized text
        """
        # Create audio config
        if audio_source is None:
            audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        else:
            audio_config = speechsdk.audio.AudioConfig(filename=audio_source)
        
        # Create speech recognizer
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        
        # Create a future to hold the result
        result_future = asyncio.Future()
        
        # Set up callbacks
        def handle_result(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                result_future.set_result(evt.result.text)
            else:
                result_future.set_result("")
        
        def handle_canceled(evt):
            result_future.set_result("")
        
        # Connect callbacks
        speech_recognizer.recognized.connect(handle_result)
        speech_recognizer.canceled.connect(handle_canceled)
        
        # Start recognition
        speech_recognizer.start_continuous_recognition()
        
        # Wait for result
        result = await result_future
        
        # Stop recognition
        speech_recognizer.stop_continuous_recognition()
        
        return result
    
    async def text_to_speech(self, text, audio_output=None):
        """
        Convert text to speech
        
        Args:
            text: Text to convert to speech
            audio_output: Audio output to use (default: speaker)
            
        Returns:
            True if successful, False otherwise
        """
        # Create audio config
        if audio_output is None:
            audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
        else:
            audio_config = speechsdk.audio.AudioOutputConfig(filename=audio_output)
        
        # Create speech synthesizer
        speech_synthesizer = speechsdk.SpeechSynthesizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        
        # Create a future to hold the result
        result_future = asyncio.Future()
        
        # Set up callbacks
        def handle_result(evt):
            result_future.set_result(True)
        
        def handle_canceled(evt):
            result_future.set_result(False)
        
        # Connect callbacks
        speech_synthesizer.synthesis_completed.connect(handle_result)
        speech_synthesizer.synthesis_canceled.connect(handle_canceled)
        
        # Start synthesis
        speech_synthesizer.speak_text_async(text)
        
        # Wait for result
        result = await result_future
        
        return result
    
    async def start_continuous_listening(self, callback):
        """
        Start continuous listening for speech
        
        Args:
            callback: Callback function to call when speech is recognized
            
        Returns:
            Speech recognizer object
        """
        # Create audio config
        audio_config = speechsdk.audio.AudioConfig(use_default_microphone=True)
        
        # Create speech recognizer
        speech_recognizer = speechsdk.SpeechRecognizer(
            speech_config=self.speech_config,
            audio_config=audio_config
        )
        
        # Set up callback
        def handle_result(evt):
            if evt.result.reason == speechsdk.ResultReason.RecognizedSpeech:
                asyncio.create_task(callback(evt.result.text))
        
        # Connect callback
        speech_recognizer.recognized.connect(handle_result)
        
        # Start recognition
        speech_recognizer.start_continuous_recognition()
        
        return speech_recognizer
    
    def stop_continuous_listening(self, speech_recognizer):
        """
        Stop continuous listening
        
        Args:
            speech_recognizer: Speech recognizer object to stop
        """
        speech_recognizer.stop_continuous_recognition() 