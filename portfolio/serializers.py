from rest_framework import serializers
from .models import Project, CaseStudy, Section


class SectionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Section
        fields = ['id', 'title', 'section_type', 'content', 'order', 'media_urls']


class ProjectSerializer(serializers.ModelSerializer):
    logo = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = [
            'id', 'title', 'slug', 'summary', 'role', 'timeline', 
            'technologies', 'featured', 'logo', 'created_at'
        ]
    
    def get_logo(self, obj):
        if not obj.logo:
            return None
        
        request = self.context.get('request')
        if request:
            try:
                return request.build_absolute_uri(obj.logo.url)
            except ValueError:
                return None
        
        # Fallback for when no request context is available
        if obj.logo.url.startswith('http'):
            return obj.logo.url
        return None


class CaseStudySerializer(serializers.ModelSerializer):
    project = ProjectSerializer(read_only=True)
    sections = SectionSerializer(many=True, read_only=True)
    title = serializers.SerializerMethodField()
    slug = serializers.SerializerMethodField()
    
    class Meta:
        model = CaseStudy
        fields = [
            'id', 'title', 'slug', 'description', 'category', 
            'hero_image', 'sections', 'project'
        ]
    
    def get_title(self, obj):
        return obj.title or obj.project.title
    
    def get_slug(self, obj):
        return obj.slug or obj.project.slug