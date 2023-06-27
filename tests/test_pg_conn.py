import psycopg2 as pg
from musicbrainz_bot import config


def make_connection(use_test_db: bool) -> bool:
    if use_test_db is True:
        URI = config.MB_TEST_DB
    else:
        URI = config.MB_DB

    try:
        _ = pg.connect(URI)
        return True

    except Exception:
        return False


def test_TEST_DB_connection() -> None:
    """Test the connection to the test database."""
    result = make_connection(use_test_db=True)
    assert result is True, "Connection to the TEST database failed."


def test_DB_connection() -> None:
    """Test the connection to the main database."""
    result = make_connection(use_test_db=False)
    assert result is True, "Connection to the main database failed."
