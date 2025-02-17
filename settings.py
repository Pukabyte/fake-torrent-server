from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    LOG_LEVEL: str = "INFO"
    INFOHASH: str = "41e6cd50ccec55cd5704c5e3d176e7b59317a3fb"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings() 
