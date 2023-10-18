# A simple test script to edit an existing area in musicbrainz.org

from musicbrainz_bot.editing import MusicBrainzClient
import musicbrainz_bot.config as cfg
import pytest
import tests.utils as utils


@pytest.fixture(scope="function")
def mb_client():
    mb = MusicBrainzClient(
        cfg.MB_USERNAME, cfg.MB_PASSWORD, cfg.MB_SITE, use_test_db=True
    )
    return mb


@pytest.fixture(scope="function")
def area_updatable():
    return {
        "name": "test_area_edit",
        "comment": "disambiguation_comment",
        "type_id": "3",
        "iso_3166_1": ["AA", "BB"],
        "iso_3166_2": ["AA-A", "BB-B"],
        "iso_3166_3": ["AAAA", "BBBB"],
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


@pytest.fixture(scope="function")
def area_update():
    return {
        "name": "test_area_edit_edited",
        "comment": "disambiguation_comment",
        "type_id": "3",
        "iso_3166_1": ["AX", "BX"],
        "iso_3166_2": ["AA-X", "BB-X"],
        "iso_3166_3": ["AAAX", "BBBX"],
        "url": [
            {
                "text": "https://www.wikidata.org/wiki/Q152",
                "link_type_id": 358,
            },
            {
                "text": "https://www.wikidata.org/wiki/Q153",
                "link_type_id": 358,
            },
            {
                "text": "https://www.wikidata.org/wiki/Q154",
                "link_type_id": 358,
            },
        ],
    }


def _add_area(area, mb):
    edit_note = "Tests new area with name, type, disambiguation, ISO 3166-1, ISO 3166-2, ISO 3166-3, URL, edit note."
    area_mbid = mb.add_area(area, edit_note=edit_note)

    return area_mbid


def _edit_area(area, update, gid, mb):
    edit_note = "Tests new area with name, type, disambiguation, ISO 3166-1, ISO 3166-2, ISO 3166-3, URL, edit note."
    area_mbid = mb.edit_area(gid, area, update, edit_note=edit_note)

    return area_mbid


def test_edit_area(mb_client, reset_db, area_updatable, area_update):
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
        area_mbid_og = _add_area(area_updatable, mb_client)
        area_mbid = _edit_area(area_updatable, area_update, area_mbid_og, mb_client)
        posted_data = utils.get_entity_json(area_mbid, "area")

        assert posted_data["name"] == area_update["name"], "Area name is incorrect"

        assert (
            posted_data["disambiguation"] == area_update["comment"]
        ), "Area disambiguation is incorrect"

        assert (
            posted_data["type"] == area_types[area_update["type_id"]]
        ), "Area type is incorrect"

        assert (
            posted_data["iso-3166-1-codes"] == area_update["iso_3166_1"]
        ), "Area ISO 3166-1 is incorrect"

        assert (
            posted_data["iso-3166-2-codes"] == area_update["iso_3166_2"]
        ), "Area ISO 3166-2 is incorrect"

        assert (
            posted_data["iso-3166-3-codes"] == area_update["iso_3166_3"]
        ), "Area ISO 3166-3 is incorrect"

        for original, received in zip(area_update["url"], posted_data["relations"]):
            assert (
                received["url"]["resource"] == original["text"]
            ), "Area URL is incorrect"  # area URL correct?
            try:
                assert (
                    received["type"] == link_type_ids[original["link_type_id"]]
                ), "Area URL link type is incorrect"  # area URL link type correct?
            except KeyError:
                pass

        assert area_mbid is not None, "Area MBID is None"
        print(
            f"""Area Edited with MBID: {area_mbid}\nLink: http://localhost:5000/area/{area_mbid}"""
        )
    except Exception as e:
        pytest.fail(str(e))


if __name__ == "__main__":
    pytest.main([__file__])
