import os
from typing import List, Union
from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "Employee Payroll Management System"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"

    # Security & Tokens
    SECRET_KEY: str = "supersecret_payroll_jwt_encryption_key_change_in_production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # Database
    DATABASE_URL: str = "mysql+pymysql://root:root@localhost:3306/payroll_db"
    USE_SQLITE_FALLBACK: bool = True
    SQLITE_FALLBACK_URL: str = "sqlite:///./payroll.db"

    # CORS
    CORS_ORIGINS: Union[List[str], str] = ["*"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",") if i.strip()]
        elif isinstance(v, list):
            return v
        return ["*"]

    # Organization & PDF Settings
    COMPANY_NAME: str = "Antigravity Enterprise Solutions Inc."
    COMPANY_ADDRESS: str = "100 Tech Innovation Boulevard, Silicon Valley, CA"
    COMPANY_CONTACT: str = "hr@antigravity.io | +1 (555) 019-2834"

    # File System
    UPLOAD_DIR: str = "./uploads"
    PAYSLIP_DIR: str = "./uploads/payslips"

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env"),
        env_file_encoding="utf-8",
        extra="ignore"
    )


settings = Settings()

# Ensure directories exist
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
os.makedirs(settings.PAYSLIP_DIR, exist_ok=True)
