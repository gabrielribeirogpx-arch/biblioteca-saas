import os

class Settings:
    DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@db:5432/library")

settings = Settings()