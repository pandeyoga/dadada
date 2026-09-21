"""ITER-316 — KPI Desainer: 'Tren Nilai Desain' + Bobot Nilai Desain.

Skenario (bahasa Indonesia sesuai review request):
  1. GET designer-kpi → weights.design (default 20), Dewi Lestari design_avg_score≈1.31,
     grade_design_pts≈65.5, grade numerik. Desainer Demo grade numerik (bukan null).
  2. GET designer-kpi/trend?metric=design_score → months=6, scale_max=2, series lengkap.
  3. metric=grade dan metric=avg_score masih 200.
  4. PUT config rnd.kpi_weight_design=50 → grade Dewi Lestari TURUN.
     Set 0 → Dewi NAIK, Desainer Demo grade jadi null. Kembali 20 di akhir.
  5. Ekspor CSV/PDF, report PDF individu, my-kpi 200.
"""
import os
import pytest
import requests

def _read_backend_url():
    v = os.environ.get("REACT_APP_BACKEND_URL")
    if not v:
        try:
            with open("/app/frontend/.env") as f:
                for line in f:
                    if line.startswith("REACT_APP_BACKEND_URL="):
                        v = line.split("=", 1)[1].strip()
                        break
        except OSError:
            pass
    assert v, "REACT_APP_BACKEND_URL kosong"
    return v.rstrip("/")


BASE_URL = _read_backend_url()
ENTITY = "ent_ksc"


# ─── Fixtures ────────────────────────────────────────────────────────────────
@pytest.fixture(scope="module")
def token():
    r = requests.post(f"{BASE_URL}/api/auth/login",
                      json={"email": "admin@kainnusantara.id", "password": "demo12345"},
                      timeout=30)
    assert r.status_code == 200, f"login failed: {r.status_code} {r.text[:200]}"
    tok = r.json().get("token") or r.json().get("access_token")
    assert tok
    return tok


@pytest.fixture(scope="module")
def client(token):
    s = requests.Session()
    s.headers.update({
        "Authorization": f"Bearer {token}",
        "X-Entity-Id": ENTITY,
        "Content-Type": "application/json",
    })
    return s


def _kpi(client, **extra):
    params = {"entity_id": ENTITY, "period": "all", **extra}
    r = client.get(f"{BASE_URL}/api/rnd/reports/designer-kpi", params=params, timeout=30)
    assert r.status_code == 200, f"{r.status_code} {r.text[:200]}"
    return r.json()


def _set_weight(client, value):
    r = client.put(f"{BASE_URL}/api/config/values", params={"entity_id": ENTITY}, json={
        "items": [{"key": "rnd.kpi_weight_design", "value": value,
                   "scope_type": "global", "reason": "uji ITER-316"}]
    }, timeout=30)
    assert r.status_code == 200, f"config PUT {value}: {r.status_code} {r.text[:300]}"


# ─── Reset bobot ke default 20 setelah semua test ────────────────────────────
@pytest.fixture(scope="module", autouse=True)
def _restore_weight(client):
    yield
    try:
        _set_weight(client, 20)
    except Exception as e:
        print(f"WARN: gagal mengembalikan bobot ke 20: {e}")


# ─── 1. Designer KPI dasar ───────────────────────────────────────────────────
class TestDesignerKpiBase:
    def test_weights_and_rows(self, client):
        data = _kpi(client)
        w = data.get("weights") or {}
        assert "design" in w, "weights.design harus ada"
        assert float(w["design"]) == 20.0, f"default design weight harus 20, dapat {w['design']}"

        items = {r["designer"]: r for r in data["items"]}
        assert "Dewi Lestari" in items, f"Dewi Lestari tidak ada. items={list(items)}"
        dewi = items["Dewi Lestari"]
        assert dewi.get("design_avg_score") is not None
        assert abs(float(dewi["design_avg_score"]) - 1.31) < 0.05, dewi["design_avg_score"]
        assert abs(float(dewi["grade_design_pts"]) - 65.5) < 1.0, dewi["grade_design_pts"]
        assert isinstance(dewi["grade_score"], (int, float))
        assert dewi.get("grade_letter") in {"A", "B", "C", "D"}

        # Desainer Demo: hanya nilai desain, grade tetap numerik
        assert "Desainer Demo" in items, f"Desainer Demo tidak ada. items={list(items)}"
        demo = items["Desainer Demo"]
        assert demo["grade_score"] is not None, "grade_score Desainer Demo harus numerik (bukan null)"


# ─── 2. Trend endpoint ───────────────────────────────────────────────────────
class TestDesignerKpiTrend:
    def _trend(self, client, metric, months=6):
        r = client.get(f"{BASE_URL}/api/rnd/reports/designer-kpi/trend",
                       params={"entity_id": ENTITY, "metric": metric, "months": months}, timeout=30)
        assert r.status_code == 200, f"{metric}: {r.status_code} {r.text[:200]}"
        return r.json()

    def test_design_score_trend(self, client):
        data = self._trend(client, "design_score", 6)
        assert data["metric"] == "design_score"
        assert data.get("scale_max") == 2
        assert len(data["months"]) == 6
        assert len(data["month_labels"]) == 6
        assert data["series"], "series kosong"
        for s in data["series"]:
            assert "designer" in s
            pts = s["points"]
            assert len(pts) == 6
            assert any(p["score"] is not None for p in pts), f"{s['designer']} semua null"
            for p in pts:
                assert "month" in p and "versions" in p and "acc" in p

        dewi = next((s for s in data["series"] if s["designer"] == "Dewi Lestari"), None)
        assert dewi, "Dewi Lestari tidak ada di series"
        last4 = [p["score"] for p in dewi["points"][-4:]]
        expected = [0.75, 1.25, 1.5, 1.75]
        for got, exp in zip(last4, expected):
            assert got is not None and abs(float(got) - exp) < 0.1, f"Dewi last4={last4} exp={expected}"

    def test_grade_metric(self, client):
        d = self._trend(client, "grade", 6)
        assert d["metric"] == "grade"
        assert d["series"]

    def test_avg_score_metric(self, client):
        d = self._trend(client, "avg_score", 6)
        assert d["metric"] == "avg_score"
        assert d["series"]


# ─── 3. Bobot desain — dampak ke grade ───────────────────────────────────────
class TestDesignWeightImpact:
    def test_weight_changes(self, client):
        base = _kpi(client)
        base_items = {r["designer"]: r for r in base["items"]}
        dewi_base = base_items["Dewi Lestari"]["grade_score"]
        assert float(base["weights"]["design"]) == 20.0

        # Naikkan bobot ke 50 → grade Dewi TURUN
        _set_weight(client, 50)
        d50 = _kpi(client)
        assert float(d50["weights"]["design"]) == 50.0
        items50 = {r["designer"]: r for r in d50["items"]}
        dewi_50 = items50["Dewi Lestari"]["grade_score"]
        assert dewi_50 < dewi_base, f"expected turun: base={dewi_base} 50={dewi_50}"

        # Turunkan ke 0 → Dewi NAIK, Desainer Demo grade null
        _set_weight(client, 0)
        d0 = _kpi(client)
        assert float(d0["weights"]["design"]) == 0.0
        items0 = {r["designer"]: r for r in d0["items"]}
        dewi_0 = items0["Dewi Lestari"]["grade_score"]
        assert dewi_0 > dewi_base, f"expected naik: base={dewi_base} 0={dewi_0}"
        assert items0["Desainer Demo"]["grade_score"] is None

        # Kembalikan ke 20
        _set_weight(client, 20)
        drestored = _kpi(client)
        assert float(drestored["weights"]["design"]) == 20.0


# ─── 4. Ekspor & report ──────────────────────────────────────────────────────
class TestExports:
    def test_csv(self, client):
        r = client.get(f"{BASE_URL}/api/rnd/reports/designer-kpi/export",
                       params={"entity_id": ENTITY, "period": "all", "format": "csv"}, timeout=30)
        assert r.status_code == 200, r.text[:200]
        assert len(r.content) > 0

    def test_pdf(self, client):
        r = client.get(f"{BASE_URL}/api/rnd/reports/designer-kpi/export",
                       params={"entity_id": ENTITY, "period": "all", "format": "pdf"}, timeout=30)
        assert r.status_code == 200, r.text[:200]
        assert "pdf" in r.headers.get("content-type", "").lower()

    def test_report_designer_pdf(self, client):
        r = client.get(f"{BASE_URL}/api/rnd/reports/designer-kpi/report",
                       params={"entity_id": ENTITY, "period": "all", "designer": "Dewi Lestari"}, timeout=30)
        assert r.status_code == 200, r.text[:200]

    def test_my_kpi(self, client):
        r = client.get(f"{BASE_URL}/api/rnd/reports/my-kpi",
                       params={"entity_id": ENTITY}, timeout=30)
        assert r.status_code == 200, r.text[:200]
        data = r.json()
        assert "design" in (data.get("weights") or {})
