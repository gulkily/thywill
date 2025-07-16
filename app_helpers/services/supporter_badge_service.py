#!/usr/bin/env python3
"""
Supporter Badge Service for ThyWill

Handles multi-type supporter badges with configurable symbols, colors, and tooltips.
"""

import json
import os
from typing import Dict, List, Optional
from pathlib import Path


class SupporterBadgeService:
    """Service for managing supporter badges with multiple types."""
    
    def __init__(self, config_path: str = "supporter_badges_config.json"):
        self.config_path = Path(config_path)
        self._config_cache = None
        self._config_mtime = None
    
    def _load_config(self) -> Dict:
        """Load badge configuration from JSON file with caching."""
        if not self.config_path.exists():
            # Return default config if file doesn't exist
            return {
                "financial": {
                    "symbol": "♥",
                    "color": "#dc2626",
                    "tooltip": "Financial Supporter",
                    "priority": 1
                }
            }
        
        current_mtime = self.config_path.stat().st_mtime
        
        # Check if we need to reload the config
        if self._config_cache is None or self._config_mtime != current_mtime:
            try:
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config_cache = json.load(f)
                self._config_mtime = current_mtime
            except (json.JSONDecodeError, IOError) as e:
                print(f"Error loading supporter badge config: {e}")
                # Return default config on error
                return {
                    "financial": {
                        "symbol": "♥",
                        "color": "#dc2626",
                        "tooltip": "Financial Supporter",
                        "priority": 1
                    }
                }
        
        return self._config_cache
    
    def get_badge_config(self, supporter_type: str) -> Optional[Dict]:
        """Get badge configuration for a specific supporter type."""
        config = self._load_config()
        return config.get(supporter_type)
    
    def get_all_badge_configs(self) -> Dict:
        """Get all badge configurations."""
        return self._load_config()
    
    def parse_supporter_types(self, supporter_type_str: str) -> List[str]:
        """Parse supporter type string into list of types."""
        if not supporter_type_str:
            return []
        
        # Handle comma-separated types
        types = [t.strip() for t in supporter_type_str.split(',')]
        return [t for t in types if t]  # Remove empty strings
    
    def generate_badge_html(self, supporter_type_str: str, max_badges: int = 3) -> str:
        """Generate HTML for supporter badges based on type string."""
        if not supporter_type_str:
            return ''
        
        types = self.parse_supporter_types(supporter_type_str)
        if not types:
            return ''
        
        config = self._load_config()
        
        # Get badge configurations for each type
        badge_configs = []
        for supporter_type in types:
            if supporter_type in config:
                badge_configs.append((supporter_type, config[supporter_type]))
        
        # Sort by priority (lower number = higher priority)
        badge_configs.sort(key=lambda x: x[1].get('priority', 999))
        
        # Limit to max_badges
        badge_configs = badge_configs[:max_badges]
        
        # Generate HTML
        html_parts = []
        for supporter_type, badge_config in badge_configs:
            symbol = badge_config.get('symbol', '♥')
            color = badge_config.get('color', '#dc2626')
            tooltip = badge_config.get('tooltip', f'{supporter_type.title()} Supporter')
            
            html_parts.append(
                f'<span class="supporter-badge" '
                f'style="color: {color}; animation: pulse 2s infinite;" '
                f'title="{tooltip}">{symbol}</span>'
            )
        
        return ''.join(html_parts)
    
    def generate_user_badge_html(self, user) -> str:
        """Generate badge HTML for a user object."""
        if not user or not getattr(user, 'is_supporter', False):
            return ''
        
        supporter_type = getattr(user, 'supporter_type', None)
        
        # Backward compatibility: if no supporter_type, default to financial
        if not supporter_type:
            supporter_type = 'financial'
        
        return self.generate_badge_html(supporter_type)
    
    def get_available_types(self) -> List[str]:
        """Get list of available supporter types."""
        config = self._load_config()
        return list(config.keys())
    
    def get_type_display_name(self, supporter_type: str) -> str:
        """Get display name for a supporter type."""
        config = self.get_badge_config(supporter_type)
        if config:
            return config.get('tooltip', supporter_type.title())
        return supporter_type.title()


# Global instance
supporter_badge_service = SupporterBadgeService()