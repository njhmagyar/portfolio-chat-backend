from django.urls import path
from . import views

urlpatterns = [
    path('api/chat/', views.chat_query, name='chat_query'),
    path('api/projects/', views.projects_list, name='projects_list'),
    path('api/conversation/<uuid:session_id>/', views.conversation_history, name='conversation_history'),
]