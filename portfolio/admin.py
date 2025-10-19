from django.contrib import admin
from .models import Project, CaseStudy, Section, Conversation, Message


class SectionInline(admin.TabularInline):
    model = Section
    extra = 1
    fields = ['title', 'section_type', 'order']


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
            'fields': ('title', 'slug', 'featured')
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
    list_display = ['project', 'category', 'created_sections_count']
    search_fields = ['project__title', 'problem_statement', 'solution_overview']
    inlines = [SectionInline]
    
    def created_sections_count(self, obj):
        return obj.sections.count()
    created_sections_count.short_description = 'Sections'
    
    fieldsets = (
        ('Project Link', {
            'fields': ('project', 'category')
        }),
        ('Case Study Content', {
            'fields': ('problem_statement', 'solution_overview', 'lessons_learned', 'next_steps')
        }),
        ('Impact & Metrics', {
            'fields': ('impact_metrics',),
            'description': 'Enter metrics as JSON array, e.g., [{"metric": "Conversion Rate", "value": "+23%"}]'
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


class MessageInline(admin.TabularInline):
    model = Message
    extra = 0
    fields = ['message_type', 'content', 'timestamp', 'response_time_ms', 'token_count']
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
    list_display = ['conversation_short', 'message_type', 'order_in_session', 'timestamp', 'response_time_ms', 'token_count']
    list_filter = ['message_type', 'timestamp']
    search_fields = ['conversation__session_id', 'content']
    readonly_fields = ['timestamp']
    
    def conversation_short(self, obj):
        return str(obj.conversation.session_id)[:8] + "..."
    conversation_short.short_description = 'Conversation'
    
    fieldsets = (
        ('Message Info', {
            'fields': ('conversation', 'message_type', 'order_in_session', 'timestamp')
        }),
        ('Content', {
            'fields': ('content',)
        }),
        ('Metrics', {
            'fields': ('response_time_ms', 'token_count'),
            'description': 'Performance and usage metrics (AI responses only)'
        }),
    )
