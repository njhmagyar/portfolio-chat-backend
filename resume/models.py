from django.db import models
from django.core.exceptions import ValidationError


class Resume(models.Model):
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    summary = models.TextField(blank=True)
    file_url = models.URLField(help_text="URL to AWS-hosted resume file")
    published = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['published'],
                condition=models.Q(published=True),
                name='unique_published_resume'
            )
        ]

    def __str__(self):
        return self.title

    def clean(self):
        if self.published and Resume.objects.filter(published=True).exclude(id=self.id).exists():
            raise ValidationError("Only one resume can be published at a time.")


class Experience(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='experiences')
    company_name = models.CharField(max_length=200)
    job_title = models.CharField(max_length=200)
    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order', '-start_date']

    def __str__(self):
        return f"{self.job_title} at {self.company_name}"


class Bullet(models.Model):
    experience = models.ForeignKey(Experience, on_delete=models.CASCADE, related_name='bullets')
    content = models.TextField()  # Rich text field
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return f"Bullet {self.order}: {self.content[:50]}..."


class SkillCategory(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='skill_categories')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name_plural = "Skill Categories"

    def __str__(self):
        return self.name


class Skill(models.Model):
    skill_category = models.ForeignKey(SkillCategory, on_delete=models.CASCADE, related_name='skills')
    name = models.CharField(max_length=100)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']

    def __str__(self):
        return self.name


class Education(models.Model):
    resume = models.ForeignKey(Resume, on_delete=models.CASCADE, related_name='education')
    title = models.CharField(max_length=200)
    subtitle = models.CharField(max_length=200, blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['order']
        verbose_name_plural = "Education"

    def __str__(self):
        return self.title
