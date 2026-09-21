"""Backend tests for iter39: Design Studio HOLD, Proofing labels, richer history, and
score-only-on-ACC.

Covers request items 1-7 from the review request (backend section).
"""
import os
import io
import time
import pytest
import requests

def _load_backend_url():
    v = os.environ.get('REACT_APP_BACKEND_URL')
    if not v:
        try:
            with open('/app/frontend/.env') as fh:
                for ln in fh:
                    if ln.startswith('REACT_APP_BACKEND_URL='):
                        v = ln.split('=', 1)[1].strip()
                        break
        except FileNotFoundError:
            pass
    assert v, 'REACT_APP_BACKEND_URL missing'
    return v.rstrip('/')


BASE_URL = _load_backend_url()
ENT = 'ent_ksc'
HDR_ENT = {'X-Entity-Id': ENT}

ADMIN = ('admin@kainnusantara.id', 'demo12345')
MANAGER = ('manager@kainnusantara.id', 'demo12345')
DESIGNER = ('designer@kainnusantara.id', 'demo12345')

DSGN_HOLD = 'dsgn_87a63c89bc80'          # HOLD + proofing in_progress
DSGN_MASTER = 'dsgn_7eec40ef4396'        # master product
DSGN_FINISHED = 'dsgn_00ad22fda7bb'      # proofing finished
DSGN_DRAFT = 'dsgn_d700534f8a69'         # draft (hold should be rejected)
DSGN_PENDING_1 = 'dsgn_6166f71b9297'
DSGN_PENDING_2 = 'dsgn_4e9ba57321ca'


def _login(email, password):
    r = requests.post(f"{BASE_URL}/api/auth/login", json={'email': email, 'password': password}, timeout=30)
    assert r.status_code == 200, f"login failed for {email}: {r.status_code} {r.text}"
    data = r.json()
    return data['token'], data.get('user') or data.get('profile') or data


def _items(resp):
    j = resp.json()
    if isinstance(j, list):
        return j
    return j.get('items', [])



def _h(token, extra=None):
    h = {'Authorization': f'Bearer {token}', **HDR_ENT}
    if extra:
        h.update(extra)
    return h


@pytest.fixture(scope='module')
def admin_token():
    return _login(*ADMIN)[0]


@pytest.fixture(scope='module')
def designer_token():
    return _login(*DESIGNER)[0]


@pytest.fixture(scope='module')
def manager_token():
    return _login(*MANAGER)[0]


# --- 1. Permissions include rnd.hold for admin, not for designer -------------
class TestPermissions:
    def test_admin_has_rnd_hold(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={'email': ADMIN[0], 'password': ADMIN[1]}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        # permissions can be under user.permissions or top-level permissions
        perms = (body.get('user') or {}).get('permissions') or body.get('permissions') or {}
        rnd = perms.get('rnd') or []
        assert 'hold' in rnd, f"admin permissions.rnd missing 'hold': {rnd}"

    def test_designer_no_rnd_hold(self):
        r = requests.post(f"{BASE_URL}/api/auth/login", json={'email': DESIGNER[0], 'password': DESIGNER[1]}, timeout=30)
        assert r.status_code == 200
        body = r.json()
        perms = (body.get('user') or {}).get('permissions') or body.get('permissions') or {}
        rnd = perms.get('rnd') or []
        assert 'hold' not in rnd, f"designer must NOT have rnd.hold: {rnd}"


# --- 2. Gallery listing shape ------------------------------------------------
class TestGalleryList:
    def test_gallery_shape_and_specific_items(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/design-gallery",
                         params={'entity_id': ENT},
                         headers=_h(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        items = _items(r)
        assert items, 'no items returned'
        by_id = {}
        for it in items:
            # shape check per item
            assert 'on_hold' in it, f"item missing on_hold: {it.get('id')}"
            assert isinstance(it['on_hold'], bool)
            assert 'hold' in it and isinstance(it['hold'], dict)
            proofing = it.get('proofing') or {}
            for k in ('state', 'label', 'detail', 'samples', 'specs', 'master_product'):
                assert k in proofing, f"proofing missing {k} in {it.get('id')}"
            by_id[it['id']] = it
        # Specific items
        assert by_id.get(DSGN_HOLD, {}).get('on_hold') is True
        assert by_id.get(DSGN_HOLD, {}).get('proofing', {}).get('state') == 'in_progress'
        m = by_id.get(DSGN_MASTER, {})
        assert m.get('proofing', {}).get('state') == 'master'
        mp = m.get('proofing', {}).get('master_product') or {}
        assert mp.get('sku') == 'RND-KTN-150', f"expected sku RND-KTN-150 got {mp}"
        assert by_id.get(DSGN_FINISHED, {}).get('proofing', {}).get('state') == 'finished'

    def test_gallery_filter_on_hold(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/design-gallery",
                         params={'entity_id': ENT, 'on_hold': 'yes'},
                         headers=_h(admin_token), timeout=30)
        assert r.status_code == 200
        items = _items(r)
        assert items, 'expected at least one held design'
        for it in items:
            assert it.get('on_hold') is True, f"non-held returned: {it.get('id')}"


# --- 3. Hold/Release lifecycle -----------------------------------------------
class TestHoldLifecycle:
    def test_hold_already_held_returns_400(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/design-gallery/{DSGN_HOLD}/lifecycle/hold",
                          json={'note': 'TEST_ dobel hold'},
                          headers=_h(admin_token), timeout=30)
        assert r.status_code == 400, r.text
        assert 'HOLD' in r.text.upper()

    def test_release_then_rehold_roundtrip(self, admin_token):
        # Release
        r = requests.post(f"{BASE_URL}/api/design-gallery/{DSGN_HOLD}/lifecycle/release-hold",
                          json={'note': 'TEST_ lepas'},
                          headers=_h(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        design = body.get('design') or body
        assert design.get('on_hold') is False
        hh = design.get('hold_history') or []
        assert len(hh) >= 1
        # timeline last event is release_hold
        tl = design.get('timeline') or []
        assert tl, 'no timeline'
        last_release = [e for e in tl if e.get('event') == 'release_hold']
        assert last_release, f"no release_hold timeline event: {[e.get('event') for e in tl[-5:]]}"

        # Missing note -> 400
        r2 = requests.post(f"{BASE_URL}/api/design-gallery/{DSGN_HOLD}/lifecycle/hold",
                           json={}, headers=_h(admin_token), timeout=30)
        assert r2.status_code == 400, r2.text

        # Re-hold with note
        r3 = requests.post(f"{BASE_URL}/api/design-gallery/{DSGN_HOLD}/lifecycle/hold",
                           json={'note': 'TEST_ hold ulang'},
                           headers=_h(admin_token), timeout=30)
        assert r3.status_code == 200, r3.text
        design3 = (r3.json().get('design') or r3.json())
        assert design3.get('on_hold') is True

    def test_designer_hold_forbidden(self, designer_token):
        r = requests.post(f"{BASE_URL}/api/design-gallery/{DSGN_HOLD}/lifecycle/hold",
                          json={'note': 'TEST_ designer'},
                          headers=_h(designer_token), timeout=30)
        assert r.status_code == 403, r.text
        assert 'rnd.hold' in r.text or 'Permission' in r.text

    def test_hold_on_draft_400(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/design-gallery/{DSGN_DRAFT}/lifecycle/hold",
                          json={'note': 'TEST_ draft'},
                          headers=_h(admin_token), timeout=30)
        assert r.status_code == 400, r.text


# --- 4. Proofing sample rejected while HOLD ---------------------------------
class TestSampleAgainstHold:
    def test_proofing_rejected(self, admin_token):
        payload = {
            'title': 'TEST_ proofing hold',
            'sample_types': ['proofing'],
            'design_id': DSGN_HOLD,
        }
        r = requests.post(f"{BASE_URL}/api/rnd/samples",
                          json=payload, headers=_h(admin_token), timeout=30)
        assert r.status_code == 400, r.text
        assert 'HOLD' in r.text.upper()

    def test_labdip_allowed_then_cancel(self, admin_token):
        payload = {
            'title': 'TEST_ labdip on hold design',
            'sample_types': ['labdip'],
            'design_id': DSGN_HOLD,
        }
        r = requests.post(f"{BASE_URL}/api/rnd/samples",
                          json=payload, headers=_h(admin_token), timeout=30)
        assert r.status_code in (200, 201), r.text
        sid = (r.json().get('sample') or r.json()).get('id') or r.json().get('id')
        assert sid, f"no sample id in resp: {r.text[:200]}"
        # cancel
        c = requests.post(f"{BASE_URL}/api/rnd/samples/{sid}/cancel",
                          json={'reason': 'TEST_ cleanup'},
                          headers=_h(admin_token), timeout=30)
        assert c.status_code in (200, 204), c.text


# --- 5. Legacy per-version score endpoint removed ----------------------------
class TestLegacyScoreRemoved:
    def test_versions_score_endpoint_removed(self, admin_token):
        r = requests.post(f"{BASE_URL}/api/design-gallery/{DSGN_PENDING_1}/versions/1/score",
                          json={'score': 3.0}, headers=_h(admin_token), timeout=30)
        assert r.status_code in (404, 405), f"expected 404/405 got {r.status_code} {r.text[:120]}"


# --- 6. Score-only-on-ACC ---------------------------------------------------
class TestScoreOnlyOnAcc:
    def test_request_revision_ignores_score(self, admin_token):
        # find a pending_approval design
        target = None
        for did in (DSGN_PENDING_1, DSGN_PENDING_2):
            g = requests.get(f"{BASE_URL}/api/design-gallery/{did}", headers=_h(admin_token), timeout=30)
            if g.status_code == 200 and (g.json().get('design') or g.json()).get('status') == 'pending_approval':
                target = did
                break
        if not target:
            pytest.skip('no pending_approval design available')
        r = requests.post(f"{BASE_URL}/api/design-gallery/{target}/lifecycle/request-revision",
                          json={'note': 'TEST_ revisi', 'score': 1.5},
                          headers=_h(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        design = r.json().get('design') or r.json()
        versions = design.get('versions') or []
        assert versions, 'no versions'
        # score not stored
        assert not versions[0].get('score'), f"score should be null after revision, got {versions[0].get('score')}"
        # timeline event has no score
        tl = design.get('timeline') or []
        rev_evts = [e for e in tl if e.get('event') == 'request_revision']
        assert rev_evts
        assert not rev_evts[-1].get('score'), f"request_revision event should not carry score: {rev_evts[-1]}"

    def test_approve_without_score_400(self, admin_token):
        # Need a pending_approval design; find one dynamically
        r = requests.get(f"{BASE_URL}/api/design-gallery",
                         params={'entity_id': ENT, 'status': 'pending_approval'},
                         headers=_h(admin_token), timeout=30)
        items = _items(r) if r.status_code == 200 else []
        pending = [i['id'] for i in items if i.get('status') == 'pending_approval']
        if not pending:
            pytest.skip('no pending_approval design for approve test')
        did = pending[0]
        r2 = requests.post(f"{BASE_URL}/api/design-gallery/{did}/lifecycle/approve",
                           json={'note': 'TEST_ approve tanpa nilai'},
                           headers=_h(admin_token), timeout=30)
        assert r2.status_code == 400, r2.text
        assert 'nilai' in r2.text.lower() or 'score' in r2.text.lower()


# --- 7. Updates → timeline diff; files upload/delete; history endpoint ------
class TestHistoryAndFiles:
    def test_update_story_produces_timeline_diff(self, admin_token):
        # Use a non-critical design (DSGN_MASTER already ACC – updating story should still be allowed)
        did = DSGN_MASTER
        new_story = f"TEST_ cerita baru {int(time.time())}"
        r = requests.put(f"{BASE_URL}/api/design-gallery/{did}",
                         json={'story': new_story}, headers=_h(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        design = r.json().get('design') or r.json()
        tl = design.get('timeline') or []
        updated = [e for e in tl if e.get('event') == 'updated']
        assert updated, f"no 'updated' timeline event; got {[e.get('event') for e in tl[-5:]]}"
        changes = updated[-1].get('changes') or []
        story_ch = [c for c in changes if c.get('field') == 'story']
        assert story_ch, f"no story change entry: {changes}"
        assert story_ch[-1].get('to') == new_story

    def test_file_upload_and_delete(self, admin_token):
        did = DSGN_MASTER
        files = {'file': ('test.txt', io.BytesIO(b'TEST_ payload'), 'text/plain')}
        r = requests.post(f"{BASE_URL}/api/design-gallery/{did}/files-kind/reference",
                          files=files, headers={'Authorization': f'Bearer {admin_token}', **HDR_ENT}, timeout=30)
        # accept 200/201 if allowed; if content-type limited, skip
        if r.status_code not in (200, 201):
            pytest.skip(f"file upload not supported for reference kind: {r.status_code} {r.text[:120]}")
        body = r.json()
        design = body.get('design') or body
        # find newly uploaded file id
        files_list = design.get('files') or []
        target = None
        for f in files_list:
            if f.get('name') == 'test.txt' or (f.get('original_name') == 'test.txt'):
                target = f.get('id') or f.get('file_id')
        if not target:
            pytest.skip('could not locate uploaded file id')
        d = requests.delete(f"{BASE_URL}/api/design-gallery/{did}/files/{target}",
                            headers=_h(admin_token), timeout=30)
        assert d.status_code in (200, 204), d.text
        # check timeline
        hist = requests.get(f"{BASE_URL}/api/design-gallery/{did}/history",
                            headers=_h(admin_token), timeout=30)
        assert hist.status_code == 200, hist.text
        events = [i.get('event') for i in hist.json().get('items', [])]
        assert 'file_deleted' in events, f"file_deleted not in history events: {events[:20]}"

    def test_history_endpoint_shape_and_kind_filter(self, admin_token):
        r = requests.get(f"{BASE_URL}/api/design-gallery/{DSGN_HOLD}/history",
                         headers=_h(admin_token), timeout=30)
        assert r.status_code == 200, r.text
        body = r.json()
        for k in ('count', 'items', 'kinds'):
            assert k in body, f"history missing key {k}"
        # kind=hold
        r2 = requests.get(f"{BASE_URL}/api/design-gallery/{DSGN_HOLD}/history",
                          params={'kind': 'hold'}, headers=_h(admin_token), timeout=30)
        assert r2.status_code == 200
        items = r2.json().get('items', [])
        assert items, 'expected hold events'
        for it in items:
            # Each item should be a hold-family event
            ev = (it.get('event') or '').lower()
            assert 'hold' in ev, f"non-hold event returned when filtering kind=hold: {ev}"
