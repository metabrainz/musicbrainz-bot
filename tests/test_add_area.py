# A simple test script to add a new area to test .metabrainz.org

from musicbrainz_bot.editing import MusicBrainzClient
import musicbrainz_bot.config as cfg
import mechanize


def test_add_area():
    try:
        area_mbid = _add_area()
        assert area_mbid is not None, "Area MBID is None"
    except Exception as e:
        raise Exception(e)


def _add_area():
    mb = MusicBrainzClient(
        cfg.MB_USERNAME, cfg.MB_PASSWORD, cfg.MB_SITE, use_test_db=True
    )

    browser = mechanize.Browser()
    browser.set_handle_robots(False)
    browser.set_debug_redirects(False)
    browser.set_debug_http(False)

    area = {
        "name": "updating add_area() to remove 'data_template'",
        "comment": "disambiguation_test",
        "type": "3",
        "iso_3166_1": None,
        "iso_3166_2": None,
        "iso_3166_3": ["XXXA"],
        "url": [
            {
                "text": "https://www.wikidata.org/wiki/Q152",
                "link_type_id": 358,
            },
            {
                "text": "https://www.wikidata.org/wiki/Q1494",
                "link_type_id": 358,
            },
        ],
    }

    edit_note = "Tests new area with name, type, disambiguation, edit note."
    area_mbid = mb.add_area(area, edit_note=edit_note)

    return area_mbid
