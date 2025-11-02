from django.contrib import admin
from .models import Project, CaseStudy, Section, FAQ, Conversation, Message


class SectionInline(admin.StackedInline):
    model = Section
    extra = 1
    fields = ['title', 'section_type', 'order', 'content', 'media_urls']


class CaseStudyInline(admin.StackedInline):
    model = CaseStudy
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'featured', 'created_at']
    list_filter = ['featured', 'created_at']
    search_fields = ['title', 'summary', 'description']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['featured']
    inlines = [CaseStudyInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'logo', 'slug', 'featured')
        }),
        ('Content', {
            'fields': ('summary', 'description', 'role', 'timeline')
        }),
        ('Technical Details', {
            'fields': ('technologies',),
            'description': 'Enter technologies as a JSON array, e.g., ["Django", "Vue.js", "PostgreSQL"]'
        }),
    )


@admin.register(CaseStudy)
class CaseStudyAdmin(admin.ModelAdmin):
    list_display = ['project', 'title', 'category', 'created_sections_count']
    search_fields = ['project__title', 'title', 'description']
    list_filter = ['category']
    prepopulated_fields = {'slug': ('title',)}
    inlines = [SectionInline]
    
    def created_sections_count(self, obj):
        return obj.sections.count()
    created_sections_count.short_description = 'Sections'
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('project', 'category', 'title', 'slug')
        }),
        ('Content', {
            'fields': ('description', 'hero_image')
        }),
    )


@admin.register(Section)
class SectionAdmin(admin.ModelAdmin):
    list_display = ['title', 'case_study', 'section_type', 'order']
    list_filter = ['section_type', 'case_study__category']
    search_fields = ['title', 'content', 'case_study__project__title']
    list_editable = ['order']
    
    fieldsets = (
        ('Section Details', {
            'fields': ('case_study', 'title', 'section_type', 'order')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Media', {
            'fields': ('media_urls',),
            'description': 'Enter media URLs as JSON array, e.g., ["http://example.com/image1.jpg"]'
        }),
    )


@admin.register(FAQ)
class FAQAdmin(admin.ModelAdmin):
    list_display = ['question_short', 'is_featured', 'is_active', 'has_audio_display', 'priority', 'created_at', 'updated_at']
    list_filter = ['is_featured', 'is_active', 'priority', 'created_at']
    search_fields = ['question', 'response']
    list_editable = ['is_featured', 'is_active', 'priority']
    ordering = ['-priority', '-created_at']
    readonly_fields = ['audio_generated_at', 'audio_generation_time_ms']
    
    def question_short(self, obj):
        return obj.question[:100] + ('...' if len(obj.question) > 100 else '')
    question_short.short_description = 'Question'
    
    def has_audio_display(self, obj):
        return '🔊' if obj.has_audio else '🔇'
    has_audio_display.short_description = 'Audio'
    has_audio_display.admin_order_field = 'audio_file'
    
    fieldsets = (
        ('FAQ Content', {
            'fields': ('question', 'response')
        }),
        ('Settings', {
            'fields': ('is_featured', 'is_active', 'priority'),
            'description': 'Featured FAQs appear as homepage prompts. Higher priority FAQs are included first in LLM context'
        }),
        ('Audio', {
            'fields': ('audio_file', 'audio_generated_at', 'audio_generation_time_ms'),
            'description': 'Audio is automatically generated when FAQ is saved. Generation time in milliseconds.',
            'classes': ('collapse',)
        }),
        ('Media', {
            'fields': ('media_urls',),
            'description': 'Enter media URLs as JSON array, e.g., ["http://example.com/image1.jpg"]',
            'classes': ('collapse',)
        }),
    )


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ['message_type', 'content', 'source_faq', 'response_length', 'timestamp', 'response_time_ms', 'token_count']
    readonly_fields = ['timestamp']
    ordering = ['order_in_session']


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ['session_id_short', 'started_at', 'total_messages', 'is_active', 'last_activity']
    list_filter = ['is_active', 'started_at', 'last_activity']
    search_fields = ['session_id', 'ip_address']
    readonly_fields = ['session_id', 'started_at', 'last_activity']
    inlines = [MessageInline]
    
    def session_id_short(self, obj):
        return str(obj.session_id)[:8] + "..."
    session_id_short.short_description = 'Session ID'
    
    fieldsets = (
        ('Session Info', {
            'fields': ('session_id', 'started_at', 'last_activity', 'is_active')
        }),
        ('Statistics', {
            'fields': ('total_messages',)
        }),
        ('Technical Data', {
            'fields': ('ip_address', 'user_agent'),
            'classes': ('collapse',)
        }),
    )


@admin.register(Message)
class MessageAdmin(admin.ModelAdmin):
    list_display = ['conversation_short', 'message_type', 'order_in_session', 'response_length', 'has_audio_display', 'source_faq_short', 'timestamp']
    list_filter = ['message_type', 'response_length', 'timestamp']
    search_fields = ['conversation__session_id', 'content']
    readonly_fields = ['timestamp', 'audio_generated_at', 'audio_generation_time_ms']
    
    def conversation_short(self, obj):
        return str(obj.conversation.session_id)[:8] + "..."
    conversation_short.short_description = 'Conversation'
    
    def has_audio_display(self, obj):
        return '🔊' if obj.has_audio else '🔇'
    has_audio_display.short_description = 'Audio'
    has_audio_display.admin_order_field = 'audio_file'
    
    def source_faq_short(self, obj):
        if obj.source_faq:
            return f"FAQ #{obj.source_faq.id}"
        return "-"
    source_faq_short.short_description = 'Source FAQ'
    source_faq_short.admin_order_field = 'source_faq'
    
    fieldsets = (
        ('Message Info', {
            'fields': ('conversation', 'message_type', 'order_in_session', 'response_length', 'timestamp')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Source & Audio', {
            'fields': ('source_faq', 'audio_file', 'audio_generated_at', 'audio_generation_time_ms'),
            'description': 'Source FAQ (if response was based on FAQ) and audio information'
        }),
        ('Slides', {
            'fields': ('slide_title', 'slide_body'),
            'classes': ('collapse',)
        }),
        ('Metrics', {
            'fields': ('response_time_ms', 'token_count'),
            'description': 'Performance and usage metrics (AI responses only)',
            'classes': ('collapse',)
        }),
    )
