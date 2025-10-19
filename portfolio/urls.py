from django.urls import path
from . import views

urlpatterns = [
    path('api/chat/', views.chat_query, name='chat_query'),
    path('api/projects/', views.projects_list, name='projects_list'),
    path('api/conversation/<uuid:session_id>/', views.conversation_history, name='conversation_history'),
    path('api/voice/generate/', views.generate_voice, name='generate_voice'),
    path('api/voice/generate-message/', views.generate_message_audio, name='generate_message_audio'),
    path('api/voice/test/', views.voice_test, name='voice_test'),
]