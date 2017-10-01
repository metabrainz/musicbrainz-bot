import mechanize
import urllib
import urllib2
import time
import re
import os
import random
import string
import json
import tempfile
import hashlib
import base64
from utils import structureToString, colored_out
from datetime import datetime
from mbbot.guesscase import guess_artist_sort_name

# Optional modules
try:
    from selenium import webdriver
    from selenium.webdriver.common.keys import Keys
    from selenium.webdriver.support import expected_conditions as EC
    from selenium.webdriver.common.by import By
    from selenium.webdriver.support.ui import WebDriverWait
    from selenium.common.exceptions import NoSuchElementException, ElementNotVisibleException
except ImportError as err:
    colored_out(bcolors.WARNING, "Warning: Cannot use Selenium Webdriver client: %s" % err)
    webdriver = None

try:
    from pyvirtualdisplay import Display
except ImportError as err:
    colored_out(bcolors.WARNING, "Warning: Cannot run Selenium Webdriver client in headless mode: %s" % err)
    Display = None

def format_time(secs):
    return '%0d:%02d' % (secs // 60, secs % 60)


def album_to_form(album):
    form = {}
    form['artist_credit.names.0.artist.name'] = album['artist']
    form['artist_credit.names.0.name'] = album['artist']
    if album.get('artist_mbid'):
        form['artist_credit.names.0.mbid'] = album['artist_mbid']
    form['name'] = album['title']
    if album.get('date'):
        date_parts = album['date'].split('-')
        if len(date_parts) > 0:
            form['date.year'] = date_parts[0]
            if len(date_parts) > 1:
                form['date.month'] = date_parts[1]
                if len(date_parts) > 2:
                    form['date.day'] = date_parts[2]
    if album.get('label'):
        form['labels.0.name'] = album['label']
    if album.get('barcode'):
        form['barcode'] = album['barcode']
    for medium_no, medium in enumerate(album['mediums']):
        form['mediums.%d.format' % medium_no] = medium['format']
        form['mediums.%d.position' % medium_no] = medium['position']
        for track_no, track in enumerate(medium['tracks']):
            form['mediums.%d.track.%d.position' % (medium_no, track_no)] = track['position']
            form['mediums.%d.track.%d.name' % (medium_no, track_no)] = track['title']
            form['mediums.%d.track.%d.length' % (medium_no, track_no)] = format_time(track['length'])
    form['edit_note'] = 'http://www.cdbaby.com/cd/' + album['_id'].split(':')[1]
    return form


class MusicBrainzClient(object):

    def __init__(self, username, password, server="http://musicbrainz.org", editor_id=None):
        self.server = server
        self.username = username
        self.editor_id = editor_id
        self.b = mechanize.Browser()
        self.b.set_handle_robots(False)
        self.b.set_debug_redirects(False)
        self.b.set_debug_http(False)
        self.b.addheaders = [('User-agent', 'musicbrainz-bot/1.0 ( %s/user/%s )' % (server, username))]
        self.login(username, password)

    def url(self, path, **kwargs):
        query = ''
        if kwargs:
            query = '?' + urllib.urlencode([(k, v.encode('utf8')) for (k, v) in kwargs.items()])
        return self.server + path + query

    def _select_form(self, action):
        self.b.select_form(predicate=lambda f: f.method.lower() == "post" and action in f.action)

    def login(self, username, password):
        self.b.open(self.url("/login"))
        self._select_form("/login")
        self.b["username"] = username
        self.b["password"] = password
        self.b.submit()
        resp = self.b.response()
        if resp.geturl() != self.url("/user/" + urllib.quote(username)):
            raise Exception('unable to login')

    # return number of edits that left for today
    def edits_left(self, max_edits=1000):
        if self.editor_id is None:
            print 'error, pass editor_id to constructor for edits_left()'
            return 0
        today = datetime.utcnow().strftime('%Y-%m-%d')
        kwargs = {
                'page': '2000',
                'combinator': 'and',
                'negation': '0',
                'conditions.0.field': 'open_time',
                'conditions.0.operator': '>',
                'conditions.0.args.0': today,
                'conditions.0.args.1': '',
                'conditions.1.field': 'editor',
                'conditions.1.operator': '=',
                'conditions.1.name': self.username,
                'conditions.1.args.0': str(self.editor_id)
        }
        url = self.url("/search/edits", **kwargs)
        self.b.open(url)
        page = self.b.response().read()
        m = re.search(r'Found (?:at least )?([0-9]+(?:,[0-9]+)?) edits', page)
        if not m:
            print 'error, could not determine remaining edits'
            return 0
        return max_edits - int(re.sub(r'[^0-9]+', '', m.group(1)))

    def _extract_mbid(self, entity_type):
        m = re.search(r'/' + entity_type + r'/([0-9a-f-]{36})$', self.b.geturl())
        if m is None:
            raise Exception('unable to post edit')
        return m.group(1)

    def add_release(self, album, edit_note, auto=False):
        form = album_to_form(album)
        self.b.open(self.url("/release/add"), urllib.urlencode(form))
        time.sleep(2.0)
        self._select_form("/release")
        self.b.submit(name="step_editnote")
        time.sleep(2.0)
        self._select_form("/release")
        print self.b.response().read()
        self.b.submit(name="save")
        return self._extract_mbid('release')

    def add_artist(self, artist, edit_note, auto=False):
        self.b.open(self.url("/artist/create"))
        self._select_form("/artist/create")
        self.b["edit-artist.name"] = artist['name']
        self.b["edit-artist.sort_name"] = artist.get('sort_name', guess_artist_sort_name(artist['name']))
        self.b["edit-artist.edit_note"] = edit_note.encode('utf8')
        self.b.submit()
        return self._extract_mbid('artist')

    def _as_auto_editor(self, prefix, auto):
        try:
            self.b[prefix + "make_votable"] = [] if auto else ["1"]
        except mechanize.ControlNotFoundError:
            pass

    def _check_response(self, already_done_msg='any changes to the data already present'):
        page = self.b.response().read()
        if "Thank you, your " not in page:
            if not already_done_msg or already_done_msg not in page:
                raise Exception('unable to post edit')
            else:
                return False
        return True

    def _edit_note_and_auto_editor_and_submit_and_check_response(self, prefix, auto, edit_note, already_done_msg='default'):
        self.b[prefix + "edit_note"] = edit_note.encode('utf8')
        self._as_auto_editor(prefix, auto)
        self.b.submit()
        if already_done_msg != 'default':
            return self._check_response(already_done_msg)
        else:
            return self._check_response()

    def _relationship_editor_webservice_action(self, action, rel_id, link_type, edit_note, auto, entity0, entity1, attributes={}, begin_date={}, end_date={}):
        if (action == "edit" or action == "delete") and rel_id is None:
            raise Exception('Can''t ' + action + ' relationship: no Id has been provided')
        prefix = "rel-editor."
        dta = {prefix + "rels.0.action": action,
             prefix + "rels.0.link_type": link_type,
             prefix + "edit_note": edit_note.encode('utf-8'),
             prefix + "make_votable": not auto and 1 or 0}
        if rel_id:
            dta[prefix + "rels.0.id"] = rel_id
        entities = sorted([entity0, entity1], key=lambda entity: entity['type'])
        dta.update((prefix + "rels.0.entity." + `x`+"." + k, v) for x in xrange(2) for (k, v) in entities[x].iteritems())
        dta.update((prefix + "rels.0.attrs." + k, str(v)) for k, v in attributes.items())
        dta.update((prefix + "rels.0.period.begin_date." + k, str(v)) for k, v in begin_date.items())
        dta.update((prefix + "rels.0.period.end_date." + k, str(v)) for k, v in end_date.items())
        try:
            self.b.open(self.url("/relationship-editor"), data=urllib.urlencode(dta))
        except urllib2.HTTPError, e:
            if e.getcode() != 400:
                raise Exception('unable to post edit', e)
        try:
            jmsg = json.load(self.b.response())
        except ValueError, e:
            raise Exception('unable to parse response as JSON', e)
        if not jmsg.has_key('edits') or jmsg.has_key('error'):
            raise Exception('unable to post edit', jmsg)
        else:
            if jmsg["edits"][0]["message"] == "no changes":
                return False
        return True

    def add_url(self, entity_type, entity_id, link_type, url, edit_note='', auto=False):
        return self._relationship_editor_webservice_action(
            "add", None, link_type, edit_note, auto,
            {"gid": entity_id, "type": entity_type},
            {"url": url, "type": "url"})

    def _update_entity_if_not_set(self, update, entity_dict, entity_type, item, suffix="_id", utf8ize=False, inarray=False):
        if item in update:
            key = "edit-" + entity_type + "." + item + suffix
            if self.b[key] != (inarray and [''] or ''):
                print " * " + item + " already set, not changing"
                return False
            val = (
                utf8ize and entity_dict[item].encode('utf-8') or str(entity_dict[item]))
            self.b[key] = (inarray and [val] or val)
        return True

    def _update_artist_date_if_not_set(self, update, artist, item_prefix):
        item = item_prefix + '_date'
        if item in update:
            prefix = "edit-artist.period." + item
            if self.b[prefix + ".year"]:
                print " * " + item.replace('_', ' ') + " year already set, not changing"
                return False
            self.b[prefix + ".year"] = str(artist[item + '_year'])
            if artist[item + '_month']:
                self.b[prefix + ".month"] = str(artist[item + '_month'])
                if artist[item + '_day']:
                    self.b[prefix + ".day"] = str(artist[item + '_day'])
        return True

    def edit_artist(self, artist, update, edit_note, auto=False):
        self.b.open(self.url("/artist/%s/edit" % (artist['gid'],)))
        self._select_form("/edit")
        self.b.set_all_readonly(False)
        if not self._update_entity_if_not_set(update, artist, 'artist', 'area'):
            return
        for item in ['type', 'gender']:
            if not self._update_entity_if_not_set(update, artist, 'artist', item, inarray=True):
                return
        for item_prefix in ['begin', 'end']:
            if not self._update_artist_date_if_not_set(update, artist, item_prefix):
                return
        if not self._update_entity_if_not_set(update, artist, 'artist', 'comment', '', utf8ize=True):
            return
        return self._edit_note_and_auto_editor_and_submit_and_check_response('edit-artist.', auto, edit_note)

    def edit_artist_credit(self, entity_id, credit_id, ids, names, join_phrases, edit_note):
        assert len(ids) == len(names) == len(join_phrases) + 1
        join_phrases.append('')

        self.b.open(self.url("/artist/%s/credit/%d/edit" % (entity_id, int(credit_id))))
        self._select_form("/edit")

        for i in range(len(ids)):
            for field in ['artist.id', 'artist.name', 'name', 'join_phrase']:
                k = "split-artist.artist_credit.names.%d.%s" % (i, field)
                try:
                    self.b.form.find_control(k).readonly = False
                except mechanize.ControlNotFoundError:
                    self.b.form.new_control('text', k, {})
        self.b.fixup()

        for i, aid in enumerate(ids):
            self.b["split-artist.artist_credit.names.%d.artist.id" % i] = str(int(aid))
        # Form also has "split-artist.artist_credit.names.%d.artist.name", but it is not required
        for i, name in enumerate(names):
            self.b["split-artist.artist_credit.names.%d.name" % i] = name.encode('utf-8')
        for i, join in enumerate(join_phrases):
            self.b["split-artist.artist_credit.names.%d.join_phrase" % i] = join.encode('utf-8')

        self.b["split-artist.edit_note"] = edit_note.encode('utf-8')
        self.b.submit()
        return self._check_response()

    def set_artist_type(self, entity_id, type_id, edit_note, auto=False):
        self.b.open(self.url("/artist/%s/edit" % (entity_id,)))
        self._select_form("/edit")
        if self.b["edit-artist.type_id"] != ['']:
            print " * already set, not changing"
            return
        self.b["edit-artist.type_id"] = [str(type_id)]
        return self._edit_note_and_auto_editor_and_submit_and_check_response('edit-artist.', auto, edit_note)

    def edit_url(self, entity_id, old_url, new_url, edit_note, auto=False):
        self.b.open(self.url("/url/%s/edit" % (entity_id,)))
        self._select_form("/edit")
        if self.b["edit-url.url"] != str(old_url):
            print " * value has changed, aborting"
            return
        if self.b["edit-url.url"] == str(new_url):
            print " * already set, not changing"
            return
        self.b["edit-url.url"] = str(new_url)
        return self._edit_note_and_auto_editor_and_submit_and_check_response('edit-url.', auto, edit_note)

    def edit_work(self, work, update, edit_note, auto=False):
        self.b.open(self.url("/work/%s/edit" % (work['gid'],)))
        self._select_form("/edit")
        for item in ['type', 'language']:
            if not self._update_entity_if_not_set(update, work, 'work', item, inarray=True):
                return
        if not self._update_entity_if_not_set(update, work, 'work', 'comment', '', utf8ize=True):
            return
        return self._edit_note_and_auto_editor_and_submit_and_check_response('edit-work.', auto, edit_note)

    def edit_relationship(self, rel_id, entity0, entity1, link_type, attributes, begin_date, end_date, edit_note, auto=False):
        return self._relationship_editor_webservice_action('edit', rel_id, link_type, edit_note, auto, entity0, entity1, attributes, begin_date, end_date)

    def remove_relationship(self, rel_id, entity0_type, entity1_type, edit_note):
        self.b.open(self.url("/edit/relationship/delete", id=str(rel_id), type0=entity0_type, type1=entity1_type))
        self._select_form("/edit")
        self.b["confirm.edit_note"] = edit_note.encode('utf8')
        self.b.submit()
        self._check_response(None)

    def merge(self, entity_type, entity_ids, target_id, edit_note):
        params = [('add-to-merge', id) for id in entity_ids]
        self.b.open(self.url("/%s/merge_queue" % entity_type), urllib.urlencode(params))
        page = self.b.response().read()
        if "You are about to merge" not in page:
            raise Exception('unable to add items to merge queue')

        params = {'merge.target': target_id, 'submit': 'submit', 'merge.edit_note': edit_note}
        for idx, val in enumerate(entity_ids):
            params['merge.merging.%s' % idx] = val
        self.b.open(self.url("/%s/merge" % entity_type), urllib.urlencode(params))
        self._check_response(None)

    def _edit_release_information(self, entity_id, attributes, edit_note, auto=False):
        self.b.open(self.url("/release/%s/edit" % (entity_id,)))
        self._select_form("/edit")
        changed = False
        for k, v in attributes.items():
            self.b.form.find_control(k).readonly = False
            if self.b[k] != v[0] and v[0] is not None:
                print " * %s has changed to %r, aborting" % (k, self.b[k])
                return False
            if self.b[k] != v[1]:
                changed = True
                self.b[k] = v[1]
        if not changed:
            print " * already set, not changing"
            return False
        self.b["barcode_confirm"] = ["1"]
        self.b.submit(name="step_editnote")
        page = self.b.response().read()
        self._select_form("/edit")
        try:
            self.b["edit_note"] = edit_note.encode('utf8')
        except mechanize.ControlNotFoundError:
            raise Exception('unable to post edit')
        self._as_auto_editor("", auto)
        self.b.submit(name="save")
        page = self.b.response().read()
        if "Release information" not in page:
            raise Exception('unable to post edit')
        return True

    def set_release_script(self, entity_id, old_script_id, new_script_id, edit_note, auto=False):
        return self._edit_release_information(entity_id, {"script_id": [[str(old_script_id)], [str(new_script_id)]]}, edit_note, auto)

    def set_release_language(self, entity_id, old_language_id, new_language_id, edit_note, auto=False):
        return self._edit_release_information(entity_id, {"language_id": [[str(old_language_id)], [str(new_language_id)]]}, edit_note, auto)

    def set_release_packaging(self, entity_id, old_packaging_id, new_packaging_id, edit_note, auto=False):
        old_packaging = [str(old_packaging_id)] if old_packaging_id is not None else None
        return self._edit_release_information(entity_id, {"packaging_id": [old_packaging, [str(new_packaging_id)]]}, edit_note, auto)

    def add_edit_note(self, identify, edit_note):
        '''Adds an edit note to the last (or very recently) made edit. This
        is necessary e.g. for ISRC submission via web service, as it has no
        support for edit notes. The "identify" argument is a function
            function(str, str) -> bool
        which receives the edit number as first, the raw html body of the edit
        as second argument, and determines if the note should be added to this
        edit.'''
        self.b.open(self.url("/user/%s/edits" % (self.username,)))
        page = self.b.response().read()
        self._select_form("/edit")
        edits = re.findall(r'<h2><a href="' + self.server + r'/edit/([0-9]+).*?<div class="edit-details">(.*?)</div>', page, re.S)
        for i, (edit_nr, text) in enumerate(edits):
            if identify(edit_nr, text):
                self.b['enter-vote.vote.%d.edit_note' % i] = edit_note.encode('utf8')
                break
        self.b.submit()

    def cancel_edit(self, edit_nr, edit_note=u''):
        self.b.open(self.url("/edit/%s/cancel" % (edit_nr,)))
        page = self.b.response().read()
        self._select_form("/cancel")
        if edit_note:
            self.b['confirm.edit_note'] = edit_note.encode('utf8')
        self.b.submit()

class MusicBrainzWebdriverClient(object):

    def __init__(self, username, password, server="http://musicbrainz.org", editor_id=None, headless=True):
        if headless and Display is not None:
            self.display = Display(visible=0, size=(800, 600))
            self.display.start()
        if webdriver is None:
            raise Exception('Selenium webdriver is not installed')
        self.server = server
        self.username = username
        self.editor_id = editor_id
        self.driver = webdriver.Firefox()
        self.login(username, password)
        self.wait = WebDriverWait(self.driver, 60)

    def __del__(self):
        self.driver.quit()
        if hasattr(self, 'display') and self.display is not None:
            self.display.popen.terminate()

    def url(self, path, **kwargs):
        query = ''
        if kwargs:
            query = '?' + urllib.urlencode([(k, v.encode('utf8')) for (k, v) in kwargs.items()])
        return self.server + path + query

    def login(self, username, password):
        self.driver.get(self.url("/login"))
        self.driver.find_element_by_name("username").send_keys(username)
        passwordField = self.driver.find_element_by_name("password")
        passwordField.send_keys(password)
        passwordField.submit()
        if self.driver.current_url != self.url("/user/" + urllib.quote(username)):
            raise Exception('unable to login')

    def _as_auto_editor(self, prefix, auto):
        if not auto:
            self.driver.find_element_by_name(prefix + ".make_votable").click()

    def _enter_edit_note(self, edit_note):
        textarea = None
        try:
            textarea = self.driver.find_element_by_xpath("//textarea[@class='edit-note']")
        except NoSuchElementException:
            try:
                textarea = self.driver.find_element_by_id('edit-note-text')
            except NoSuchElementException:
                pass
        if textarea is not None:
            textarea.send_keys(edit_note.encode('utf8'))
        else:
            print " * No textarea found for edit note!"

    def _submit_and_wait(self, submitButton):
        submitButton.click()
        self.wait.until(EC.staleness_of(submitButton))

    def _exist_errors_in_release_editor(self):
        tabs = self.driver.find_elements_by_xpath("//ul[@role='tablist']//li")
        for tab in tabs:
            if 'error-tab' in tab.get_attribute('class'):
                return True

    def add_cover_art(self, release_gid, image, types=[], position=None, comment=u'', edit_note=u'', auto=False):
        # Download image if it is remote
        image_is_remote = True if image.startswith(('http://', 'https://', 'ftp://')) else False
        if image_is_remote:
            u = urllib2.urlopen(image)
            tmpfile = tempfile.NamedTemporaryFile(delete=False)
            tmpfile.write(u.read())
            tmpfile.close()
            localFile = tmpfile.name
        else:
            localFile = os.path.abspath(image)

        self.driver.get(self.url("/release/%s/add-cover-art" % (release_gid,)))
        # Select image
        self.driver.execute_script("$('input[type=file]').css('left', 0);") # Selenium needs the file selector to be visible
        self.driver.find_element_by_xpath("//input[@type='file']").send_keys(localFile)
        # Set types
        typeLabels = self.driver.find_elements_by_xpath("//div[@class='cover-art-types row']//ul//label")
        for type in types:
            for label in typeLabels:
                if label.find_element_by_tag_name('span').text.lower() == type.lower():
                    label.click()
                    break
        # Set comment
        self.driver.find_element_by_xpath("//input[@class='comment']").send_keys(comment.encode('utf8'))
        # Set edit note
        self._enter_edit_note(edit_note)
        # Auto-edit
        self._as_auto_editor('add-cover-art', auto)
        # Submit
        submitButton = self.driver.find_element_by_id("add-cover-art-submit")
        self._submit_and_wait(submitButton)
        # Remove downloaded file
        if image_is_remote:
            os.remove(localFile)

    def _release_editor_prerequisites_are_satisfied(self):
        # Disable confirmation when exiting this page
        self.driver.execute_script("window.onbeforeunload = function(e){};")
        # Confirm barcode, if required
        self.wait.until(EC.presence_of_element_located((By.ID, "barcode")))
        try:
            self.driver.find_element_by_id("barcode").click()
            self.driver.find_element_by_xpath("//input[contains(@data-bind, 'confirmed')]").click()
        except (NoSuchElementException, ElementNotVisibleException) as e:
            pass
        # Check that there are no preexisting errors that would prevent submitting the changes
        if self._exist_errors_in_release_editor():
            print " * can't edit this release, it has preexisting errors"
            return False
        return True

    def set_release_medium_format(self, entity_id, medium_id, new_format_id, edit_note, auto=False):
        self.driver.get(self.url("/release/%s/edit" % (entity_id,)))
        if not self._release_editor_prerequisites_are_satisfied():
            return
        # Open Tracklist tab
        self.driver.find_element_by_xpath("//a[@href='#tracklist']").click()
        # Set format
        xpath = "//select[@id='disc-format-%s']//option[@value='%s']" % (medium_id, new_format_id)
        self.wait.until(EC.presence_of_element_located((By.XPATH, xpath)))
        self.driver.find_element_by_xpath(xpath).click()
        # Check that setting new format doesn't generate error (e.g. setting format to Vinyl if discid is present)
        errorTDs = self.driver.find_elements_by_xpath("//tr[@class='error']//td[contains(@data-bind, 'hasInvalidFormat')]")
        for errorTD in errorTDs:
            if errorTD.is_displayed():
                print " * has a discid => medium format can't be set to a format that can't have disc IDs"
                return
        # Open Edit Note tab
        self.driver.find_element_by_xpath("//a[@href='#edit-note']").click()
        # Set edit note
        self._enter_edit_note(edit_note)
        # Auto-edit
        if not auto:
            self.driver.find_element_by_xpath("//input[@data-bind='checked: makeVotable']").click()
        # Submit
        xpath = "//button[@data-click='submitEdits']"
        self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        submitButton = self.driver.find_element_by_xpath(xpath)
        self._submit_and_wait(submitButton)

    def edit_release_tracklisting(self, entity_id, mediums, edit_note=u'', auto=False):
        """
        Edit a release tracklisting. Doesn't handle adding/deleting tracks. Track ids are mandatory.
        Each medium object may contain the following properties: tracklist. (position, format, name could be added later if needed)
        Each track object may contain the following properties: length, number.
        """
        self.driver.get(self.url("/release/%s/edit" % (entity_id,)))
        self.wait = WebDriverWait(self.driver, 60)
        if not self._release_editor_prerequisites_are_satisfied():
            return
        # Open Tracklist tab
        self.driver.find_element_by_xpath("//a[@href='#tracklist']").click()
        for medium_no, medium in enumerate(mediums):
            if 'tracklist' in medium:
                # Load medium if required
                disc_button = self.driver.find_element_by_xpath("((//fieldset[@class='advanced-disc'])[%s]//td[@class='icon'])[1]//button" % (medium_no+1))
                if 'expand' in disc_button.get_attribute('class'):
                    disc_button.click()
                for track in medium['tracklist']:
                    if 'id' not in track:
                        print " * track id is required"
                        return
                    self.wait.until(EC.presence_of_element_located((By.ID, "track-row-%s" % track['id'])))
                    if 'number' in track:
                        input = self.driver.find_element_by_xpath("//tr[@id='track-row-%s']//td[@class='position']//input" % track['id'])
                        input.clear()
                        input.send_keys(track['number'])
                    if 'length' in track:
                        input = self.driver.find_element_by_xpath("//tr[@id='track-row-%s']//td[@class='length']//input" % track['id'])
                        input.clear()
                        input.send_keys(track['length'])
        # Open Edit Note tab
        self.driver.find_element_by_xpath("//a[@href='#edit-note']").click()
        # Set edit note
        self._enter_edit_note(edit_note)
        # Auto-edit
        if not auto:
            self.driver.find_element_by_xpath("//input[@data-bind='checked: makeVotable']").click()
        # Submit
        xpath = "//button[@data-click='submitEdits']"
        self.wait.until(EC.element_to_be_clickable((By.XPATH, xpath)))
        submitButton = self.driver.find_element_by_xpath(xpath)
        self._submit_and_wait(submitButton)
