import pytest
import tests.utils as utils
import psycopg2 as pg

MB_TEST_DB = utils.get_test_db_URI()


@pytest.fixture(scope="session", autouse=True)
def reset_db(db_conn):
    # utils.reset_db_docker(db_conn)
    utils.create_user(db_conn)
    yield
    utils.reset_db(db_conn)


@pytest.fixture(scope="session")
def db_conn():
    conn = pg.connect(MB_TEST_DB)
    conn.autocommit = True

    yield conn

    conn.close()
