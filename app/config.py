"""
Configuration management for the Document Converter API
"""

import os
from pathlib import Path
from typing import Dict, Any
from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings"""
    
    # API Configuration
    app_name: str = Field(default="Document Converter API", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    
    # File Storage Configuration
    base_dir: str = Field(default="/app/data", env="BASE_DIR")
    max_file_size: int = Field(default=50 * 1024 * 1024, env="MAX_FILE_SIZE")  # 50MB
    allowed_extensions: list = Field(default=[".docx"], env="ALLOWED_EXTENSIONS")
    
    # Processing Configuration
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    cleanup_temp_files: bool = Field(default=True, env="CLEANUP_TEMP_FILES")
    preserve_images: bool = Field(default=True, env="PRESERVE_IMAGES")
    
    # Pandoc Configuration
    pandoc_timeout: int = Field(default=300, env="PANDOC_TIMEOUT")  # 5 minutes
    pandoc_math_engine: str = Field(default="mathml", env="PANDOC_MATH_ENGINE")
    pandoc_toc_depth: int = Field(default=4, env="PANDOC_TOC_DEPTH")
    
    # HTML2Text Configuration
    h2t_body_width: int = Field(default=0, env="H2T_BODY_WIDTH")
    h2t_ignore_links: bool = Field(default=False, env="H2T_IGNORE_LINKS")
    h2t_ignore_images: bool = Field(default=True, env="H2T_IGNORE_IMAGES")
    h2t_unicode_snob: bool = Field(default=True, env="H2T_UNICODE_SNOB")

    # Security Configuration
    secret_key: str = Field(default="your-secret-key-here", env="SECRET_KEY")
    allowed_hosts: str = Field(default="localhost,127.0.0.1", env="ALLOWED_HOSTS")

    # Database Configuration
    database_url: str = Field(default="sqlite:///./document_converter.db", env="DATABASE_URL")

    # Redis Configuration
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")

    class Config:
        env_file = ".env"
        case_sensitive = False


class DirectoryManager:
    """Manages directory structure for the application"""
    
    def __init__(self, base_dir: str):
        self.base_dir = Path(base_dir)
        self.docx_dir = self.base_dir / "docx"
        self.html_dir = self.base_dir / "html"
        self.md_dir = self.base_dir / "md"
        self.temp_dir = self.base_dir / "temp"
        self.logs_dir = self.base_dir / "logs"
        
    def create_directories(self) -> None:
        """Create all necessary directories"""
        directories = [
            self.base_dir, self.docx_dir, self.html_dir, 
            self.md_dir, self.temp_dir, self.logs_dir
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError) as e:
                # Log the error but continue with other directories
                print(f"Warning: Could not create directory {directory}: {e}")
                continue
    
    def get_relative_path(self, file_path: Path, from_dir: Path) -> str:
        """Get relative path from one directory to another"""
        try:
            return str(file_path.relative_to(from_dir))
        except ValueError:
            return str(file_path)


# Global settings instance
settings = Settings()

# Global directory manager
dir_manager = DirectoryManager(settings.base_dir)
