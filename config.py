# Nova-Exchange Configuration
import os
from pydantic_settings import BaseSettings
from typing import Optional


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""
    
    # Supabase configuration
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_key: Optional[str] = None
    
    # App configuration
    app_name: str = "Nova Exchange"
    app_description: str = "Nova SBE Marketplace for Students"
    debug: bool = False
    
    # Security
    secret_key: str = "your-secret-key-change-in-production"
    
    # File upload settings
    max_file_size: int = 5 * 1024 * 1024  # 5MB
    allowed_image_types: list[str] = ["image/jpeg", "image/png", "image/webp", "image/gif"]
    max_images_per_listing: int = 3
    
    class Config:
        env_file = ".env"
        env_prefix = ""
        
    @property
    def supabase(self) -> tuple[str, str]:
        """Return (url, anon_key) tuple."""
        return (self.supabase_url, self.supabase_anon_key)


# Global settings instance
settings = Settings()
