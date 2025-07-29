"""
Prayer Categorization Service

This service handles AI-powered and fallback categorization of prayers for
safety filtering, specificity classification, and subject categorization.
Integrates with the archive-first architecture.
"""

import json
import logging
from typing import Dict, List, Optional
from datetime import datetime
import os

logger = logging.getLogger(__name__)

# Import feature flags
try:
    from app import (
        PRAYER_CATEGORIZATION_ENABLED,
        AI_CATEGORIZATION_ENABLED, 
        KEYWORD_FALLBACK_ENABLED,
        CATEGORIZATION_CIRCUIT_BREAKER_ENABLED,
        SAFETY_SCORING_ENABLED,
        CATEGORIZATION_CACHING_ENABLED
    )
except ImportError:
    # Fallback for testing or standalone usage
    PRAYER_CATEGORIZATION_ENABLED = os.getenv("PRAYER_CATEGORIZATION_ENABLED", "false").lower() == "true"
    AI_CATEGORIZATION_ENABLED = os.getenv("AI_CATEGORIZATION_ENABLED", "false").lower() == "true"
    KEYWORD_FALLBACK_ENABLED = os.getenv("KEYWORD_FALLBACK_ENABLED", "false").lower() == "true"
    CATEGORIZATION_CIRCUIT_BREAKER_ENABLED = os.getenv("CATEGORIZATION_CIRCUIT_BREAKER_ENABLED", "false").lower() == "true"
    SAFETY_SCORING_ENABLED = os.getenv("SAFETY_SCORING_ENABLED", "false").lower() == "true"
    CATEGORIZATION_CACHING_ENABLED = os.getenv("CATEGORIZATION_CACHING_ENABLED", "false").lower() == "true"

# Default categorization for fallback scenarios
DEFAULT_CATEGORIZATION = {
    'safety_score': 1.0,  # Assume safe if analysis fails
    'specificity_type': 'unknown',
    'subject_category': 'general',
    'safety_flags': [],
    'categorization_method': 'default_fallback',
    'categorization_confidence': 0.0
}

# Keyword mapping for subject categorization fallback
SUBJECT_KEYWORDS = {
    'health': ['healing', 'surgery', 'doctor', 'illness', 'recovery', 'medical', 'hospital', 'medicine', 'sick', 'pain'],
    'relationships': ['family', 'marriage', 'friend', 'children', 'spouse', 'relationship', 'love', 'wedding', 'divorce'],
    'work': ['job', 'career', 'workplace', 'employment', 'business', 'interview', 'promotion', 'work', 'boss'],
    'spiritual': ['faith', 'ministry', 'discipleship', 'spiritual', 'church', 'worship', 'baptism', 'communion', 'salvation'],
    'provision': ['financial', 'money', 'job', 'income', 'resources', 'bills', 'debt', 'poverty', 'needs'],
    'protection': ['safety', 'travel', 'protection', 'security', 'danger', 'accident', 'harm', 'violence'],
    'guidance': ['decision', 'wisdom', 'direction', 'choice', 'guidance', 'confused', 'uncertain', 'path'],
    'gratitude': ['thank', 'grateful', 'praise', 'blessing', 'celebrate', 'joy', 'appreciation', 'thankful'],
    'crisis': ['emergency', 'urgent', 'crisis', 'disaster', 'tragedy', 'sudden', 'critical', 'immediate'],
    'transitions': ['birth', 'death', 'marriage', 'move', 'graduation', 'retirement', 'change', 'new']
}

class PrayerCategorizationService:
    """Service for categorizing prayers with multiple fallback strategies"""
    
    def __init__(self):
        if CATEGORIZATION_CIRCUIT_BREAKER_ENABLED:
            self.circuit_breaker = CategorizationCircuitBreaker()
        else:
            self.circuit_breaker = None
    
    def categorize_prayer_with_fallback(self, prayer_text: str, ai_response: str = None) -> dict:
        """Categorize prayer with multiple fallback strategies"""
        
        # Check if categorization is enabled at all
        if not PRAYER_CATEGORIZATION_ENABLED:
            return DEFAULT_CATEGORIZATION
            
        # Strategy 1: Parse AI response if provided and AI categorization enabled
        if ai_response and AI_CATEGORIZATION_ENABLED and (not self.circuit_breaker or self.circuit_breaker.should_attempt_ai_categorization()):
            try:
                categories = self.parse_ai_categorization(ai_response)
                if self.validate_categorization(categories):
                    if self.circuit_breaker:
                        self.circuit_breaker.record_attempt(True)
                    categories['categorization_method'] = 'ai_full'
                    return categories
            except Exception as e:
                logger.warning(f"AI categorization parsing failed: {e}")
                if self.circuit_breaker:
                    self.circuit_breaker.record_attempt(False)
        
        # Strategy 2: Keyword-based fallback (if enabled)
        if KEYWORD_FALLBACK_ENABLED:
            try:
                categories = self.keyword_based_categorization(prayer_text)
                categories['categorization_method'] = 'keyword_fallback'
                logger.info(f"Using keyword fallback categorization for prayer")
                return categories
            except Exception as e:
                logger.error(f"Keyword fallback failed: {e}")
        
        # Strategy 3: Safe defaults
        logger.warning("Using default fallback categorization")
        return {**DEFAULT_CATEGORIZATION, 'categorization_method': 'default_fallback'}
    
    def keyword_based_categorization(self, prayer_text: str) -> dict:
        """Simple keyword matching for categorization"""
        text_lower = prayer_text.lower()
        
        # Find best matching subject category
        subject_scores = {}
        for category, keywords in SUBJECT_KEYWORDS.items():
            score = sum(1 for keyword in keywords if keyword in text_lower)
            if score > 0:
                subject_scores[category] = score
        
        subject_category = max(subject_scores, key=subject_scores.get) if subject_scores else 'general'
        
        # Simple specificity detection - look for capitalized names
        words = prayer_text.split()
        has_names = any(word[0].isupper() and len(word) > 2 and word.isalpha() for word in words)
        specificity = 'specific' if has_names else 'general'
        
        result = {
            'specificity_type': specificity,
            'subject_category': subject_category,
            'specificity_confidence': 0.6,  # Lower confidence for keyword matching
            'categorization_confidence': 0.6
        }
        
        # Only add safety scoring if enabled
        if SAFETY_SCORING_ENABLED:
            result['safety_score'] = 1.0  # Keywords assume safe content
            result['safety_flags'] = []
        else:
            result['safety_score'] = 1.0  # Default safe
            result['safety_flags'] = []
        
        return result
    
    def parse_ai_categorization(self, response_text: str) -> dict:
        """Extract categorization data from AI response"""
        lines = response_text.split('\n')
        categories = {}
        
        for line in lines:
            line = line.strip()
            if ':' not in line:
                continue
                
            key, value = line.split(':', 1)
            key = key.strip().upper()
            value = value.strip()
            
            try:
                if key == 'SAFETY_SCORE':
                    categories['safety_score'] = float(value)
                elif key == 'SPECIFICITY':
                    categories['specificity_type'] = value.lower()
                elif key == 'SUBJECT':
                    categories['subject_category'] = value.lower()
                elif key == 'CONFIDENCE':
                    categories['categorization_confidence'] = float(value)
                elif key == 'SAFETY_FLAGS':
                    categories['safety_flags'] = json.loads(value) if value != '[]' else []
            except (ValueError, json.JSONDecodeError) as e:
                logger.warning(f"Failed to parse categorization field {key}: {e}")
                continue
        
        return categories
    
    def validate_categorization(self, categories: dict) -> bool:
        """Validate that categorization contains required fields with valid values"""
        required_fields = ['safety_score', 'specificity_type', 'subject_category']
        
        for field in required_fields:
            if field not in categories:
                return False
        
        # Validate safety score range
        if not (0.0 <= categories['safety_score'] <= 1.0):
            return False
        
        # Validate specificity type
        valid_specificity = ['specific', 'general', 'mixed', 'unknown']
        if categories['specificity_type'] not in valid_specificity:
            return False
        
        # Validate subject category
        valid_subjects = list(SUBJECT_KEYWORDS.keys()) + ['general', 'other']
        if categories['subject_category'] not in valid_subjects:
            return False
        
        return True


class CategorizationCircuitBreaker:
    """Circuit breaker to disable AI categorization when failure rate is high"""
    
    def __init__(self, failure_threshold=0.2, cooldown_minutes=15):
        self.failure_threshold = failure_threshold
        self.cooldown_minutes = cooldown_minutes
        self.failure_count = 0
        self.total_attempts = 0
        self.last_failure_time = None
        self.is_open = False
    
    def should_attempt_ai_categorization(self) -> bool:
        """Check if AI categorization should be attempted"""
        if not self.is_open:
            return True
        
        # Check if cooldown period has passed
        if (self.last_failure_time and 
            datetime.now().timestamp() - self.last_failure_time.timestamp() > self.cooldown_minutes * 60):
            self.is_open = False
            self.failure_count = 0
            self.total_attempts = 0
            logger.info("Circuit breaker reset - resuming AI categorization attempts")
            return True
        
        return False
    
    def record_attempt(self, success: bool):
        """Record the result of a categorization attempt"""
        self.total_attempts += 1
        
        if not success:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
        
        # Open circuit if failure rate exceeds threshold
        if self.total_attempts >= 10:  # Minimum attempts before evaluation
            failure_rate = self.failure_count / self.total_attempts
            if failure_rate > self.failure_threshold:
                self.is_open = True
                logger.warning(f"Circuit breaker opened - AI categorization disabled due to {failure_rate:.1%} failure rate")