from django.contrib import admin
from .models import Resume, Experience, Bullet, SkillCategory, Skill, Education


class ExperienceInline(admin.TabularInline):
    model = Experience
    extra = 0
    ordering = ['order']


class BulletInline(admin.TabularInline):
    model = Bullet
    extra = 0
    ordering = ['order']


class SkillInline(admin.TabularInline):
    model = Skill
    extra = 0
    ordering = ['order']


class SkillCategoryInline(admin.TabularInline):
    model = SkillCategory
    extra = 0
    ordering = ['order']


class EducationInline(admin.TabularInline):
    model = Education
    extra = 0
    ordering = ['order']


@admin.register(Resume)
class ResumeAdmin(admin.ModelAdmin):
    list_display = ['title', 'subtitle', 'published', 'created_at']
    list_filter = ['published', 'created_at']
    search_fields = ['title', 'subtitle']
    inlines = [ExperienceInline, SkillCategoryInline, EducationInline]


@admin.register(Experience)
class ExperienceAdmin(admin.ModelAdmin):
    list_display = ['job_title', 'company_name', 'resume', 'start_date', 'end_date', 'order']
    list_filter = ['resume', 'start_date']
    search_fields = ['job_title', 'company_name']
    inlines = [BulletInline,]
    ordering = ['resume', 'order']


@admin.register(Bullet)
class BulletAdmin(admin.ModelAdmin):
    list_display = ['experience', 'order', 'content_preview']
    list_filter = ['experience']
    ordering = ['experience', 'order']

    def content_preview(self, obj):
        return obj.content[:50] + "..." if len(obj.content) > 50 else obj.content
    content_preview.short_description = 'Content'


@admin.register(SkillCategory)
class SkillCategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'resume', 'order']
    list_filter = ['resume']
    search_fields = ['name']
    ordering = ['resume', 'order']
    inlines = [SkillInline]


@admin.register(Skill)
class SkillAdmin(admin.ModelAdmin):
    list_display = ['name', 'skill_category', 'order']
    list_filter = ['skill_category__resume', 'skill_category']
    search_fields = ['name']
    ordering = ['skill_category', 'order']


@admin.register(Education)
class EducationAdmin(admin.ModelAdmin):
    list_display = ['title', 'subtitle', 'resume', 'order']
    list_filter = ['resume']
    search_fields = ['title', 'subtitle']
    ordering = ['resume', 'order']
