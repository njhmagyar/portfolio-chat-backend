import uuid
from django.db import models
from django.utils import timezone
from django.db.models.signals import post_save
from django.dispatch import receiver


class Project(models.Model):
        
    title = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    summary = models.TextField(max_length=500)
    description = models.TextField()
    role = models.CharField(max_length=100)
    timeline = models.CharField(max_length=50)
    technologies = models.JSONField(default=list)
    featured = models.BooleanField(default=False)
    logo = models.ImageField(upload_to='project-logos/', blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-featured', '-created_at']
    
    def __str__(self):
        return self.title


class CaseStudy(models.Model):
    CATEGORY_CHOICES = [
        ('design', 'Design'),
        ('development', 'Development'),
        ('product', 'Product Management'),
    ]

    project = models.OneToOneField(Project, on_delete=models.CASCADE, related_name='case_study')
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES)
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


class FAQ(models.Model):
    """
    Frequently Asked Questions model to store common questions and responses
    for LLM context enhancement.
    """
    question = models.TextField(help_text="The frequently asked question")
    response = models.TextField(help_text="Plain text response to the question")
    media_urls = models.JSONField(
        default=list, 
        blank=True,
        help_text="List of media URLs related to this FAQ (images, videos, etc.)"
    )
    is_featured = models.BooleanField(default=False, blank=True, help_text="Whether the FAQ's question is shown as a prompt on the homepage")
    is_active = models.BooleanField(default=True, help_text="Whether this FAQ is active and should be included in LLM context")
    priority = models.PositiveIntegerField(default=0, help_text="Higher priority FAQs are included first in LLM context")
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Audio fields for voice synthesis
    audio_file = models.FileField(upload_to='faq_audio/', blank=True, null=True)
    audio_generated_at = models.DateTimeField(blank=True, null=True)
    audio_generation_time_ms = models.PositiveIntegerField(blank=True, null=True)
    
    class Meta:
        ordering = ['-priority', '-created_at']
        verbose_name = "FAQ"
        verbose_name_plural = "FAQs"
    
    def __str__(self):
        return f"FAQ: {self.question[:100]}{'...' if len(self.question) > 100 else ''}"
    
    @property
    def has_audio(self):
        """Check if this FAQ has associated audio."""
        return bool(self.audio_file and self.audio_file.name)


class Conversation(models.Model):
    session_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    started_at = models.DateTimeField(default=timezone.now)
    last_activity = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)
    total_messages = models.PositiveIntegerField(default=0)
    ip_address = models.GenericIPAddressField(blank=True, null=True)
    user_agent = models.TextField(blank=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return f"Conversation {str(self.session_id)[:8]} ({self.total_messages} messages)"


class Message(models.Model):
    MESSAGE_TYPES = [
        ('user_query', 'User Query'),
        ('ai_response', 'AI Response'),
    ]
    
    RESPONSE_LENGTH_CHOICES = [
        ('short', 'Short'),
        ('medium', 'Medium'),
        ('long', 'Long'),
    ]
    
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='messages')
    message_type = models.CharField(max_length=20, choices=MESSAGE_TYPES)
    content = models.TextField()
    timestamp = models.DateTimeField(default=timezone.now)
    response_time_ms = models.PositiveIntegerField(null=True, blank=True)
    token_count = models.PositiveIntegerField(null=True, blank=True)
    order_in_session = models.PositiveIntegerField()
    response_length = models.CharField(max_length=10, choices=RESPONSE_LENGTH_CHOICES, default='short')
    
    # Audio fields for voice synthesis
    audio_file = models.FileField(upload_to='voice_audio/', blank=True, null=True)
    audio_generated_at = models.DateTimeField(blank=True, null=True)
    audio_generation_time_ms = models.PositiveIntegerField(blank=True, null=True)
    
    # Slide fields for presentation generation
    slide_title = models.CharField(max_length=200, blank=True, null=True)
    slide_body = models.TextField(blank=True, null=True)  # Stores HTML content
    
    # FAQ source tracking for audio reuse
    source_faq = models.ForeignKey('FAQ', on_delete=models.SET_NULL, blank=True, null=True, 
                                   help_text="FAQ that was used as the source for this response")
    
    class Meta:
        ordering = ['order_in_session']
        unique_together = ['conversation', 'order_in_session']
    
    def __str__(self):
        return f"{self.conversation.session_id} - {self.message_type} #{self.order_in_session}"
    
    @property
    def has_audio(self):
        """Check if this message has associated audio."""
        return bool(self.audio_file and self.audio_file.name)


# Signal handlers for automatic audio generation
@receiver(post_save, sender=FAQ)
def generate_faq_audio(sender, instance, created, **kwargs):
    """
    Automatically generate audio for FAQ when it's created or response is updated.
    """
    # Only generate audio if the FAQ has a response and doesn't already have audio
    if instance.response and not instance.has_audio:
        try:
            from .voice_service import VoiceService
            voice_service = VoiceService()
            
            # Generate audio for the FAQ response
            voice_service.generate_and_save_audio_for_faq(instance)
        except Exception as e:
            # Log error but don't fail the save
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to generate audio for FAQ {instance.id}: {str(e)}")
