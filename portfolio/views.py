import json
import logging
import time
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from django.conf import settings
from django.db import transaction
from django.core.cache import cache
from django.utils import timezone
from datetime import timedelta
from .models import Project, CaseStudy, Section, Conversation, Message, FAQ
from .services import PortfolioLLMService
from .utils import validate_message_content, is_suspicious_pattern, get_client_ip
from .voice_service import VoiceService
from .slide_service import SlideService

logger = logging.getLogger(__name__)


@csrf_exempt
@require_http_methods(["POST"])
def chat_query(request):
    """
    Handle chat queries from the frontend and return LLM-generated responses
    based on portfolio data. Tracks conversation history with abuse prevention.
    """
    try:
        data = json.loads(request.body)
        user_query = data.get('query', '').strip()
        session_id = data.get('session_id')  # Frontend will provide this
        response_length = data.get('response_length', 'short')  # Default to short
        
        if not user_query:
            return JsonResponse({
                'error': 'Query is required'
            }, status=400)
        
        # Get client info for analytics and rate limiting
        ip_address = get_client_ip(request)
        user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # ABUSE PREVENTION CHECKS
        
        # 1. Rate limiting per IP address (10 requests per minute)
        ip_key = f"chat_rate_{ip_address}"
        recent_requests = cache.get(ip_key, 0)
        if recent_requests >= 10:
            logger.warning(f"Rate limit exceeded for IP: {ip_address}")
            return JsonResponse({
                'error': 'Rate limit exceeded. Please wait before sending another message.'
            }, status=429)
        cache.set(ip_key, recent_requests + 1, 60)  # 1 minute expiry
        
        # 2. Message content validation (length, profanity, spam patterns)
        is_valid, error_message = validate_message_content(user_query)
        if not is_valid:
            logger.warning(f"Invalid message from IP {ip_address}: {error_message}")
            return JsonResponse({
                'error': error_message
            }, status=400)
        
        # 3. Session limits check (if session exists)
        if session_id:
            try:
                existing_conversation = Conversation.objects.get(session_id=session_id)
                # Check session message limit (50 messages max)
                if existing_conversation.total_messages >= 50:
                    return JsonResponse({
                        'error': 'Session message limit reached. Please start a new conversation.'
                    }, status=429)
                
                # Check for suspicious patterns (repeated messages)
                recent_user_messages = list(existing_conversation.messages.filter(
                    message_type='user_query'
                ).order_by('-timestamp')[:3].values_list('content', flat=True))
                
                if is_suspicious_pattern(user_query, recent_user_messages):
                    logger.warning(f"Suspicious pattern detected from IP {ip_address}: repeated message")
                    return JsonResponse({
                        'error': 'Please avoid sending duplicate messages.'
                    }, status=400)
                    
            except Conversation.DoesNotExist:
                pass  # Will create new conversation below
        
        with transaction.atomic():
            # Get or create conversation
            if session_id:
                try:
                    conversation = Conversation.objects.get(session_id=session_id)
                    # Update last activity
                    conversation.save(update_fields=['last_activity'])
                except Conversation.DoesNotExist:
                    # Session ID exists in frontend but not in database
                    # Create a new conversation
                    conversation = Conversation.objects.create(
                        ip_address=ip_address,
                        user_agent=user_agent
                    )
                    logger.warning(f"Session {session_id} not found, created new conversation {conversation.session_id}")
            else:
                # Create new conversation
                conversation = Conversation.objects.create(
                    ip_address=ip_address,
                    user_agent=user_agent
                )
            
            # Get next message order
            next_order = conversation.messages.count() + 1
            
            # Save user message
            user_message = Message.objects.create(
                conversation=conversation,
                message_type='user_query',
                content=user_query,
                order_in_session=next_order,
                response_length=response_length
            )
            
            # Generate AI response
            start_time = time.time()
            llm_service = PortfolioLLMService()
            ai_response, source_faq = llm_service.generate_response(user_query, response_length=response_length)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Estimate token count (rough approximation: ~4 chars per token)
            estimated_tokens = len(user_query + ai_response) // 4
            
            # Save AI message with source FAQ if identified
            ai_message = Message.objects.create(
                conversation=conversation,
                message_type='ai_response',
                content=ai_response,
                order_in_session=next_order + 1,
                response_time_ms=response_time_ms,
                token_count=estimated_tokens,
                response_length=response_length,
                source_faq=source_faq  # Track which FAQ was used as source
            )
            
            # Generate slide content for the AI response
            slide_service = SlideService()
            slide_service.generate_slide_for_message(ai_message)
            
            # Update conversation stats
            conversation.total_messages = conversation.messages.count()
            conversation.save(update_fields=['total_messages'])
        
        return JsonResponse({
            'response': ai_response,
            'query': user_query,
            'session_id': str(conversation.session_id),
            'message_count': conversation.total_messages,
            'user_message_id': user_message.id,
            'ai_message_id': ai_message.id,
            'slide_title': ai_message.slide_title,
            'slide_body': ai_message.slide_body
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in chat_query: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred processing your request'
        }, status=500)




@require_http_methods(["GET"])
def projects_list(request):
    """
    Return a list of all projects for API consumption.
    """
    try:
        projects = Project.objects.all()
        projects_data = []
        
        for project in projects:
            # Handle logo URL (make absolute if needed)
            logo_url = None
            if project.logo:
                logo_url = project.logo.url
                # If it's already a full URL (S3), use as-is
                if not logo_url.startswith('http') and logo_url.startswith('/'):
                    # If it's a relative URL (local development), make it absolute
                    base_url = getattr(settings, 'BACKEND_BASE_URL', 'http://localhost:8000')
                    logo_url = f"{base_url}{logo_url}"
            
            project_data = {
                'id': project.id,
                'title': project.title,
                'slug': project.slug,
                'summary': project.summary,
                'description': project.description,
                'role': project.role,
                'timeline': project.timeline,
                'technologies': project.technologies,
                'featured': project.featured,
                'logo': logo_url,
                'created_at': project.created_at.isoformat(),
            }
            
            # Include case study if it exists
            if hasattr(project, 'case_study'):
                case_study = project.case_study
                project_data['case_study'] = {
                    'category': case_study.category,
                    'hero_image': case_study.hero_image,
                    'problem_statement': case_study.problem_statement,
                    'solution_overview': case_study.solution_overview,
                    'impact_metrics': case_study.impact_metrics,
                    'lessons_learned': case_study.lessons_learned,
                    'next_steps': case_study.next_steps,
                }
                
                # Include sections
                sections = case_study.sections.all()
                project_data['case_study']['sections'] = [
                    {
                        'title': section.title,
                        'section_type': section.section_type,
                        'content': section.content,
                        'order': section.order,
                        'media_urls': section.media_urls,
                    }
                    for section in sections
                ]
            
            projects_data.append(project_data)
        
        return JsonResponse({
            'projects': projects_data,
            'count': len(projects_data)
        })
        
    except Exception as e:
        logger.error(f"Error in projects_list: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred fetching projects'
        }, status=500)


@require_http_methods(["GET"])
def conversation_history(request, session_id):
    """
    Return the message history for a specific conversation session.
    """
    try:
        conversation = Conversation.objects.get(session_id=session_id)
        
        # Get all messages for this conversation
        messages = conversation.messages.all()
        
        messages_data = []
        voice_service = VoiceService()
        
        for message in messages:
            message_data = {
                'id': message.id,
                'message_type': message.message_type,
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'order_in_session': message.order_in_session,
                'has_audio': message.has_audio,
                'audio_url': voice_service.get_audio_url_for_message(message) if message.has_audio else None,
                'slide_title': message.slide_title,
                'slide_body': message.slide_body,
            }
            messages_data.append(message_data)
        
        return JsonResponse({
            'session_id': str(conversation.session_id),
            'messages': messages_data,
            'total_messages': conversation.total_messages,
            'started_at': conversation.started_at.isoformat(),
            'last_activity': conversation.last_activity.isoformat(),
        })
        
    except Conversation.DoesNotExist:
        return JsonResponse({
            'error': 'Conversation not found'
        }, status=404)
    except Exception as e:
        logger.error(f"Error in conversation_history: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred fetching conversation history'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generate_voice(request):
    """
    Generate voice audio for given text using ElevenLabs TTS.
    Returns base64-encoded audio data.
    """
    try:
        data = json.loads(request.body)
        text = data.get('text', '').strip()
        
        if not text:
            return JsonResponse({
                'error': 'Text is required'
            }, status=400)
        
        # Get client info for rate limiting
        ip_address = get_client_ip(request)
        
        # Voice generation rate limiting (5 requests per minute per IP)
        voice_rate_key = f"voice_rate_{ip_address}"
        recent_voice_requests = cache.get(voice_rate_key, 0)
        if recent_voice_requests >= 5:
            logger.warning(f"Voice rate limit exceeded for IP: {ip_address}")
            return JsonResponse({
                'error': 'Voice generation rate limit exceeded. Please wait before generating more audio.'
            }, status=429)
        cache.set(voice_rate_key, recent_voice_requests + 1, 60)  # 1 minute expiry
        
        # Text length validation for voice generation
        if len(text) > 1000:  # Reasonable limit for TTS
            return JsonResponse({
                'error': 'Text too long for voice generation (maximum 1000 characters)'
            }, status=400)
        
        # Initialize voice service
        voice_service = VoiceService()
        
        # Check if ElevenLabs API key is configured
        if not settings.ELEVENLABS_API_KEY:
            logger.error("ElevenLabs API key not configured")
            return JsonResponse({
                'error': 'Voice generation service not configured'
            }, status=503)
        
        # Generate audio
        start_time = time.time()
        audio_base64 = voice_service.generate_audio_base64(text)
        generation_time_ms = int((time.time() - start_time) * 1000)
        
        if not audio_base64:
            return JsonResponse({
                'error': 'Failed to generate voice audio'
            }, status=500)
        
        logger.info(f"Generated voice for text length: {len(text)} chars, time: {generation_time_ms}ms")
        
        return JsonResponse({
            'audio_data': audio_base64,
            'audio_format': 'mp3',
            'text_length': len(text),
            'generation_time_ms': generation_time_ms
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in generate_voice: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred generating voice audio'
        }, status=500)


@require_http_methods(["GET"])
def voice_test(request):
    """
    Test ElevenLabs API connection and return available voices.
    """
    try:
        voice_service = VoiceService()
        
        # Test connection
        connection_ok = voice_service.test_connection()
        
        if not connection_ok:
            return JsonResponse({
                'status': 'error',
                'message': 'ElevenLabs API connection failed'
            }, status=503)
        
        # Get available voices
        voices = voice_service.get_available_voices()
        
        return JsonResponse({
            'status': 'success',
            'message': 'ElevenLabs API connection successful',
            'available_voices': voices[:10],  # Limit to first 10 voices
            'total_voices': len(voices)
        })
        
    except Exception as e:
        logger.error(f"Error in voice_test: {str(e)}")
        return JsonResponse({
            'status': 'error',
            'message': 'Voice service test failed'
        }, status=500)


@csrf_exempt
@require_http_methods(["POST"])
def generate_message_audio(request):
    """
    Generate audio for a specific message by message ID.
    """
    try:
        data = json.loads(request.body)
        message_id = data.get('message_id')
        
        if not message_id:
            return JsonResponse({
                'error': 'message_id is required'
            }, status=400)
        
        # Get client info for rate limiting
        ip_address = get_client_ip(request)
        
        # Voice generation rate limiting (5 requests per minute per IP)
        voice_rate_key = f"voice_rate_{ip_address}"
        recent_voice_requests = cache.get(voice_rate_key, 0)
        if recent_voice_requests >= 5:
            logger.warning(f"Voice rate limit exceeded for IP: {ip_address}")
            return JsonResponse({
                'error': 'Voice generation rate limit exceeded. Please wait before generating more audio.'
            }, status=429)
        cache.set(voice_rate_key, recent_voice_requests + 1, 60)  # 1 minute expiry
        
        try:
            message = Message.objects.get(id=message_id)
        except Message.DoesNotExist:
            return JsonResponse({
                'error': 'Message not found'
            }, status=404)
        
        # Only generate audio for AI responses
        if message.message_type != 'ai_response':
            return JsonResponse({
                'error': 'Audio can only be generated for AI responses'
            }, status=400)
        
        # Check if ElevenLabs API key is configured
        if not settings.ELEVENLABS_API_KEY:
            logger.error("ElevenLabs API key not configured")
            return JsonResponse({
                'error': 'Voice generation service not configured'
            }, status=503)
        
        # Generate and save audio
        voice_service = VoiceService()
        success = voice_service.generate_and_save_audio_for_message(message)
        
        if not success:
            return JsonResponse({
                'error': 'Failed to generate audio for message'
            }, status=500)
        
        # Get the audio URL
        audio_url = voice_service.get_audio_url_for_message(message)
        
        return JsonResponse({
            'message_id': message_id,
            'audio_url': audio_url,
            'has_audio': message.has_audio,
            'generation_time_ms': message.audio_generation_time_ms
        })
        
    except json.JSONDecodeError:
        return JsonResponse({
            'error': 'Invalid JSON in request body'
        }, status=400)
    except Exception as e:
        logger.error(f"Error in generate_message_audio: {str(e)}")
        return JsonResponse({
            'error': 'An error occurred generating message audio'
        }, status=500)


@require_http_methods(["GET"])
def featured_questions(request):
    """
    Return featured FAQ questions for homepage prompts.
    Falls back to default questions if no FAQs are featured.
    """
    try:
        # Get featured FAQ questions
        featured_faqs = FAQ.objects.filter(is_featured=True, is_active=True).order_by('-priority', '-created_at')[:6]
        
        if featured_faqs:
            # Use featured FAQ questions with audio URLs
            questions_data = []
            voice_service = VoiceService()
            
            for faq in featured_faqs:
                # Get audio URL using the same pattern as message audio
                audio_url = None
                if faq.has_audio:
                    try:
                        # Handle audio URL generation similar to message audio
                        if faq.audio_file.url.startswith('http'):
                            audio_url = faq.audio_file.url
                        elif faq.audio_file.url.startswith('/'):
                            base_url = getattr(settings, 'BACKEND_BASE_URL', 'http://localhost:8000')
                            audio_url = f"{base_url}{faq.audio_file.url}"
                        else:
                            audio_url = faq.audio_file.url
                    except Exception as e:
                        logger.error(f"Error getting audio URL for FAQ {faq.id}: {str(e)}")
                        audio_url = None
                
                question_data = {
                    'question': faq.question,
                    'response': faq.response,
                    'has_audio': faq.has_audio,
                    'audio_url': audio_url,
                    'faq_id': faq.id
                }
                questions_data.append(question_data)
            
            return JsonResponse({
                'questions': questions_data,
                'source': 'featured_faqs',
                'count': len(questions_data)
            })
        else:
            # Fallback to default hardcoded questions (without audio)
            questions = [
                {
                    'question': "What projects have you worked on?",
                    'response': None,
                    'has_audio': False,
                    'audio_url': None,
                    'faq_id': None
                },
                {
                    'question': "What are your main skills?",
                    'response': None,
                    'has_audio': False,
                    'audio_url': None,
                    'faq_id': None
                }, 
                {
                    'question': "Tell me about your experience",
                    'response': None,
                    'has_audio': False,
                    'audio_url': None,
                    'faq_id': None
                },
                {
                    'question': "What's your design process?",
                    'response': None,
                    'has_audio': False,
                    'audio_url': None,
                    'faq_id': None
                }
            ]
            
            return JsonResponse({
                'questions': questions,
                'source': 'default',
                'count': len(questions)
            })
        
    except Exception as e:
        logger.error(f"Error in featured_questions: {str(e)}")
        # Return fallback questions on error
        return JsonResponse({
            'questions': [
                {
                    'question': "What projects have you worked on?",
                    'response': None,
                    'has_audio': False,
                    'audio_url': None,
                    'faq_id': None
                },
                {
                    'question': "What are your main skills?",
                    'response': None,
                    'has_audio': False,
                    'audio_url': None,
                    'faq_id': None
                },
                {
                    'question': "Tell me about your experience",
                    'response': None,
                    'has_audio': False,
                    'audio_url': None,
                    'faq_id': None
                }, 
                {
                    'question': "What's your design process?",
                    'response': None,
                    'has_audio': False,
                    'audio_url': None,
                    'faq_id': None
                }
            ],
            'source': 'fallback',
            'count': 4
        })
