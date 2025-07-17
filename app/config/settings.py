import os
from pydantic_settings import BaseSettings
from typing import Optional

class Settings(BaseSettings):
    """Application settings"""
    
    openai_api_key: str
    db_host: str = "localhost"
    db_name: str = "faq_db"
    db_user: str = "faq_user"
    db_password: str
    db_port: str = "5432"
    environment: str = "development"
    log_level: str = "INFO"
    
    @property
    def database_url(self) -> str:
        """Database connection URL"""
        return f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
    
    @property
    def db_config(self) -> dict:
        """Database configuration dictionary"""
        return {
            "host": self.db_host,
            "database": self.db_name,
            "user": self.db_user,
            "password": self.db_password,
            "port": self.db_port
        }
    
    class Config:
        env_file = ".env"

settings = Settings()