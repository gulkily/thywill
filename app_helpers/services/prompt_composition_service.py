"""
Prompt Composition Service - Dynamic Prayer Generation Prompt Building

Composes prayer generation prompts from modular text files based on feature flags.
Maintains auditability by keeping all prompt text in version-controlled files.
"""

import os
from pathlib import Path
from typing import List, Optional

try:
    from app import (
        PRAYER_CATEGORIZATION_ENABLED,
        AI_CATEGORIZATION_ENABLED, 
        SAFETY_SCORING_ENABLED
    )
except ImportError:
    # Fallback for testing or standalone usage
    PRAYER_CATEGORIZATION_ENABLED = os.getenv("PRAYER_CATEGORIZATION_ENABLED", "false").lower() == "true"
    AI_CATEGORIZATION_ENABLED = os.getenv("AI_CATEGORIZATION_ENABLED", "false").lower() == "true"
    SAFETY_SCORING_ENABLED = os.getenv("SAFETY_SCORING_ENABLED", "false").lower() == "true"


class PromptCompositionService:
    """Service for composing dynamic prayer generation prompts from modular text files"""
    
    def __init__(self):
        self.prompts_dir = Path(__file__).parent.parent.parent / "prompts"
        self._validate_prompt_files()
    
    def _validate_prompt_files(self):
        """Ensure all required prompt files exist"""
        required_files = [
            "prayer_generation_system.txt",
            "prayer_categorization_request_analysis.txt",
            "prayer_categorization_verification.txt", 
            "prayer_categorization_output_format.txt"
        ]
        
        for filename in required_files:
            file_path = self.prompts_dir / filename
            if not file_path.exists():
                raise FileNotFoundError(f"Required prompt file missing: {file_path}")
    
    def _read_prompt_file(self, filename: str) -> str:
        """Read and return content of a prompt file"""
        file_path = self.prompts_dir / filename
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return f.read().strip()
        except FileNotFoundError:
            raise FileNotFoundError(f"Prompt file not found: {file_path}")
        except Exception as e:
            raise Exception(f"Error reading prompt file {file_path}: {e}")
    
    def build_prayer_generation_prompt(self) -> str:
        """
        Build complete prayer generation system prompt based on active feature flags.
        
        Returns:
            Complete system prompt string composed from modular text files
        """
        
        # Re-read feature flags at runtime for testing flexibility
        prayer_categorization_enabled = os.getenv("PRAYER_CATEGORIZATION_ENABLED", "false").lower() == "true"
        ai_categorization_enabled = os.getenv("AI_CATEGORIZATION_ENABLED", "false").lower() == "true"
        safety_scoring_enabled = os.getenv("SAFETY_SCORING_ENABLED", "false").lower() == "true"
        
        # Always start with base prayer generation prompt
        prompt_parts = [self._read_prompt_file("prayer_generation_system.txt")]
        
        # Add categorization components only if enabled
        if prayer_categorization_enabled and ai_categorization_enabled:
            
            # Add request analysis instructions
            prompt_parts.append("")  # Blank line for readability
            prompt_parts.append(self._read_prompt_file("prayer_categorization_request_analysis.txt"))
            
            # Add instruction to generate prayer
            prompt_parts.append("")
            prompt_parts.append("[Generate the prayer based on the above guidelines]")
            
            # Add verification instructions
            prompt_parts.append("")
            prompt_parts.append(self._read_prompt_file("prayer_categorization_verification.txt"))
            
            # Add structured output format
            prompt_parts.append("")
            prompt_parts.append(self._read_prompt_file("prayer_categorization_output_format.txt"))
        
        elif prayer_categorization_enabled and safety_scoring_enabled:
            # Safety-only mode (minimal categorization)
            prompt_parts.append("")
            prompt_parts.append("After generating the prayer, evaluate:")
            prompt_parts.append("- Safety: Rate from 0.0 (concerning) to 1.0 (positive)")
            prompt_parts.append("- List any specific safety concerns")
            prompt_parts.append("")
            prompt_parts.append("Return format:")
            prompt_parts.append("SAFETY_SCORE: [0.0-1.0]")
            prompt_parts.append("SAFETY_FLAGS: [array of concerns]")
        
        return "\n".join(prompt_parts)
    
    def get_prompt_composition_info(self) -> dict:
        """
        Get information about current prompt composition for debugging/logging.
        
        Returns:
            Dictionary with composition details and feature flag states
        """
        
        # Re-read feature flags at runtime
        prayer_categorization_enabled = os.getenv("PRAYER_CATEGORIZATION_ENABLED", "false").lower() == "true"
        ai_categorization_enabled = os.getenv("AI_CATEGORIZATION_ENABLED", "false").lower() == "true"
        safety_scoring_enabled = os.getenv("SAFETY_SCORING_ENABLED", "false").lower() == "true"
        
        components = ["prayer_generation_system.txt"]
        
        if prayer_categorization_enabled and ai_categorization_enabled:
            components.extend([
                "prayer_categorization_request_analysis.txt",
                "prayer_categorization_verification.txt",
                "prayer_categorization_output_format.txt"
            ])
        elif prayer_categorization_enabled and safety_scoring_enabled:
            components.append("inline_safety_analysis")
        
        return {
            "components": components,
            "feature_flags": {
                "PRAYER_CATEGORIZATION_ENABLED": prayer_categorization_enabled,
                "AI_CATEGORIZATION_ENABLED": ai_categorization_enabled,
                "SAFETY_SCORING_ENABLED": safety_scoring_enabled
            },
            "total_components": len(components)
        }


# Singleton instance for application use
prompt_composition_service = PromptCompositionService()