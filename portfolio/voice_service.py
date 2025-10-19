import logging
import base64
from io import BytesIO
from typing import Optional
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils import timezone
from elevenlabs import VoiceSettings
from elevenlabs.client import ElevenLabs

logger = logging.getLogger(__name__)


class VoiceService:
    """
    Service class for generating voice audio using ElevenLabs API.
    """
    
    def __init__(self):
        self.client = ElevenLabs(api_key=settings.ELEVENLABS_API_KEY)
        # Nathan's voice profile - professional, friendly male voice
        self.voice_id = settings.ELEVENLABS_VOICE_ID
        self.voice_settings = VoiceSettings(
            stability=0.8,      # High stability for consistent voice
            similarity_boost=0.8,  # High similarity for natural sound
            style=0.3,          # Moderate style for conversational tone
            use_speaker_boost=True  # Enhanced clarity
        )
    
    def generate_audio(self, text: str) -> Optional[bytes]:
        """
        Generate audio from text using ElevenLabs TTS.
        Returns audio data as bytes, or None if generation fails.
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for voice generation")
                return None
            
            # Clean the text for better TTS processing
            cleaned_text = self._clean_text_for_tts(text)
            
            # Generate audio using ElevenLabs
            audio_generator = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=cleaned_text,
                voice_settings=self.voice_settings,
                model_id="eleven_multilingual_v2"  # High-quality multilingual model
            )
            
            # Collect audio data
            audio_data = b"".join(audio_generator)
            
            if not audio_data:
                logger.error("No audio data generated")
                return None
            
            logger.info(f"Generated audio for text length: {len(text)} chars, audio size: {len(audio_data)} bytes")
            return audio_data
            
        except Exception as e:
            logger.error(f"Error generating audio with ElevenLabs: {str(e)}")
            return None
    
    def generate_audio_base64(self, text: str) -> Optional[str]:
        """
        Generate audio and return as base64 encoded string for frontend consumption.
        """
        try:
            audio_data = self.generate_audio(text)
            if not audio_data:
                return None
            
            # Encode as base64 for JSON transport
            audio_base64 = base64.b64encode(audio_data).decode('utf-8')
            return audio_base64
            
        except Exception as e:
            logger.error(f"Error encoding audio to base64: {str(e)}")
            return None
    
    def _clean_text_for_tts(self, text: str) -> str:
        """
        Clean and prepare text for better TTS processing.
        """
        # Remove excessive whitespace
        cleaned = ' '.join(text.split())
        
        # Remove markdown-style formatting that might confuse TTS
        cleaned = cleaned.replace('**', '')  # Remove bold markers
        cleaned = cleaned.replace('*', '')   # Remove italic markers
        cleaned = cleaned.replace('`', '')   # Remove code markers
        
        # Replace common abbreviations with full words for better pronunciation
        replacements = {
            'e.g.': 'for example',
            'i.e.': 'that is',
            'etc.': 'and so on',
            'vs.': 'versus',
            'w/': 'with',
            'w/o': 'without',
            'API': 'A P I',
            'URL': 'U R L',
            'HTML': 'H T M L',
            'CSS': 'C S S',
            'JS': 'JavaScript',
            'UI': 'user interface',
            'UX': 'user experience',
        }
        
        for abbrev, full_form in replacements.items():
            cleaned = cleaned.replace(abbrev, full_form)
        
        # Ensure text ends with punctuation for natural speech cadence
        if cleaned and not cleaned.endswith(('.', '!', '?')):
            cleaned += '.'
        
        return cleaned
    
    def get_available_voices(self) -> list:
        """
        Get list of available voices from ElevenLabs.
        Useful for voice selection features.
        """
        try:
            voices = self.client.voices.get_all()
            return [
                {
                    'voice_id': voice.voice_id,
                    'name': voice.name,
                    'category': getattr(voice, 'category', 'Unknown'),
                    'description': getattr(voice, 'description', '')
                }
                for voice in voices.voices
            ]
        except Exception as e:
            logger.error(f"Error fetching available voices: {str(e)}")
            return []
    
    def generate_and_save_audio_for_message(self, message_obj, text: str = None) -> bool:
        """
        Generate audio for a message and save it to the message object.
        Returns True if successful, False otherwise.
        """
        try:
            # Use message content if no text provided
            if text is None:
                text = message_obj.content
            
            # Only generate audio for AI responses
            if message_obj.message_type != 'ai_response':
                logger.info("Skipping audio generation for non-AI message")
                return False
            
            # Check if audio already exists
            if message_obj.has_audio:
                logger.info(f"Audio already exists for message {message_obj.id}")
                return True
            
            # Generate audio
            start_time = timezone.now()
            audio_data = self.generate_audio(text)
            
            if not audio_data:
                logger.error("Failed to generate audio data")
                return False
            
            # Calculate generation time
            generation_time = timezone.now() - start_time
            generation_time_ms = int(generation_time.total_seconds() * 1000)
            
            # Create filename based on message info
            filename = f"msg_{message_obj.conversation.session_id}_{message_obj.order_in_session}.mp3"
            
            # Save audio file to message
            audio_file = ContentFile(audio_data, name=filename)
            message_obj.audio_file.save(filename, audio_file, save=False)
            
            # Update audio metadata
            message_obj.audio_generated_at = timezone.now()
            message_obj.audio_generation_time_ms = generation_time_ms
            message_obj.save()
            
            logger.info(f"Generated and saved audio for message {message_obj.id}, time: {generation_time_ms}ms")
            return True
            
        except Exception as e:
            logger.error(f"Error generating and saving audio for message: {str(e)}")
            return False
    
    def get_audio_url_for_message(self, message_obj) -> Optional[str]:
        """
        Get the audio URL for a message, or None if no audio exists.
        """
        try:
            if message_obj.has_audio:
                # Django-storages handles the URL construction automatically
                # For S3: returns full S3 URL (https://bucket.s3.amazonaws.com/...)
                # For local: returns relative URL that we need to make absolute
                audio_url = message_obj.audio_file.url
                
                # If it's already a full URL (S3), return as-is
                if audio_url.startswith('http'):
                    return audio_url
                
                # If it's a relative URL (local development), make it absolute
                if audio_url.startswith('/'):
                    from django.conf import settings
                    base_url = getattr(settings, 'BACKEND_BASE_URL', 'http://localhost:8000')
                    return f"{base_url}{audio_url}"
                
                return audio_url
            return None
        except Exception as e:
            logger.error(f"Error getting audio URL for message: {str(e)}")
            return None
    
    def test_connection(self) -> bool:
        """
        Test the ElevenLabs API connection.
        """
        try:
            # Try to fetch user info to test API key
            user = self.client.user.get()
            logger.info(f"ElevenLabs connection successful. User: {user.subscription.tier}")
            return True
        except Exception as e:
            logger.error(f"ElevenLabs connection failed: {str(e)}")
            return False