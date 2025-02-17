from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    RADARR_URL: str = "http://radarr:7878"
    SONARR_URL: str = "http://sonarr:8989"
    RADARR_API_KEY: str = ""
    SONARR_API_KEY: str = ""
    ZILEAN_URL: str = "http://zilean:8181"
    MATCH_THRESHOLD: float = 0.8
    LOG_LEVEL: str = "INFO"
    
    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"

settings = Settings() 
