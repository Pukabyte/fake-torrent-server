from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    LOG_LEVEL: str = "DEBUG"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings() 
