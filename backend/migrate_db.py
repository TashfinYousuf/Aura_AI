# FILE: backend/migrate_db.py
from app.database.session import engine
from sqlalchemy import text

def run_migration():
    with engine.connect() as conn:
        try:
            conn.execute(text("ALTER TABLE user_profiles ADD COLUMN telegram_id VARCHAR;"))
            conn.commit()
            print("✅ [MIGRATION SUCCESS] 'telegram_id' column added to user_profiles table!")
        except Exception as e:
            if "duplicate column name" in str(e).lower() or "already exists" in str(e).lower():
                print("ℹ️ Column 'telegram_id' already exists.")
            else:
                print(f"⚠️ Migration Error: {e}")

if __name__ == "__main__":
    run_migration()