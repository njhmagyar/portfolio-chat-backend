import json
import os
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from resume.models import Resume, Experience, Bullet, SkillCategory, Skill, Education


class Command(BaseCommand):
    help = 'Idempotently seed resume data from JSON fixture'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fixture',
            type=str,
            default='nathan_resume.json',
            help='JSON fixture file name (default: nathan_resume.json)'
        )

    def handle(self, *args, **options):
        fixture_file = options['fixture']
        fixture_path = os.path.join('resume', 'fixtures', fixture_file)
        
        if not os.path.exists(fixture_path):
            self.stdout.write(
                self.style.ERROR(f'Fixture file not found: {fixture_path}')
            )
            return

        with open(fixture_path, 'r') as f:
            data = json.load(f)

        try:
            # Create or update resume
            resume_data = data['resume']
            resume, created = Resume.objects.update_or_create(
                title=resume_data['title'],
                defaults={
                    'subtitle': resume_data['subtitle'],
                    'summary': resume_data['summary'],
                    'file_url': resume_data['file_url'],
                    'published': resume_data['published']
                }
            )
            
            if created:
                self.stdout.write(
                    self.style.SUCCESS(f'Created resume: {resume.title}')
                )
            else:
                self.stdout.write(
                    self.style.WARNING(f'Updated existing resume: {resume.title}')
                )

            # Create or update experiences and their bullets
            for exp_data in data['experiences']:
                experience, exp_created = Experience.objects.update_or_create(
                    resume=resume,
                    company_name=exp_data['company_name'],
                    job_title=exp_data['job_title'],
                    defaults={
                        'start_date': exp_data['start_date'],
                        'end_date': exp_data['end_date'],
                        'order': exp_data['order']
                    }
                )
                
                status = 'Created' if exp_created else 'Updated'
                self.stdout.write(f'  {status} experience: {experience.job_title} at {experience.company_name}')
                
                # Create or update bullets for this experience
                for bullet_data in exp_data['bullets']:
                    bullet, bullet_created = Bullet.objects.update_or_create(
                        experience=experience,
                        content=bullet_data['content'],
                        defaults={
                            'order': bullet_data['order']
                        }
                    )
                    
                    if bullet_created:
                        self.stdout.write(f'    Created bullet: {bullet.content[:50]}...')

            # Create or update skill categories and skills
            for cat_data in data['skill_categories']:
                skill_category, cat_created = SkillCategory.objects.update_or_create(
                    resume=resume,
                    name=cat_data['name'],
                    defaults={
                        'order': cat_data['order']
                    }
                )
                
                status = 'Created' if cat_created else 'Updated'
                self.stdout.write(f'  {status} skill category: {skill_category.name}')
                
                for skill_data in cat_data['skills']:
                    skill, skill_created = Skill.objects.update_or_create(
                        skill_category=skill_category,
                        name=skill_data['name'],
                        defaults={
                            'order': skill_data['order']
                        }
                    )
                    
                    if skill_created:
                        self.stdout.write(f'    Created skill: {skill.name}')

            # Create or update education entries
            for edu_data in data['education']:
                education, edu_created = Education.objects.update_or_create(
                    resume=resume,
                    title=edu_data['title'],
                    defaults={
                        'subtitle': edu_data['subtitle'],
                        'order': edu_data['order']
                    }
                )
                
                status = 'Created' if edu_created else 'Updated'
                self.stdout.write(f'  {status} education: {education.title}')

            self.stdout.write(
                self.style.SUCCESS(f'Successfully seeded resume data for {resume.title}')
            )

        except KeyError as e:
            self.stdout.write(
                self.style.ERROR(f'Missing required field in JSON: {e}')
            )
        except ValidationError as e:
            self.stdout.write(
                self.style.ERROR(f'Validation error: {e}')
            )
        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Unexpected error: {e}')
            )