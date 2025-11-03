import logging
import re
from typing import Dict, Tuple, Optional
from django.conf import settings
from openai import OpenAI

logger = logging.getLogger(__name__)


class SlideService:
    """
    Service class for generating slide content from user queries and AI responses.
    """
    
    def __init__(self):
        self.client = OpenAI(api_key=settings.OPENAI_API_KEY)
    
    def generate_slide_content(self, user_query: str, ai_response: str) -> Tuple[str, str]:
        """
        Generate slide title and HTML body content based on user query and AI response.
        Returns (slide_title, slide_body_html)
        """
        try:
            # Generate slide content using GPT
            slide_prompt = self._build_slide_prompt(user_query, ai_response)
            
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a presentation expert. Generate concise, professional slide content."
                    },
                    {
                        "role": "user", 
                        "content": slide_prompt
                    }
                ],
                max_tokens=300,
                temperature=0.3
            )
            
            slide_content = response.choices[0].message.content.strip()
            return self._parse_slide_content(slide_content)
            
        except Exception as e:
            logger.error(f"Error generating slide content: {str(e)}")
            # Fallback to simple extraction
            return self._fallback_slide_generation(user_query, ai_response)
    
    def _build_slide_prompt(self, user_query: str, ai_response: str) -> str:
        """Build the prompt for slide generation."""
        return f"""
Based on this conversation:

User Question: "{user_query}"
AI Response: "{ai_response}"

Generate slide content in this exact format:

TITLE: [Create a concise, professional slide title (max 50 characters)]
BODY:
- [First key point from the response]
- [Second key point from the response]
- [Third key point from the response]
- [Fourth key point if applicable]

Rules:
1. Title should be clear and relevant to the user's question
2. Use 3-4 bullet points maximum
3. Each bullet should be 10-15 words
4. Focus on the most important information
5. Use professional, portfolio-appropriate language

Example:
TITLE: My Key Projects
BODY:
- Michigan Online: Educational platform development
- Twirlmate: Social networking app for dancers  
- Codespec: Technical documentation tool
"""
    
    def _parse_slide_content(self, content: str) -> Tuple[str, str]:
        """Parse the GPT response into title and HTML body."""
        try:
            lines = content.strip().split('\n')
            title = ""
            body_lines = []
            
            in_body = False
            for line in lines:
                line = line.strip()
                if line.startswith('TITLE:'):
                    title = line.replace('TITLE:', '').strip()
                elif line.startswith('BODY:'):
                    in_body = True
                elif in_body and line.startswith('-'):
                    # Clean up the bullet point
                    bullet = line[1:].strip()
                    if bullet:
                        body_lines.append(bullet)
            
            # Convert to HTML
            if body_lines:
                html_body = '<ul class="slide-bullets">\n'
                for bullet in body_lines:
                    html_body += f'  <li>{bullet}</li>\n'
                html_body += '</ul>'
            else:
                html_body = '<p>Key information from conversation</p>'
            
            return title or self._extract_title_from_query(user_query), html_body
            
        except Exception as e:
            logger.error(f"Error parsing slide content: {str(e)}")
            return self._fallback_slide_generation(user_query, ai_response)
    
    def _fallback_slide_generation(self, user_query: str, ai_response: str) -> Tuple[str, str]:
        """Fallback method for slide generation when GPT fails."""
        # Generate title from query
        title = self._extract_title_from_query(user_query)
        
        # Extract key points from response
        sentences = [s.strip() for s in ai_response.split('.') if s.strip()]
        
        # Create bullet points from key sentences
        bullets = []
        for sentence in sentences[:4]:  # Max 4 bullets
            if len(sentence) > 15 and len(sentence) < 100:
                # Clean up the sentence
                clean_sentence = re.sub(r'^(I|I\'ve|I have|My|The|A)\s+', '', sentence, flags=re.IGNORECASE)
                clean_sentence = clean_sentence.strip()
                if clean_sentence:
                    bullets.append(clean_sentence)
        
        # If no good bullets found, use a generic one
        if not bullets:
            bullets = ["Key portfolio information", "Professional experience highlights"]
        
        # Convert to HTML
        html_body = '<ul class="slide-bullets">\n'
        for bullet in bullets:
            html_body += f'  <li>{bullet}</li>\n'
        html_body += '</ul>'
        
        return title, html_body
    
    def _extract_title_from_query(self, query: str) -> str:
        """Extract a slide title from the user query."""
        query = query.strip().lower()
        
        # Common query patterns and their titles
        title_patterns = {
            r'what projects.*work': 'My Projects',
            r'what.*skills': 'My Skills',
            r'tell me about.*experience': 'My Experience', 
            r'what.*background': 'My Background',
            r'what.*education': 'My Education',
            r'design process': 'My Design Process',
            r'what.*tools': 'Tools & Technologies',
            r'what.*achievements': 'Key Achievements',
            r'what.*roles': 'Professional Roles',
            r'what.*companies': 'Work Experience',
        }
        
        for pattern, title in title_patterns.items():
            if re.search(pattern, query):
                return title
        
        # Generic fallback
        return 'Portfolio Information'
    
    def generate_slide_for_message(self, message_obj) -> bool:
        """
        Generate slide content for an AI response message.
        Returns True if successful, False otherwise.
        """
        try:
            # Only generate slides for AI responses
            if message_obj.message_type != 'ai_response':
                return False
            
            # Skip if slide content already exists
            if message_obj.slide_title and message_obj.slide_body:
                logger.info(f"Slide content already exists for message {message_obj.id}")
                return True
            
            # Get the corresponding user query
            user_message = message_obj.conversation.messages.filter(
                message_type='user_query',
                order_in_session=message_obj.order_in_session - 1
            ).first()
            
            if not user_message:
                logger.warning(f"No user query found for AI response {message_obj.id}")
                return False
            
            # Generate slide content
            slide_title, slide_body = self.generate_slide_content(
                user_message.content, 
                message_obj.content
            )
            
            # Extract relevant media from case study sections
            media_urls = self.extract_relevant_media(user_message.content, message_obj.content)
            
            # Save to message
            message_obj.slide_title = slide_title
            message_obj.slide_body = slide_body
            message_obj.slide_media_urls = media_urls
            message_obj.save(update_fields=['slide_title', 'slide_body', 'slide_media_urls'])
            
            logger.info(f"Generated slide content for message {message_obj.id}: '{slide_title}' with {len(media_urls)} media items")
            return True
            
        except Exception as e:
            logger.error(f"Error generating slide for message {message_obj.id}: {str(e)}")
            return False
    
    def extract_relevant_media(self, user_query: str, ai_response: str) -> list:
        """
        Extract relevant media URLs from case study sections based on the conversation context.
        """
        try:
            from .models import Project, CaseStudy, Section
            
            media_urls = []
            query_lower = user_query.lower()
            response_lower = ai_response.lower()
            
            # Search for projects mentioned in the response or query
            projects = Project.objects.all()
            relevant_projects = []
            
            for project in projects:
                # Check if project is mentioned by name
                if (project.title.lower() in response_lower or 
                    project.title.lower() in query_lower or
                    any(tech.lower() in response_lower for tech in project.technologies if isinstance(tech, str))):
                    relevant_projects.append(project)
            
            # If no specific projects found, look for keyword matches
            if not relevant_projects:
                # Look for general topic matches
                if any(word in query_lower for word in ['design', 'ui', 'ux', 'interface']):
                    relevant_projects = projects.filter(case_study__category='design')[:2]
                elif any(word in query_lower for word in ['development', 'code', 'programming', 'tech']):
                    relevant_projects = projects.filter(case_study__category='development')[:2]
                elif any(word in query_lower for word in ['project', 'work', 'portfolio']):
                    relevant_projects = projects.filter(featured=True)[:3]
            
            # Extract media from relevant projects' case study sections
            for project in relevant_projects:
                for case_study in project.case_studies.all():
                    # Add hero image if available
                    if case_study.hero_image:
                        media_urls.append(case_study.hero_image)
                    
                    # Add media from sections (prioritize certain section types)
                    sections = case_study.sections.all()
                    
                    # Prioritize visual sections
                    priority_sections = sections.filter(
                        section_type__in=['design', 'results', 'implementation']
                    )
                    
                    for section in priority_sections:
                        if section.media_urls:
                            # Add up to 2 media items per section to avoid overwhelming
                            media_urls.extend(section.media_urls[:2])
                    
                    # If we don't have enough media, add from other sections
                    if len(media_urls) < 3:
                        other_sections = sections.exclude(
                            section_type__in=['design', 'results', 'implementation']
                        )
                        for section in other_sections:
                            if section.media_urls and len(media_urls) < 5:
                                media_urls.extend(section.media_urls[:1])
            
            # Remove duplicates while preserving order
            seen = set()
            unique_media = []
            for url in media_urls:
                if url and url not in seen:
                    seen.add(url)
                    unique_media.append(url)
            
            # Limit to 5 images max for performance
            return unique_media[:5]
            
        except Exception as e:
            logger.error(f"Error extracting media for slide: {str(e)}")
            return []