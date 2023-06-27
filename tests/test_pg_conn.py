import psycopg2 as pg
from musicbrainz_bot import config

URI = config.MB_TEST_DB


def test_connection():
    is_success: bool = False
    try:
        _ = pg.connect(URI)
        is_success = True
        assert is_success is True

    except Exception as e:
        print("PostgreSQL TEST Connection Failed")
        print(e)
