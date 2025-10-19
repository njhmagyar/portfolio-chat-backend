from django.contrib import admin
from .models import Project, CaseStudy, Section


class SectionInline(admin.TabularInline):
    model = Section
    extra = 1
    fields = ['title', 'section_type', 'order']


class CaseStudyInline(admin.StackedInline):
    model = CaseStudy
    extra = 0


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ['title', 'category', 'featured', 'created_at']
    list_filter = ['category', 'featured', 'created_at']
    search_fields = ['title', 'summary', 'description']
    prepopulated_fields = {'slug': ('title',)}
    list_editable = ['featured']
    inlines = [CaseStudyInline]
    
    fieldsets = (
        ('Basic Information', {
            'fields': ('title', 'slug', 'category', 'emoji', 'featured')
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
    list_display = ['project', 'created_sections_count']
    search_fields = ['project__title', 'problem_statement', 'solution_overview']
    inlines = [SectionInline]
    
    def created_sections_count(self, obj):
        return obj.sections.count()
    created_sections_count.short_description = 'Sections'
    
    fieldsets = (
        ('Project Link', {
            'fields': ('project',)
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
    list_filter = ['section_type', 'case_study__project__category']
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
