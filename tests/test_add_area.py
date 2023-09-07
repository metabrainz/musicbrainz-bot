# A simple test script to add a new area to test .metabrainz.org

from musicbrainz_bot.editing import MusicBrainzClient
import musicbrainz_bot.config as cfg
import mechanize
import pytest
import tests.utils as utils


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


@pytest.fixture(scope="function")
def area_seed():
    return {
        "name": "test_area",
        "comment": "disambiguation_comment",
        "type_id": "3",
        "iso_3166_1": ["XX", "YY"],
        "iso_3166_2": ["XX-A", "XX-B"],
        "iso_3166_3": ["XXXA", "XXXB"],
        "url": [
            {
                "text": "https://www.wikidata.org/wiki/Q152",
                "link_type_id": 358,
            },
            {
                "text": "https://www.wikidata.org/wiki/Q153",
                "link_type_id": 358,
            },
        ],
    }


def _add_area(area, mb, browser):
    edit_note = "Tests new area with name, type, disambiguation, ISO 3166-1, ISO 3166-2, ISO 3166-3, URL, edit note."
    area_mbid = mb.add_area(area, edit_note=edit_note)

    return area_mbid


def test_add_area(mb_client, browser, reset_db, area_seed):
    area_types = {
        "1": "Country",
        "2": "Subdivision",
        "3": "City",
        "4": "Municipality",
        "5": "District",
        "6": "Island",
        "7": "County",
    }

    link_type_ids = {"wikidata": "358", "geonames": "713"}

    try:
        area_mbid = _add_area(area_seed, mb_client, browser)
        posted_data = utils.get_entity_json(area_mbid, "area")

        assert area_mbid is not None, "Area MBID is None"
        assert posted_data["id"] == area_mbid, "Area MBID is incorrect"

        assert posted_data["name"] == area_seed["name"], "Area name is incorrect"

        assert (
            posted_data["disambiguation"] == area_seed["comment"]
        ), "Area disambiguation is incorrect"

        assert (
            posted_data["type"] == area_types[area_seed["type_id"]]
        ), "Area type is incorrect"

        assert (
            posted_data["iso-3166-1-codes"] == area_seed["iso_3166_1"]
        ), "Area ISO 3166-1 is incorrect"

        assert (
            posted_data["iso-3166-2-codes"] == area_seed["iso_3166_2"]
        ), "Area ISO 3166-2 is incorrect"

        assert (
            posted_data["iso-3166-3-codes"] == area_seed["iso_3166_3"]
        ), "Area ISO 3166-3 is incorrect"

        for original, received in zip(area_seed["url"], posted_data["relations"]):
            assert (
                received["url"]["resource"] == original["text"]
            ), "Area URL is incorrect"
            try:
                assert (
                    received["type"] == link_type_ids[original["link_type_id"]]
                ), "Area URL link type is incorrect"
            except KeyError:
                pass

        print(
            f"""Area Generated with MBID: {area_mbid}\nLink: {cfg.MB_SITE}/area/{area_mbid}"""
        )
    except Exception as e:
        assert False, f"{e}"


if __name__ == "__main__":
    pytest.main([__file__])
