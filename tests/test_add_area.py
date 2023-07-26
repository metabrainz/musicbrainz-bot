# A simple test script to add a new area to test .metabrainz.org

from musicbrainz_bot.editing import MusicBrainzClient
import musicbrainz_bot.config as cfg
import mechanize
import pytest


@pytest.fixture(scope="function")
def mb_client():
    mb = MusicBrainzClient(
        cfg.MB_USERNAME, cfg.MB_PASSWORD, cfg.MB_SITE, use_test_db=True
    )
    return mb


@pytest.fixture(scope="function")
def browser():
    browser = mechanize.Browser()
    browser.set_handle_robots(False)
    browser.set_debug_redirects(False)
    browser.set_debug_http(False)
    return browser


def _add_area(mb, browser):
    area = {
        "name": "test_area",
        "comment": "disambiguation_comment",
        "type": "3",
        "iso_3166_1": ["XX"],
        "iso_3166_2": ["XX-A"],
        "iso_3166_3": ["XXXA"],
        "url": [
            {
                "text": "https://www.wikidata.org/wiki/Q152",
                "link_type_id": 358,
            },
        ],
    }

    edit_note = "Tests new area with name, type, disambiguation, edit note."
    area_mbid = mb.add_area(area, edit_note=edit_note)

    return area_mbid


def test_add_area(mb_client, browser, reset_db):
    try:
        area_mbid = _add_area(mb_client, browser)
        assert area_mbid is not None, "Area MBID is None"
        print(
            f"""Area Generated with MBID: {area_mbid}
Link: https://localhost:5000/area/{area_mbid}"""
        )
    except Exception as e:
        pytest.fail(str(e))


if __name__ == "__main__":
    pytest.main([__file__])