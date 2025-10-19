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
from .models import Project, CaseStudy, Section, Conversation, Message
from .services import PortfolioLLMService
from .utils import validate_message_content, is_suspicious_pattern, get_client_ip

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
                order_in_session=next_order
            )
            
            # Generate AI response
            start_time = time.time()
            llm_service = PortfolioLLMService()
            ai_response = llm_service.generate_response(user_query)
            response_time_ms = int((time.time() - start_time) * 1000)
            
            # Estimate token count (rough approximation: ~4 chars per token)
            estimated_tokens = len(user_query + ai_response) // 4
            
            # Save AI message
            ai_message = Message.objects.create(
                conversation=conversation,
                message_type='ai_response',
                content=ai_response,
                order_in_session=next_order + 1,
                response_time_ms=response_time_ms,
                token_count=estimated_tokens
            )
            
            # Update conversation stats
            conversation.total_messages = conversation.messages.count()
            conversation.save(update_fields=['total_messages'])
        
        return JsonResponse({
            'response': ai_response,
            'query': user_query,
            'session_id': str(conversation.session_id),
            'message_count': conversation.total_messages
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
        
        messages_data = [
            {
                'id': message.id,
                'message_type': message.message_type,
                'content': message.content,
                'timestamp': message.timestamp.isoformat(),
                'order_in_session': message.order_in_session,
            }
            for message in messages
        ]
        
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
