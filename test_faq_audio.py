#!/usr/bin/env python

import os
import sys
import django

# Setup Django environment
sys.path.append('/Users/njhmagyar/Documents/chat-nhm/backend')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'portfolio_backend.settings')
django.setup()

from portfolio.models import FAQ
from portfolio.voice_service import VoiceService

def test_faq_audio():
    print("=== FAQ Audio Test ===")
    
    # Check if we have any existing FAQs
    print("\nExisting FAQs:")
    for faq in FAQ.objects.all():
        print(f"ID: {faq.id}, Question: {faq.question[:50]}..., Has Audio: {faq.has_audio}")
    
    # Create a test FAQ
    print("\nCreating test FAQ...")
    test_faq = FAQ.objects.create(
        question="What is your favorite programming language?",
        response="My favorite programming language is Python because it's versatile, readable, and has an amazing ecosystem for web development, data science, and automation.",
        is_featured=True,
        priority=100
    )
    
    print(f"Created test FAQ: {test_faq.id}")
    print(f"Has audio after creation: {test_faq.has_audio}")
    
    if test_faq.has_audio:
        print(f"Audio file: {test_faq.audio_file.name}")
        print(f"Audio generation time: {test_faq.audio_generation_time_ms}ms")
    else:
        print("No audio was generated automatically")
        
        # Try to generate audio manually
        print("\nTrying to generate audio manually...")
        voice_service = VoiceService()
        success = voice_service.generate_and_save_audio_for_faq(test_faq)
        
        if success:
            print("Manual audio generation successful!")
            test_faq.refresh_from_db()
            print(f"Audio file: {test_faq.audio_file.name}")
            print(f"Audio generation time: {test_faq.audio_generation_time_ms}ms")
        else:
            print("Manual audio generation failed")
    
    # Test featured questions API response
    print("\n=== Testing Featured Questions API Response ===")
    from portfolio.views import featured_questions
    from django.test import RequestFactory
    
    factory = RequestFactory()
    request = factory.get('/api/featured-questions/')
    
    response = featured_questions(request)
    import json
    data = json.loads(response.content)
    
    print(f"API Response:")
    print(f"Source: {data['source']}")
    print(f"Count: {data['count']}")
    print(f"Questions structure:")
    
    for i, question in enumerate(data['questions']):
        print(f"  {i+1}. Question: {question['question'][:50]}...")
        print(f"     Has Audio: {question['has_audio']}")
        if question['audio_url']:
            print(f"     Audio URL: {question['audio_url']}")
        print()

if __name__ == "__main__":
    test_faq_audio()