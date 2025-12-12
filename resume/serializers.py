from rest_framework import serializers
from .models import Resume, Experience, Bullet, SkillCategory, Skill, Education


class SkillSerializer(serializers.ModelSerializer):
    class Meta:
        model = Skill
        fields = ['id', 'name', 'order']


class SkillCategorySerializer(serializers.ModelSerializer):
    skills = SkillSerializer(many=True, read_only=True)
    
    class Meta:
        model = SkillCategory
        fields = ['id', 'name', 'order', 'skills']


class BulletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Bullet
        fields = ['id', 'content', 'order']


class ExperienceSerializer(serializers.ModelSerializer):
    bullets = BulletSerializer(many=True, read_only=True)
    class Meta:
        model = Experience
        fields = ['id', 'company_name', 'job_title', 'start_date', 'end_date', 'order', 'bullets']


class EducationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Education
        fields = ['id', 'title', 'subtitle', 'order']


class ResumeDetailSerializer(serializers.ModelSerializer):
    experiences = ExperienceSerializer(many=True, read_only=True)
    skill_categories = SkillCategorySerializer(many=True, read_only=True)
    education = EducationSerializer(many=True, read_only=True)
    
    class Meta:
        model = Resume
        fields = [
            'id', 'title', 'subtitle', 'summary', 'file_url', 'published',
            'created_at', 'updated_at', 'experiences', 
            'skill_categories', 'education'
        ]