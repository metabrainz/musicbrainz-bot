#!/usr/bin/python

import re
import sqlalchemy
import solr
from simplemediawiki import MediaWiki
from editing import MusicBrainzClient
import pprint
import urllib
import time
from utils import mangle_name, join_names, out
import config as cfg

engine = sqlalchemy.create_engine(cfg.MB_DB)
db = engine.connect()
db.execute("SET search_path TO musicbrainz")

wp_lang = 'fr'

wp = MediaWiki('http://'+wp_lang+'.wikipedia.org/w/api.php')

suffix = '_' + wp_lang if wp_lang != 'en' else ''
wps = solr.SolrConnection('http://localhost:8983/solr/wikipedia'+suffix)

mb = MusicBrainzClient(cfg.MB_USERNAME, cfg.MB_PASSWORD, cfg.MB_SITE)

"""

CREATE TABLE bot_wp_artist_link (
    gid uuid NOT NULL,
    lang character varying(2),
    processed timestamp with time zone DEFAULT now()
);

ALTER TABLE ONLY bot_wp_artist_link
    ADD CONSTRAINT bot_wp_artist_link_pkey PRIMARY KEY (gid, lang);

CREATE VIEW v_artist_rgs AS
    SELECT acn.artist, count(*) AS count FROM (s_release_group rg JOIN artist_credit_name acn ON ((rg.artist_credit = acn.artist_credit))) WHERE (acn.artist > 2) GROUP BY acn.artist;

select a.id, ar.count into tmp_artists_with_wikipedia
from s_artist a join v_artist_rgs ar on a.id=ar.artist
left join l_artist_url l on l.entity0=a.id and
l.link in (select id from link where link_type=179) where a.id >2 and l.id is null;

SELECT a.id, a.gid, a.name
    FROM s_artist a
    JOIN v_artist_rgs ar ON a.id = ar.artist
    LEFT JOIN l_artist_url l ON l.entity0 = a.id AND l.link IN (SELECT id FROM link WHERE link_type=179)
WHERE a.id > 2 AND l.id IS NULL
ORDER BY ar.count DESC
LIMIT 1000
"""

acceptable_countries_for_lang = {
    'en': [],
    'fr': ['FR', 'MC']
}

query = """
WITH
    artists_wo_wikipedia AS (
        SELECT DISTINCT a.id
        FROM artist a
        LEFT JOIN country c ON c.id = a.country
            AND c.iso_code IN ("""+ ', '.join('%s' for unused in acceptable_countries_for_lang[wp_lang]) +""")
        LEFT JOIN l_artist_url l ON
            l.entity0 = a.id AND
            l.link IN (SELECT id FROM link WHERE link_type = 179)
        WHERE a.id > 2 AND l.id IS NULL
            AND (c.iso_code IS NOT NULL OR %s = 'en')
    )
SELECT a.id, a.gid, a.name
FROM artists_wo_wikipedia ta
JOIN s_artist a ON ta.id=a.id
LEFT JOIN bot_wp_artist_link b ON a.gid = b.gid AND b.lang = %s
WHERE b.gid IS NULL
ORDER BY a.id
LIMIT 10000
"""

query_artist_albums = """
SELECT rg.name
FROM s_release_group rg
JOIN artist_credit_name acn ON rg.artist_credit = acn.artist_credit
WHERE acn.artist = %s
UNION
SELECT r.name
FROM s_release r
JOIN artist_credit_name acn ON r.artist_credit = acn.artist_credit
WHERE acn.artist = %s
"""

params = []
params.extend(acceptable_countries_for_lang[wp_lang])
params.extend((wp_lang, wp_lang))
for a_id, a_gid, a_name in db.execute(query, params):
    out('Looking up artist "%s" http://musicbrainz.org/artist/%s' % (a_name, a_gid))
    matches = wps.query(a_name, defType='dismax', qf='name', rows=50).results
    last_wp_request = time.time()
    for match in matches:
        title = match['name']
        if title.endswith('album)') or title.endswith('song)'):
            continue
        if mangle_name(re.sub(' \(.+\)$', '', title)) != mangle_name(a_name) and mangle_name(title) != mangle_name(a_name):
            continue
        delay = time.time() - last_wp_request
        if delay < 1.0:
            time.sleep(1.0 - delay)
        last_wp_request = time.time()
        resp = wp.call({'action': 'query', 'prop': 'revisions', 'titles': title.encode('utf8'), 'rvprop': 'content'})
        pages = resp['query']['pages'].values()
        if not pages or 'revisions' not in pages[0]:
            continue
        page = mangle_name(pages[0]['revisions'][0].values()[0])
        if 'redirect' in page:
            out(' * redirect page, skipping')
            continue
        if 'disambiguationpages' in page or 'infoboxalbum' in page or 'homonymie' in page:
            out(' * disambiguation or album page, skipping')
            continue
        out(' * trying article "%s"' % (title,))
        page_title = pages[0]['title']
        found_albums = []
        albums = set([r[0] for r in db.execute(query_artist_albums, (a_id, a_id))])
        albums_to_ignore = set()
        for album in albums:
            if mangle_name(a_name) in mangle_name(album):
                albums_to_ignore.add(album)
        albums -= albums_to_ignore
        if not albums:
            continue
        for album in albums:
            mangled_album = mangle_name(album)
            if len(mangled_album) > 10 and mangled_album in page:
                found_albums.append(album)
        ratio = len(found_albums) * 1.0 / len(albums)
        out(' * ratio: %s, has albums: %s, found albums: %s' % (ratio, len(albums), len(found_albums)))
        min_ratio = 0.15 if len(a_name) > 15 else 0.3
        if ratio < min_ratio:
            continue
        url = 'http://'+wp_lang+'.wikipedia.org/wiki/%s' % (urllib.quote(page_title.encode('utf8').replace(' ', '_')),)
        text = 'Matched based on the name. The page mentions %s.' % (join_names('album', found_albums),)
        out(' * linking to %s' % (url,))
        out(' * edit note: %s' % (text,))
        time.sleep(60 * 3)
        mb.add_url("artist", a_gid, 179, url, text)
        break
    db.execute("INSERT INTO bot_wp_artist_link (gid, lang) VALUES (%s, %s)", (a_gid,wp_lang))

