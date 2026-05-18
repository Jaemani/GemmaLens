from sqlalchemy import text

from app.db.session import Base, engine


def init_db() -> None:
    Base.metadata.create_all(bind=engine)
    migrate_sqlite()


def migrate_sqlite() -> None:
    if engine.dialect.name != "sqlite":
        return
    with engine.begin() as connection:
        dictionary_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(dictionary_items)"))}
        if "view_count" not in dictionary_columns:
            connection.execute(text("ALTER TABLE dictionary_items ADD COLUMN view_count INTEGER DEFAULT 0"))
        if "last_viewed_at" not in dictionary_columns:
            connection.execute(text("ALTER TABLE dictionary_items ADD COLUMN last_viewed_at DATETIME"))

        profile_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(user_profiles)"))}
        if "support_language" not in profile_columns:
            connection.execute(text("ALTER TABLE user_profiles ADD COLUMN support_language VARCHAR(32) DEFAULT 'Korean'"))
        if "learning_language" not in profile_columns:
            connection.execute(text("ALTER TABLE user_profiles ADD COLUMN learning_language VARCHAR(32) DEFAULT 'English'"))
        if "auto_analyze_documents" not in profile_columns:
            connection.execute(text("ALTER TABLE user_profiles ADD COLUMN auto_analyze_documents BOOLEAN DEFAULT 1"))
        if "onboarding_completed" not in profile_columns:
            connection.execute(text("ALTER TABLE user_profiles ADD COLUMN onboarding_completed BOOLEAN DEFAULT 0"))
        connection.execute(text("UPDATE user_profiles SET learning_language = 'English' WHERE learning_language IS NULL OR learning_language = ''"))
        connection.execute(text("UPDATE user_profiles SET support_language = 'Korean' WHERE support_language IS NULL OR support_language = ''"))
        connection.execute(text("UPDATE user_profiles SET target_level = 'C2' WHERE target_level IS NULL OR target_level = '' OR target_level = 'unknown'"))
        connection.execute(text("UPDATE user_profiles SET auto_analyze_documents = 1 WHERE auto_analyze_documents IS NULL"))

        document_columns = {row[1] for row in connection.execute(text("PRAGMA table_info(documents)"))}
        if "original_file_path" not in document_columns:
            connection.execute(text("ALTER TABLE documents ADD COLUMN original_file_path VARCHAR(1024)"))
        if "original_mime_type" not in document_columns:
            connection.execute(text("ALTER TABLE documents ADD COLUMN original_mime_type VARCHAR(255)"))
