import os
from dataclasses import dataclass
import dotenv

dotenv.load_dotenv()
# Definição das variaveis


@dataclass
class Settings:
    db_user: str
    db_pass: str
    db_database: str
    db_host: str
    db_table: str
    db_endpoint: str
    site_praticagem: str
    log_file: str
    log_format: str


settings = Settings(
    os.getenv("DB_USER"),
    os.getenv("DB_PASS"),
    os.getenv("DB_DATABASE"),
    os.getenv("DB_HOST"),
    os.getenv("DB_TABLE"),
    os.getenv("DB_ENDPOINT"),
    os.getenv("SITE_PRATICAGEM"),
    "file.log",
    "%(asctime)s - %(levelname)s - %(message)s",
)
