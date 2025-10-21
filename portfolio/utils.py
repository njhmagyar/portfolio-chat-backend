import re
import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)

# Basic profanity word list (you can expand this)
PROFANITY_WORDS = {
    'damn', 'hell', 'crap', 'stupid', 'idiot', 'moron', 'dumb', 'suck', 'sucks',
    'hate', 'kill', 'die', 'death', 'murder', 'assault', 'attack', 'violence',
    'spam', 'scam', 'fraud', 'fake', 'bot', 'automated', 'fuck', 'shit', 'bitch',
    'bastard', 'ass', 'asshole', 'fag', 'faggot', 'cunt'
}

# Whitelist of acceptable words that contain flagged substrings
ACCEPTABLE_WORDS = {
    'skills', 'skilled', 'skillful', 'skillfully', 'skillet', 'skill',
    'classical', 'glasses', 'class', 'massage', 'assess', 'assessment',
    'assassin', 'assistance', 'assistant', 'passion', 'passionate'
}

def validate_message_content(message: str) -> Tuple[bool, str]:
    """
    Validate message content for abuse prevention.
    Returns (is_valid, error_message)
    """
    # Strip whitespace
    message = message.strip()
    
    # Length checks
    if len(message) < 3:
        return False, "Message too short (minimum 3 characters)"
    
    if len(message) > 500:
        return False, "Message too long (maximum 500 characters)"
    
    # Check for excessive special characters or repeated characters
    special_char_count = len(re.findall(r'[^a-zA-Z0-9\s\.\?\!\,\'\"]', message))
    if special_char_count > len(message) * 0.3:  # More than 30% special chars
        return False, "Message contains too many special characters"
    
    # Check for repeated characters (like "aaaaaaa")
    if re.search(r'(.)\1{4,}', message):  # 5 or more repeated characters
        return False, "Message contains excessive repeated characters"
    
    # Check for excessive caps
    if len(message) > 10:
        caps_ratio = sum(1 for c in message if c.isupper()) / len(message)
        if caps_ratio > 0.7:  # More than 70% caps
            return False, "Message contains excessive capital letters"
    
    # Basic profanity filter with whitelist check
    message_lower = message.lower()
    words_in_message = set(re.findall(r'\b\w+\b', message_lower))
    
    # Check if any message words are in the acceptable whitelist
    acceptable_found = words_in_message.intersection(ACCEPTABLE_WORDS)
    
    found_profanity = []
    for word in PROFANITY_WORDS:
        if word in message_lower:
            # Check if this profanity is part of an acceptable word
            is_part_of_acceptable = any(word in acceptable for acceptable in acceptable_found)
            if not is_part_of_acceptable:
                found_profanity.append(word)
    
    if found_profanity:
        logger.warning(f"Profanity detected in message: {found_profanity}")
        return False, "Message contains inappropriate content"
    
    # Check for spam patterns
    words = message.split()
    if len(words) > 3:
        unique_words = set(word.lower() for word in words)
        if len(unique_words) / len(words) < 0.5:  # Less than 50% unique words
            return False, "Message appears to be spam"
    
    return True, ""

def is_suspicious_pattern(message: str, previous_messages: List[str]) -> bool:
    """
    Check for suspicious patterns like repeated identical messages.
    """
    if not previous_messages:
        return False
    
    # Check if message is identical to any of the last 3 messages
    for prev_msg in previous_messages[-3:]:
        if message.strip().lower() == prev_msg.strip().lower():
            return True
    
    return False

def get_client_ip(request) -> str:
    """Get client IP address from request headers."""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '')
    return ip