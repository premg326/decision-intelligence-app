from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    ai_api_key: str = ""
    ai_base_url: str = "https://api.openai.com/v1"
    ai_model: str = "gpt-4o-mini"
    database_url: str = "sqlite+aiosqlite:///./shadow.db"
    cors_origins: str = "http://localhost:3000"
    max_scenario_nodes: int = 250
    max_scenario_edges: int = 800
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings=Settings()
