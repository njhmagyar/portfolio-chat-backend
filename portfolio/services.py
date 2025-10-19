import json
import logging
from typing import List, Dict, Any
from django.conf import settings
from openai import OpenAI
from .models import Project, CaseStudy, Section

logger = logging.getLogger(__name__)


class PortfolioLLMService:
    """
    Service class for generating LLM responses based on portfolio data.
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
        self.model = "gpt-4o-mini"  # Using the more cost-effective model
    
    def get_portfolio_context(self) -> str:
        """
        Retrieve and format portfolio data as context for the LLM.
        """
        projects = Project.objects.all()
        context_parts = []
        
        for project in projects:
            project_context = f"""
PROJECT: {project.title}
Role: {project.role}
Timeline: {project.timeline}
Technologies: {', '.join(project.technologies)}
Summary: {project.summary}
Description: {project.description}
Featured: {'Yes' if project.featured else 'No'}
"""
            
            # Add case study information if available
            if hasattr(project, 'case_study'):
                case_study = project.case_study
                project_context += f"""
CASE STUDY:
Problem Statement: {case_study.problem_statement}
Category: {case_study.category}
Solution Overview: {case_study.solution_overview}
Impact Metrics: {json.dumps(case_study.impact_metrics)}
Lessons Learned: {case_study.lessons_learned}
Next Steps: {case_study.next_steps}
"""
                
                # Add sections
                sections = case_study.sections.all()
                if sections:
                    project_context += "\nSECTIONS:\n"
                    for section in sections:
                        project_context += f"- {section.title} ({section.section_type}): {section.content}\n"
            
            context_parts.append(project_context)
        
        return "\n" + "="*50 + "\n".join(context_parts)
    
    def generate_system_prompt(self) -> str:
        """
        Generate the system prompt with portfolio context.
        """
        portfolio_context = self.get_portfolio_context()
        
        return f"""You are Nathan Magyar, a seasoned product designer and developer with expertise in UX design, full-stack development, and product management. You're having a conversation about your portfolio and work experience.

PERSONALITY & TONE:
- Professional but conversational and approachable
- Confident in your abilities without being arrogant
- Passionate about solving user problems and building great products
- Detail-oriented when discussing technical implementations
- Always willing to share insights and lessons learned

PORTFOLIO CONTEXT:
{portfolio_context}

INSTRUCTIONS:
1. Answer questions about your projects, experience, and skills based on the portfolio data above
2. Keep all responses under 144 characters - be concise and direct
3. If asked about specific projects, mention key highlights and impact metrics
4. If asked about technologies, briefly mention your experience level
5. If asked about something not in your portfolio, politely redirect to what you can discuss
6. Keep responses conversational but brief
7. Always speak in first person as Nathan Magyar
8. Focus on the most important information first

Remember: You're representing Nathan's professional work and should provide helpful, accurate information about his portfolio and capabilities."""

    def generate_response(self, user_query: str) -> str:
        """
        Generate a response to the user's query using OpenAI's API.
        """
        try:
            system_prompt = self.generate_system_prompt()
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                max_tokens=250,
                temperature=0.7,
            )
            
            return response.choices[0].message.content.strip()
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return "I'm sorry, I'm having trouble processing your question right now. Could you please try again in a moment?"
    
    def get_project_by_category(self, category: str) -> List[Project]:
        """
        Helper method to get projects by category.
        """
        return Project.objects.filter(category__icontains=category)
    
    def get_featured_projects(self) -> List[Project]:
        """
        Helper method to get featured projects.
        """
        return Project.objects.filter(featured=True)
    
    def search_projects(self, query: str) -> List[Project]:
        """
        Helper method to search projects by title, summary, or technologies.
        """
        return Project.objects.filter(
            title__icontains=query
        ).union(
            Project.objects.filter(summary__icontains=query)
        ).union(
            Project.objects.filter(technologies__icontains=query)
        )