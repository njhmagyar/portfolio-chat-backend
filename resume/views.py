from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .models import Resume
from .serializers import ResumeDetailSerializer


class ResumeDetailView(APIView):
    """
    Retrieve a complete resume with all related data in one optimized request.
    """
    
    def get(self, request, pk=None):
        # If no pk provided, get the published resume
        if pk is None:
            resume = get_object_or_404(Resume, published=True)
        else:
            resume = get_object_or_404(Resume, pk=pk)
        
        # Optimize database queries with prefetch_related
        resume = Resume.objects.prefetch_related(
            'experiences__bullets',
            'skill_categories__skills',
            'education'
        ).get(pk=resume.pk)
        
        serializer = ResumeDetailSerializer(resume)
        return Response(serializer.data, status=status.HTTP_200_OK)
