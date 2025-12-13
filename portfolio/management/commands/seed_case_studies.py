import json
import os
from django.core.management.base import BaseCommand
from django.core.exceptions import ValidationError
from portfolio.models import Project, CaseStudy, Section, Metric


class Command(BaseCommand):
    help = 'Idempotently seed case study data from JSON fixture'

    def add_arguments(self, parser):
        parser.add_argument(
            '--fixture',
            type=str,
            default='case_studies.json',
            help='JSON fixture file name (default: case_studies.json)'
        )

    def handle(self, *args, **options):
        fixture_file = options['fixture']
        fixture_path = os.path.join('portfolio', 'fixtures', fixture_file)
        
        if not os.path.exists(fixture_path):
            self.stdout.write(
                self.style.ERROR(f'Fixture file not found: {fixture_path}')
            )
            return

        with open(fixture_path, 'r') as f:
            data = json.load(f)

        try:
            for case_study_data in data['case_studies']:
                # Get the project by slug
                project_slug = case_study_data['project_slug']
                try:
                    project = Project.objects.get(slug=project_slug)
                except Project.DoesNotExist:
                    self.stdout.write(
                        self.style.ERROR(f'Project with slug "{project_slug}" not found. Skipping case study.')
                    )
                    continue

                # Create or update case study
                case_study, created = CaseStudy.objects.update_or_create(
                    project=project,
                    slug=case_study_data.get('slug'),
                    defaults={
                        'category': case_study_data['category'],
                        'hero_image': case_study_data.get('hero_image', ''),
                        'title': case_study_data.get('title', ''),
                        'description': case_study_data['description']
                    }
                )
                
                status = 'Created' if created else 'Updated'
                self.stdout.write(
                    self.style.SUCCESS(f'{status} case study: {case_study.title or case_study.project.title}')
                )

                # Create or update metrics
                if 'metrics' in case_study_data:
                    # Clear existing metrics to avoid duplicates
                    case_study.metrics.all().delete()
                    
                    for metric_data in case_study_data['metrics']:
                        metric, created = Metric.objects.update_or_create(
                            case_study=case_study,
                            value=metric_data['value'],
                            label=metric_data['label'],
                            defaults={
                                'order': metric_data.get('order', 0)
                            }
                        )
                        status = 'Created' if created else 'Updated'
                        self.stdout.write(f'  {status} metric: {metric.value} {metric.label}')

                # Create or update sections
                for section_data in case_study_data['sections']:
                    section, section_created = Section.objects.update_or_create(
                        case_study=case_study,
                        section_type=section_data['section_type'],
                        defaults={
                            'title': section_data['title'],
                            'content': section_data['content'],
                            'context': section_data.get('context', ''),
                            'order': section_data['order'],
                            'media_urls': section_data.get('media_urls', [])
                        }
                    )
                    
                    section_status = 'Created' if section_created else 'Updated'
                    self.stdout.write(f'  {section_status} section: {section.title}')

            self.stdout.write(
                self.style.SUCCESS('Successfully seeded case study data')
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