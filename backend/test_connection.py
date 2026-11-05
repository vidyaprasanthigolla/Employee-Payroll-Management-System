"""
Database & App Initialization Health Check Script
"""
import sys
import os

# Add backend directory to sys.path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.config import settings
from app.db.session import engine, SessionLocal
from sqlalchemy import text


def test_db_connection():
    print("=" * 60)
    print("EMPLOYEE PAYROLL MANAGEMENT SYSTEM - PHASE 3 VERIFICATION")
    print("=" * 60)
    print(f"Project Name     : {settings.PROJECT_NAME}")
    print(f"Version          : {settings.VERSION}")
    print(f"Configured DB    : {settings.DATABASE_URL.split('@')[-1] if '@' in settings.DATABASE_URL else settings.DATABASE_URL}")
    print(f"Active Dialect   : {engine.dialect.name}")

    try:
        session = SessionLocal()
        result = session.execute(text("SELECT 1")).scalar()
        session.close()
        if result == 1:
            print("[SUCCESS] Database connection established and verified.")
            print("[SUCCESS] SQLAlchemy session factory is functional.")
            return True
        else:
            print("[ERROR] Query executed but unexpected result returned.")
            return False
    except Exception as e:
        print(f"[FAIL] Database connection error: {e}")
        return False


if __name__ == "__main__":
    success = test_db_connection()
    sys.exit(0 if success else 1)
