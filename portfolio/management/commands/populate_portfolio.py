from django.core.management.base import BaseCommand
from portfolio.models import Project, CaseStudy, Section


class Command(BaseCommand):
    help = 'Populate portfolio with sample data'

    def handle(self, *args, **options):
        self.stdout.write('Creating sample portfolio data...')
        
        # Create E-commerce Mobile App project
        ecommerce_project, created = Project.objects.get_or_create(
            slug='ecommerce-mobile-app',
            defaults={
                'title': 'E-commerce Mobile App',
                'summary': 'Redesigned mobile checkout flow increasing conversion by 23%',
                'description': 'Led the complete redesign of the mobile checkout experience for a major e-commerce platform. Conducted user research, created prototypes, and collaborated with engineering to implement a streamlined 3-step checkout process.',
                'category': 'design',
                'role': 'Lead UX Designer',
                'timeline': '6 months',
                'technologies': ['Figma', 'React Native', 'Firebase', 'Analytics'],
                'emoji': '📱',
                'featured': True
            }
        )
        
        if created:
            # Create case study for e-commerce project
            ecommerce_case_study = CaseStudy.objects.create(
                project=ecommerce_project,
                problem_statement='Users were abandoning their carts at a rate of 70% during the mobile checkout process. The existing flow had too many steps, required excessive form input, and had poor visual hierarchy.',
                solution_overview='Redesigned the checkout flow from 7 steps down to 3, implemented smart form autofill, and created a progress indicator system. Focused on single-task screens and reduced cognitive load.',
                impact_metrics=[
                    {"metric": "Conversion Rate", "value": "+23%"},
                    {"metric": "Cart Abandonment", "value": "-45%"},
                    {"metric": "Checkout Time", "value": "-60%"}
                ],
                lessons_learned='The importance of testing with actual users on real devices. What works on desktop rarely translates directly to mobile without significant adaptation.',
                next_steps='Implement personalized payment options based on user history and location. A/B test one-click checkout for returning customers.'
            )
            
            # Create sections for the case study
            Section.objects.create(
                case_study=ecommerce_case_study,
                title='User Research & Problem Discovery',
                section_type='research',
                content='Conducted 15 user interviews and analyzed analytics data from 50,000 checkout sessions. Key findings: Users struggled with form validation, payment method selection was confusing, and the progress indicator was misleading.',
                order=1
            )
            
            Section.objects.create(
                case_study=ecommerce_case_study,
                title='Design Process & Prototyping',
                section_type='design',
                content='Created low-fidelity wireframes focusing on information hierarchy. Developed high-fidelity prototypes in Figma with micro-interactions. Conducted 3 rounds of usability testing with 8 users each.',
                order=2
            )
            
            Section.objects.create(
                case_study=ecommerce_case_study,
                title='Results & Impact',
                section_type='results',
                content='Post-launch metrics showed significant improvement across all KPIs. The redesigned checkout flow became the template for the companys desktop experience as well.',
                order=3
            )

        # Create Portfolio Chat Platform project
        chat_project, created = Project.objects.get_or_create(
            slug='portfolio-chat-platform',
            defaults={
                'title': 'Portfolio Chat Platform',
                'summary': 'AI-powered conversational portfolio with voice cloning',
                'description': 'Built this conversational portfolio platform using Django, Vue.js, and OpenAI. Features include voice cloning, RAG-powered content retrieval, and dynamic case study generation.',
                'category': 'development',
                'role': 'Full-Stack Developer',
                'timeline': '3 months',
                'technologies': ['Django', 'Vue.js', 'OpenAI', 'PostgreSQL', 'Heroku'],
                'emoji': '🤖',
                'featured': True
            }
        )
        
        if created:
            # Create case study for chat platform
            chat_case_study = CaseStudy.objects.create(
                project=chat_project,
                problem_statement='Traditional portfolios are static and dont engage visitors. Recruiters and clients often want to understand the thought process behind projects, not just see the final results.',
                solution_overview='Created an AI-powered conversational interface that can discuss any project in detail, using RAG (Retrieval Augmented Generation) to provide accurate, context-aware responses about my work.',
                impact_metrics=[
                    {"metric": "User Engagement", "value": "+300%"},
                    {"metric": "Session Duration", "value": "+150%"},
                    {"metric": "Return Visitors", "value": "+80%"}
                ],
                lessons_learned='The importance of training data quality in RAG systems. Spent significant time curating and structuring project content for better AI responses.',
                next_steps='Add multi-language support and integrate with calendar for automatic meeting scheduling based on project discussions.'
            )

        # Create SaaS Dashboard project
        saas_project, created = Project.objects.get_or_create(
            slug='saas-dashboard-redesign',
            defaults={
                'title': 'SaaS Dashboard Redesign',
                'summary': 'Improved user engagement and reduced support tickets by 40%',
                'description': 'Redesigned the main dashboard for a B2B SaaS platform serving 10k+ users. Focused on information hierarchy, data visualization, and mobile responsiveness.',
                'category': 'design',
                'role': 'Senior Product Designer',
                'timeline': '4 months',
                'technologies': ['Sketch', 'InVision', 'D3.js', 'React'],
                'emoji': '📊',
                'featured': False
            }
        )

        # Create Product Roadmap Tool project
        roadmap_project, created = Project.objects.get_or_create(
            slug='product-roadmap-tool',
            defaults={
                'title': 'Product Roadmap Tool',
                'summary': 'Internal tool for managing product roadmaps across teams',
                'description': 'Managed the development of an internal roadmap planning tool. Coordinated with stakeholders, defined requirements, and oversaw the product launch to 200+ team members.',
                'category': 'product',
                'role': 'Product Manager',
                'timeline': '8 months',
                'technologies': ['Jira', 'Confluence', 'React', 'Node.js'],
                'emoji': '🗺️',
                'featured': False
            }
        )

        self.stdout.write(
            self.style.SUCCESS('Successfully populated portfolio with sample data!')
        )