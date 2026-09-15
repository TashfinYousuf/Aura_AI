# clean_bad_users.py
from app.database.session import SessionLocal
from app.database.models import SemanticMemory

with SessionLocal() as db:
    # Delete template literal strings and invalid IDs
    deleted = db.query(SemanticMemory).filter(
        (SemanticMemory.user_id.like("%currentUser%")) | 
        (SemanticMemory.user_id.like("%${%"))
    ).delete(synchronize_session=False)
    db.commit()
    print(f"🧹 Cleaned {deleted} invalid dummy records from DB.")