import musicbrainz_bot.config as cfg
from os import system as system
from time import perf_counter
import requests
import psycopg2 as pg


"""
Defines some utility functions for testing on the musicbrainz_test database.
"""


def get_test_db_URI():
    MB_TEST_DB = f"postgresql://{cfg.TEST_DB_USERNAME}:{cfg.TEST_DB_PASSWD}@{cfg.TEST_DB_HOST}:{cfg.TEST_DB_PORT}/{cfg.TEST_DB_NAME}"
    return MB_TEST_DB


def get_db_URI():
    MB_DB = f"postgresql://{cfg.DB_USERNAME}:{cfg.DB_PASSWD}@{cfg.DB_HOST}:{cfg.DB_PORT}/{cfg.DB_NAME}"
    return MB_DB


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
    id: int = 1000,
) -> int:
    """
    Deletes a user on the database with the given ID.
    """

    try:
        cur = db_conn.cursor()
        del_query = """
        DELETE from edit_area where edit = ANY (SELECT edit FROM edit where editor = 1000);
        DELETE from edit_data where edit = ANY (SELECT edit FROM edit where editor = 1000);
        DELETE from edit_note where edit = ANY (SELECT edit FROM edit where editor = 1000);
        DELETE from edit_url where edit = ANY (SELECT edit FROM edit where editor = 1000);
        DELETE FROM edit where editor = 1000;
        DELETE FROM editor where ID = 1000;
        """

        cur.execute(del_query)
        cur.close()

    except Exception as e:
        raise (e)

    return id


def delete_area(db_conn, area_name: str = "test_area"):
    """
    Deletes an area on the database with the given area name.
    """
    try:
        cur = db_conn.cursor()

        area_id_query = """SELECT id from area where name=%s;"""
        cur.execute(area_id_query, (area_name,))

        try:
            area_id = cur.fetchone()[0]

        except Exception as e:
            raise (e)

        del_query = """
        delete from iso_3166_1 where area = %s;
        delete from iso_3166_2 where area = %s;
        delete from iso_3166_3 where area = %s;
        delete from l_area_url where entity0 = %s;
        delete from area where id = %s;
        """

        values = (area_id, area_id, area_id, area_id, area_id)

        cur.execute(del_query, values)
        cur.close()

    except Exception as e:
        raise (e)


def reset_db(db_conn):
    delete_user(db_conn, id=1000)
    delete_area(db_conn, area_name="test_area")


def get_entity_json(mbid: str, entity_type: str, payload: dict = {""}) -> dict:
    """Returns a dictionary containing the JSON response from the MusicBrainz API for the given MBID and entity type.

    Args:
        mbid (str): MusicBrainz ID of the entity.
        entity_type (str): entity type. One of "area", "artist", "event", "instrument", "label", "place", "recording", "release", "release-group", "series", "work", "url", "genre", "collection".
        payload (dict, optional): optional arguments. Defaults to {}.

    Returns:
        dict: A dictionary containing the JSON response from the MusicBrainz API for the given MBID and entity type.
    """
    url = f"{cfg.MB_SITE}/ws/2/{entity_type}/{mbid}"
    headers = {
        "mb-set-database": "TEST",
    }
    params = {
        "fmt": "json",
        "inc": "url-rels",
    }

    response = requests.get(url, headers=headers, params=params)
    return response.json()


def reset_db_docker(create_new_user: bool = False):
    """Resets the musicbrainz_test database by running the script/create_test_db.sh script in the musicbrainz docker container."""
    MB_TEST_DB = get_test_db_URI()

    try:
        start = perf_counter()
        system(
            f'sudo docker exec {cfg.MUSICBRAINZ_CONTAINER_ID} "script/create_test_db.sh"'
        )
        if create_new_user:
            with pg.connect(MB_TEST_DB) as conn:
                create_user(conn)

        end = perf_counter()

        print(f"Database reset in {round(end - start, 2)} seconds")
        return True

    except Exception as e:
        raise Exception(f"Failed to reset database: {e}")
