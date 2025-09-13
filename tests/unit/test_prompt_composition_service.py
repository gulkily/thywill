"""Unit tests for PromptCompositionService"""
import pytest
import os
from unittest.mock import patch, Mock
from pathlib import Path

from app_helpers.services.prompt_composition_service import PromptCompositionService


@pytest.mark.unit
class TestPromptCompositionService:
    """Test prompt composition functionality"""
    
    def test_service_initialization_validates_prompt_files(self):
        """Test that service validates all required prompt files exist"""
        # This test runs with real files, so it should pass if files exist
        service = PromptCompositionService()
        assert service.prompts_dir.exists()
        
        # Should have person differentiation in required files
        required_files = [
            "prayer_generation_system.txt",
            "prayer_categorization_request_analysis.txt",
            "prayer_categorization_verification.txt", 
            "prayer_categorization_output_format.txt",
            "prayer_person_differentiation.txt"
        ]
        
        for filename in required_files:
            assert (service.prompts_dir / filename).exists()
    
    @patch.dict('os.environ', {'PRAYER_PERSON_DIFFERENTIATION_ENABLED': 'true'})
    def test_build_prompt_with_person_differentiation_enabled(self):
        """Test prompt building with person differentiation enabled"""
        service = PromptCompositionService()
        prompt = service.build_prayer_generation_prompt()
        
        # Should include person differentiation content
        assert "COLLECTIVE PRONOUNS" in prompt
        assert "INDIVIDUAL/THIRD-PARTY PRONOUNS" in prompt
        assert "us/our/we" in prompt
        assert "me/my/I" in prompt
        assert "PRAYER FORMATTING RULES" in prompt
    
    @patch.dict('os.environ', {'PRAYER_PERSON_DIFFERENTIATION_ENABLED': 'false'})  
    def test_build_prompt_with_person_differentiation_disabled(self):
        """Test prompt building with person differentiation disabled"""
        service = PromptCompositionService()
        prompt = service.build_prayer_generation_prompt()
        
        # Should NOT include person differentiation content
        assert "COLLECTIVE PRONOUNS" not in prompt
        assert "INDIVIDUAL/THIRD-PARTY PRONOUNS" not in prompt
        assert "PRAYER FORMATTING RULES" not in prompt
        
        # Should still include base prompt
        assert "COMMUNITY can pray FOR the person" in prompt or "community" in prompt.lower()
    
    @patch.dict('os.environ', {
        'PRAYER_PERSON_DIFFERENTIATION_ENABLED': 'true',
        'PRAYER_CATEGORIZATION_ENABLED': 'true', 
        'AI_CATEGORIZATION_ENABLED': 'true'
    })
    def test_build_prompt_with_multiple_features_enabled(self):
        """Test prompt building with both person differentiation and categorization"""
        service = PromptCompositionService()
        prompt = service.build_prayer_generation_prompt()
        
        # Should include both features
        assert "COLLECTIVE PRONOUNS" in prompt
        assert "categorization" in prompt.lower() or "CATEGORY" in prompt
        
        # Should be properly structured
        parts = prompt.split("\n\n")
        assert len(parts) >= 3  # Base + person diff + categorization components
    
    def test_get_composition_info_includes_person_differentiation(self):
        """Test composition info includes person differentiation status"""
        service = PromptCompositionService()
        
        with patch.dict('os.environ', {'PRAYER_PERSON_DIFFERENTIATION_ENABLED': 'true'}):
            info = service.get_prompt_composition_info()
            
            assert info['feature_flags']['PRAYER_PERSON_DIFFERENTIATION_ENABLED'] is True
            assert "prayer_person_differentiation.txt" in info['components']
        
        with patch.dict('os.environ', {'PRAYER_PERSON_DIFFERENTIATION_ENABLED': 'false'}):
            info = service.get_prompt_composition_info()
            
            assert info['feature_flags']['PRAYER_PERSON_DIFFERENTIATION_ENABLED'] is False
            assert "prayer_person_differentiation.txt" not in info['components']
    
    def test_component_order_with_person_differentiation(self):
        """Test that person differentiation comes after base but before categorization"""
        service = PromptCompositionService()
        
        with patch.dict('os.environ', {
            'PRAYER_PERSON_DIFFERENTIATION_ENABLED': 'true',
            'PRAYER_CATEGORIZATION_ENABLED': 'true',
            'AI_CATEGORIZATION_ENABLED': 'true'
        }):
            info = service.get_prompt_composition_info()
            components = info['components']
            
            # Should be in correct order
            base_index = components.index("prayer_generation_system.txt")
            person_index = components.index("prayer_person_differentiation.txt")
            cat_index = components.index("prayer_categorization_request_analysis.txt")
            
            assert base_index < person_index < cat_index
    
    def test_prompt_file_reading_handles_errors_gracefully(self):
        """Test that missing or corrupted prompt files are handled"""
        service = PromptCompositionService()
        
        # Test reading non-existent file
        with pytest.raises(FileNotFoundError):
            service._read_prompt_file("nonexistent.txt")
        
        # Test that existing files can be read
        content = service._read_prompt_file("prayer_generation_system.txt")
        assert len(content) > 0
        assert isinstance(content, str)
    
    @patch.dict('os.environ', {'PRAYER_PERSON_DIFFERENTIATION_ENABLED': 'true'})
    def test_person_differentiation_prompt_content_structure(self):
        """Test that person differentiation prompt has expected structure"""
        service = PromptCompositionService()
        content = service._read_prompt_file("prayer_person_differentiation.txt")
        
        # Should have all required sections
        assert "COLLECTIVE PRONOUNS" in content
        assert "INDIVIDUAL/THIRD-PARTY PRONOUNS" in content  
        assert "PRAYER FORMATTING RULES" in content
        assert "EDGE CASES" in content
        
        # Should specify pronoun examples
        assert "us/our/we" in content
        assert "me/my/I" in content
        
        # Should have formatting instructions
        assert "FOR COLLECTIVE REQUESTS" in content
        assert "FOR INDIVIDUAL/THIRD-PARTY REQUESTS" in content