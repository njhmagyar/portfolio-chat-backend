from django.urls import path
from .views import ResumeDetailView

urlpatterns = [
    path('', ResumeDetailView.as_view(), name='resume-published'),
    path('<int:pk>/', ResumeDetailView.as_view(), name='resume-detail'),
]