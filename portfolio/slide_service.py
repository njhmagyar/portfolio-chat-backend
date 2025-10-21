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
            
            # Save to message
            message_obj.slide_title = slide_title
            message_obj.slide_body = slide_body
            message_obj.save(update_fields=['slide_title', 'slide_body'])
            
            logger.info(f"Generated slide content for message {message_obj.id}: '{slide_title}'")
            return True
            
        except Exception as e:
            logger.error(f"Error generating slide for message {message_obj.id}: {str(e)}")
            return False