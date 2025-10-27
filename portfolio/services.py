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
        
        return f"""You are Nathan Magyar, a product designer and developer. You can ONLY answer questions based on the portfolio data provided below. Do not make up information or speculate.

PORTFOLIO CONTEXT:
{portfolio_context}

CRITICAL INSTRUCTIONS:
1. ONLY answer based on the portfolio data above - never invent or assume information
2. If the portfolio data doesn't contain information to answer a question, respond with: "Sorry, I don't have enough information in my portfolio to answer that question."
3. Always speak in first person as Nathan Magyar
4. Focus on facts from the portfolio data only

ACCEPTABLE TOPICS (only if data exists above):
- Specific projects and their details
- Technologies used in documented projects
- Roles and timelines from project data
- Impact metrics and outcomes shown in portfolio
- Problem statements and solutions from case studies

UNACCEPTABLE: Any information not explicitly stated in the portfolio context above.

Remember: Accuracy over helpfulness. If you don't have the specific information in the portfolio data, say so rather than guessing."""

    def get_token_limit_for_length(self, response_length: str) -> int:
        """
        Get appropriate token limit based on response length preference.
        """
        token_limits = {
            'short': 200,   # ~50-75 words
            'medium': 300,  # ~75-100 words  
            'long': 400     # ~100-150 words
        }
        return token_limits.get(response_length, 200)
    
    def get_length_instruction(self, response_length: str) -> str:
        """
        Get response length instruction for the system prompt.
        """
        instructions = {
            'short': "Keep responses very brief - 1-2 sentences maximum.",
            'medium': "Provide a moderate response - 2-4 sentences with key details.",
            'long': "Give a comprehensive response with full details, examples, and context."
        }
        return instructions.get(response_length, instructions['short'])

    def generate_response(self, user_query: str, response_length: str = 'short') -> str:
        """
        Generate a response to the user's query using OpenAI's API.
        """
        try:
            system_prompt = self.generate_system_prompt()
            length_instruction = self.get_length_instruction(response_length)
            
            # Add length instruction to system prompt
            system_prompt += f"\n\nRESPONSE LENGTH: {length_instruction}"
            
            token_limit = self.get_token_limit_for_length(response_length)
            
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_query}
                ],
                max_tokens=token_limit,
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