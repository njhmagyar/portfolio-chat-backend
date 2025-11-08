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
            stability=0.9,      # High stability for consistent voice
            similarity_boost=0.5,  # High similarity for natural sound
            speed=0.91,
            style=0,          # Moderate style for conversational tone
            # use_speaker_boost=True  # Enhanced clarity
        )
    
    def generate_audio_with_timestamps(self, text: str) -> tuple[Optional[bytes], Optional[list]]:
        """
        Generate audio from text using ElevenLabs TTS with estimated word timestamps.
        Returns (audio_data, word_timestamps) or (None, None) if generation fails.
        
        Note: ElevenLabs doesn't directly provide word-level timestamps in the current SDK,
        so we'll generate audio and estimate timestamps based on speech rate.
        """
        try:
            if not text or not text.strip():
                logger.warning("Empty text provided for voice generation")
                return None, None
            
            # Clean the text for better TTS processing
            cleaned_text = self._clean_text_for_tts(text)
            
            # Generate audio using ElevenLabs (standard method)
            audio_generator = self.client.text_to_speech.convert(
                voice_id=self.voice_id,
                text=cleaned_text,
                voice_settings=self.voice_settings,
                model_id="eleven_flash_v2_5"
            )
            
            # Collect audio data
            audio_data = b"".join(audio_generator)
            
            if not audio_data:
                logger.error("No audio data generated")
                return None, None
            
            # Estimate word timestamps based on text analysis and average speech rate
            word_timestamps = self._estimate_word_timestamps(cleaned_text)
            
            logger.info(f"Generated audio with {len(word_timestamps)} estimated word timestamps for text length: {len(text)} chars")
            return audio_data, word_timestamps
            
        except Exception as e:
            logger.error(f"Error generating audio with timestamps: {str(e)}")
            return None, None

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
    
    def _estimate_word_timestamps(self, text: str) -> list:
        """
        Estimate word-level timestamps based on average speech rate.
        Returns list of dictionaries with word, start, and end times.
        """
        try:
            import re
            
            # Average speech rate: 150-180 words per minute (we'll use 165 WPM)
            words_per_minute = 165
            words_per_second = words_per_minute / 60.0
            
            # Split text into words, preserving punctuation context for timing
            words = re.findall(r'\b\w+\b|\S', text)
            word_timestamps = []
            
            current_time = 0.0
            
            for word in words:
                if re.match(r'\b\w+\b', word):  # Actual word
                    # Base duration for the word (characters influence duration slightly)
                    base_duration = 1.0 / words_per_second
                    # Longer words take slightly more time
                    char_factor = min(len(word) / 6.0, 1.5)  # Cap at 1.5x for very long words
                    word_duration = base_duration * char_factor
                    
                    word_timestamps.append({
                        'word': word,
                        'start': round(current_time, 2),
                        'end': round(current_time + word_duration, 2)
                    })
                    
                    current_time += word_duration
                    
                elif word in '.!?':  # Sentence endings get longer pauses
                    current_time += 0.5
                elif word in ',;:':  # Shorter pauses for other punctuation
                    current_time += 0.3
                elif word in '-()[]':  # Brief pauses for other marks
                    current_time += 0.1
            
            return word_timestamps
            
        except Exception as e:
            logger.error(f"Error estimating word timestamps: {str(e)}")
            return []
    
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
        If the message has a source_faq with audio, reuse that audio instead of generating new.
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
            
            # Check if this message was based on an FAQ with audio (the correct approach)
            if message_obj.source_faq and message_obj.source_faq.has_audio:
                logger.info(f"Message {message_obj.id} is based on FAQ {message_obj.source_faq.id} with audio, copying audio file")
                return self._copy_faq_audio_to_message(message_obj.source_faq, message_obj)
            
            # Generate new audio with timestamps if no source FAQ or FAQ has no audio
            start_time = timezone.now()
            audio_data, word_timestamps = self.generate_audio_with_timestamps(text)
            
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
            message_obj.audio_word_timestamps = word_timestamps or []
            message_obj.save()
            
            if message_obj.source_faq:
                logger.info(f"Generated new audio for message {message_obj.id} based on FAQ {message_obj.source_faq.id} (FAQ had no audio), time: {generation_time_ms}ms")
            else:
                logger.info(f"Generated new audio for message {message_obj.id} (not based on FAQ), time: {generation_time_ms}ms")
            
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
    
    
    def _copy_faq_audio_to_message(self, faq_obj, message_obj) -> bool:
        """
        Copy audio file from FAQ to message object.
        """
        try:
            if not faq_obj.has_audio:
                logger.warning(f"FAQ {faq_obj.id} has no audio to copy")
                return False
            
            # Read the FAQ audio file data
            faq_obj.audio_file.open('rb')
            audio_data = faq_obj.audio_file.read()
            faq_obj.audio_file.close()
            
            if not audio_data:
                logger.error(f"Failed to read audio data from FAQ {faq_obj.id}")
                return False
            
            # Create filename for message
            filename = f"msg_{message_obj.conversation.session_id}_{message_obj.order_in_session}.mp3"
            
            # Save audio file to message
            audio_file = ContentFile(audio_data, name=filename)
            message_obj.audio_file.save(filename, audio_file, save=False)
            
            # Copy audio metadata from FAQ (use original generation time)
            message_obj.audio_generated_at = timezone.now()
            message_obj.audio_generation_time_ms = faq_obj.audio_generation_time_ms or 0
            message_obj.audio_word_timestamps = faq_obj.audio_word_timestamps or []
            message_obj.save()
            
            logger.info(f"Successfully copied audio from FAQ {faq_obj.id} to message {message_obj.id}")
            return True
            
        except Exception as e:
            logger.error(f"Error copying FAQ audio to message: {str(e)}")
            return False

    def generate_and_save_audio_for_faq(self, faq_obj) -> bool:
        """
        Generate audio for an FAQ and save it to the FAQ object.
        Returns True if successful, False otherwise.
        """
        try:
            # Use FAQ response as the text to convert
            text = faq_obj.response
            
            if not text or not text.strip():
                logger.warning(f"Empty response for FAQ {faq_obj.id}")
                return False
            
            # Check if audio already exists
            if faq_obj.has_audio:
                logger.info(f"Audio already exists for FAQ {faq_obj.id}")
                return True
            
            # Generate audio with timestamps
            start_time = timezone.now()
            audio_data, word_timestamps = self.generate_audio_with_timestamps(text)
            
            if not audio_data:
                logger.error("Failed to generate audio data for FAQ")
                return False
            
            # Calculate generation time
            generation_time = timezone.now() - start_time
            generation_time_ms = int(generation_time.total_seconds() * 1000)
            
            # Create filename based on FAQ info
            filename = f"faq_{faq_obj.id}.mp3"
            
            # Save audio file to FAQ
            audio_file = ContentFile(audio_data, name=filename)
            faq_obj.audio_file.save(filename, audio_file, save=False)
            
            # Update audio metadata
            faq_obj.audio_generated_at = timezone.now()
            faq_obj.audio_generation_time_ms = generation_time_ms
            faq_obj.audio_word_timestamps = word_timestamps or []
            faq_obj.save()
            
            logger.info(f"Generated and saved audio for FAQ {faq_obj.id}, time: {generation_time_ms}ms")
            return True
            
        except Exception as e:
            logger.error(f"Error generating and saving audio for FAQ: {str(e)}")
            return False
    
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