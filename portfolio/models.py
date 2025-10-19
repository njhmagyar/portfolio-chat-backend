from django.db import models
from django.utils import timezone


class Project(models.Model):
    CATEGORY_CHOICES = [
        ('design', 'Design'),
        ('development', 'Development'),
        ('product', 'Product Management'),
    ]
    
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    summary = models.TextField(max_length=500)
    description = models.TextField()
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
    role = models.CharField(max_length=100)
    timeline = models.CharField(max_length=50)
    technologies = models.JSONField(default=list)
    featured = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-featured', '-created_at']
    
    def __str__(self):
        return self.title


class CaseStudy(models.Model):
    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='case_study')
    hero_image = models.URLField(blank=True, null=True)
    problem_statement = models.TextField()
    solution_overview = models.TextField()
    impact_metrics = models.JSONField(default=list)
    lessons_learned = models.TextField(blank=True)
    next_steps = models.TextField(blank=True)
    
    class Meta:
        verbose_name_plural = "Case studies"
    
    def __str__(self):
        return f"Case Study: {self.project.title}"


class Section(models.Model):
    SECTION_TYPES = [
        ('research', 'Research'),
        ('design', 'Design Process'),
        ('development', 'Development'),
        ('testing', 'Testing & Validation'),
        ('results', 'Results & Impact'),
        ('reflection', 'Reflection'),
    ]
    
    case_study = models.ForeignKey(CaseStudy, on_delete=models.CASCADE, related_name='sections')
    title = models.CharField(max_length=200)
    section_type = models.CharField(max_length=20, choices=SECTION_TYPES)
    content = models.TextField()
    order = models.PositiveIntegerField(default=0)
    media_urls = models.JSONField(default=list, blank=True)
    
    class Meta:
        ordering = ['order']
    
    def __str__(self):
        return f"{self.case_study.project.title} - {self.title}"
