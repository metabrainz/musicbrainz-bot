import musicbrainz_bot.config as cfg
from os import system as system
from time import perf_counter

"""
Defines some utility functions for testing on the musicbrainz_test database.
"""


def _get_free_editor_id(db_conn):
    """
    Returns the lowest editor ID that is not currently in use.
    """
    cur = db_conn.cursor()
    query = """
    SELECT id FROM editor
    ORDER BY id DESC
    LIMIT 1;"""
    cur.execute(query)
    results = cur.fetchone()

    cur.close()

    if results is None:
        return 1
    else:
        return results[0] + 2


def create_user(
    db_conn,
    username: str = "test_user",
    password: str = "pass",
    privs: int = 256,
    id: int = 1000,
    use_test_db: bool = True,
) -> int:
    """
    Creates a user on the database with the given username, password, and privileges.
    """
    password = "{CLEARTEXT}pass"
    # db_URI = cfg.MB_TEST_DB if use_test_db else cfg.MB_DB

    # with pg.connect(db_URI) as conn:
    cur = db_conn.cursor()
    query = (
        "INSERT INTO editor "
        "(id, name, password, privs, email, website, bio, email_confirm_date, member_since, last_login_date, ha1) "
        "VALUES (%s, %s, %s, %s, 'test@editor.org', 'http://musicbrainz.org', 'biography', '2005-10-20', '1989-07-23', now(), 'e1dd8fee8ee728b0ddc8027d3a3db478');"
    )
    values = (id, username, password, privs)
    cur.execute(query, values)

    cur.close()

    return id


def delete_user(
    db_conn,
    id: int,
) -> int:
    """
    Deletes a user on the database with the given id.
    """
    cur = db_conn.cursor()
    query = "DELETE FROM editor WHERE id = %s;"
    values = (id,)
    cur.execute(query, values)

    cur.close()

    return id


def reset_db(db_conn):
    try:
        start = perf_counter()
        system(
            f'sudo docker exec {cfg.MUSICBRAINZ_CONTAINER_ID} "script/create_test_db.sh"'
        )
        create_user(db_conn)

        end = perf_counter()

        print(f"Database reset in {round(end - start, 2)} seconds")
        return True

    except Exception as e:
        raise Exception(f"Failed to reset database: {e}")
