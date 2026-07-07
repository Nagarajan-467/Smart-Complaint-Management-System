from app.config import Settings


def test_database_url_falls_back_to_sqlite_when_mysql_settings_are_missing():
    settings = Settings(
        db_host="",
        db_user="",
        db_name="",
        db_password="",
        database_url_override=None,
    )

    assert settings.database_url.startswith("sqlite://")
