import pytest
import tests.utils as utils
import psycopg2 as pg
from musicbrainz_bot import config as cfg


@pytest.fixture(scope="session", autouse=True)
def reset_db(db_conn):
    utils.create_user(db_conn)
    yield
    utils.reset_db(db_conn)


@pytest.fixture(scope="session")
def db_conn():
    conn = pg.connect(cfg.MB_TEST_DB)
    conn.autocommit = True

    yield conn

    conn.close()
