import json
import logging
from typing import List, Dict, Any
from django.conf import settings
from openai import OpenAI
from .models import Project, CaseStudy, Section, FAQ

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
            for case_study in project.case_studies.all():
                project_context += f"""
CASE STUDY:
Title: {case_study.title}
Category: {case_study.category}
Description: {case_study.description}
Hero Image: {case_study.hero_image or 'None'}
"""
                
                # Add sections
                sections = case_study.sections.all()
                if sections:
                    project_context += "\nSECTIONS:\n"
                    for section in sections:
                        project_context += f"- {section.title} ({section.section_type}): {section.content}\n"
            
            context_parts.append(project_context)
        
        return "\n" + "="*50 + "\n".join(context_parts)
    
    def get_faq_context(self) -> str:
        """
        Retrieve and format FAQ data as context for the LLM.
        """
        faqs = FAQ.objects.filter(is_active=True)[:20]  # Limit to 20 most relevant FAQs
        
        if not faqs:
            return ""
            
        faq_parts = []
        for faq in faqs:
            faq_context = f"""
Q: {faq.question}
A: {faq.response}"""
            
            # Add media URLs if available
            if faq.media_urls:
                media_list = ', '.join(faq.media_urls)
                faq_context += f"\nMedia: {media_list}"
            
            faq_parts.append(faq_context)
        
        if faq_parts:
            return "\n\nFREQUENTLY ASKED QUESTIONS:\n" + "="*50 + "\n".join(faq_parts)
        return ""
    
    def generate_system_prompt(self) -> str:
        """
        Generate the system prompt with portfolio context and FAQ data.
        """
        portfolio_context = self.get_portfolio_context()
        faq_context = self.get_faq_context()
        
        return f"""You are Nathan Magyar, a product designer and developer. You can ONLY answer questions based on the portfolio data and FAQ information provided below. Do not make up information or speculate.

PORTFOLIO CONTEXT:
{portfolio_context}{faq_context}

CRITICAL INSTRUCTIONS:
1. ONLY answer based on the portfolio data above - never invent or assume information
2. If the portfolio data doesn't contain information to answer a question, respond with: "Sorry, I don't have enough information in my portfolio to answer that question."
3. Always speak in first person as Nathan Magyar
4. Focus on facts from the portfolio data only

ACCEPTABLE TOPICS (only if data exists above):
- Specific projects and their details
- Technologies used in documented projects
- Roles and timelines from project data
- Case study titles, categories, and descriptions
- Section content from case studies (overview, context, research, design process, implementation, results, reflection)

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

    def generate_response(self, user_query: str, response_length: str = 'short') -> tuple[str, 'FAQ', list]:
        """
        Generate a response to the user's query using OpenAI's API.
        Returns tuple of (response_text, source_faq, follow_up_suggestions) where source_faq is None if no FAQ was used.
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
            
            response_text = response.choices[0].message.content.strip()
            
            # Check if the response matches any FAQ response to determine source
            source_faq = self._find_source_faq_for_response(response_text)
            
            # Generate follow-up suggestions
            follow_up_suggestions = self.generate_follow_up_suggestions(user_query, response_text)
            
            return response_text, source_faq, follow_up_suggestions
            
        except Exception as e:
            logger.error(f"Error generating LLM response: {str(e)}")
            return "I'm sorry, I'm having trouble processing your question right now. Could you please try again in a moment?", None, []
    
    def _find_source_faq_for_response(self, response_text: str):
        """
        Find the FAQ that was used as the source for this response.
        Uses only exact matching to avoid incorrect audio reuse.
        """
        try:
            # Clean the response text for comparison (normalize whitespace)
            cleaned_response = ' '.join(response_text.split()).strip()
            
            # Only use exact match - no fuzzy matching to avoid false positives
            exact_match = FAQ.objects.filter(
                response__iexact=cleaned_response,
                is_active=True
            ).first()
            
            if exact_match:
                logger.info(f"Found exact FAQ match {exact_match.id} for LLM response")
                return exact_match
            
            # No exact match found - do not reuse audio
            return None
            
        except Exception as e:
            logger.error(f"Error finding source FAQ for response: {str(e)}")
            return None
    
    def generate_follow_up_suggestions(self, user_query: str, response_text: str) -> list:
        """
        Generate 2-3 follow-up suggestions based on the user's query and response.
        """
        try:
            # Create a simple prompt for generating follow-up suggestions
            follow_up_prompt = f"""Based on this conversation, suggest 2 brief follow-up questions that would naturally continue the conversation about the same project. Use the project name in the question. Then, create a third question. It can be about a different project, referenced specifcally by name, or a more general question about Nathan's skills, experience, technologies, or process details.

User asked: "{user_query}"
Response given: "{response_text[:300]}..."

Generate 2-3 short, specific follow-up questions (one per line, no numbers or bullets). Each should be under 60 characters."""

            follow_up_response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are helping generate natural follow-up questions for a portfolio conversation. Keep questions concise and relevant."},
                    {"role": "user", "content": follow_up_prompt}
                ],
                max_tokens=150,
                temperature=0.8,
            )
            
            # Parse the response into individual suggestions
            suggestions_text = follow_up_response.choices[0].message.content.strip()
            suggestions = [s.strip() for s in suggestions_text.split('\n') if s.strip()]
            
            # Limit to 3 suggestions and ensure they're not too long
            suggestions = [s for s in suggestions[:3] if len(s) <= 80 and s.endswith('?')]
            
            # Fallback suggestions if generation fails or produces poor results
            if not suggestions:
                suggestions = self._get_fallback_suggestions(user_query)
            
            return suggestions
            
        except Exception as e:
            logger.error(f"Error generating follow-up suggestions: {str(e)}")
            return self._get_fallback_suggestions(user_query)
    
    def _get_fallback_suggestions(self, user_query: str) -> list:
        """
        Generate fallback follow-up suggestions based on common portfolio topics.
        """
        # Categorize the query and provide relevant follow-ups
        query_lower = user_query.lower()
        
        if any(word in query_lower for word in ['project', 'work', 'built', 'created']):
            return [
                "What technologies did you use for this project?",
                "What challenges did you face during development?",
                "How long did this project take to complete?"
            ]
        elif any(word in query_lower for word in ['skill', 'technology', 'tech', 'language']):
            return [
                "What projects showcase these skills best?",
                "How did you learn these technologies?",
                "What's your preferred tech stack?"
            ]
        elif any(word in query_lower for word in ['design', 'ux', 'ui', 'user']):
            return [
                "What's your design process like?",
                "How do you approach user research?",
                "What design tools do you prefer?"
            ]
        else:
            return [
                "What projects are you most proud of?",
                "What technologies do you enjoy working with?",
                "What's your development process like?"
            ]
    
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