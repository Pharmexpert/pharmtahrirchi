"""Tests for core API endpoints."""
import pytest


class TestSecurityHeaders:
    def test_cors_headers(self, client):
        """Responses should include security headers."""
        res = client.get("/docs")
        assert res.headers.get("x-content-type-options") == "nosniff"
        assert res.headers.get("x-frame-options") == "DENY"
        assert res.headers.get("x-xss-protection") == "1; mode=block"
        assert res.headers.get("referrer-policy") == "strict-origin-when-cross-origin"


class TestUploadValidation:
    def test_upload_wrong_file_type(self, client, auth_headers):
        """Uploading non-docx/pdf should be rejected."""
        res = client.post(
            "/api/upload",
            files={"file": ("test.txt", b"hello world", "text/plain")},
            headers={"Authorization": auth_headers["Authorization"]},
        )
        assert res.status_code == 400
        assert "DOCX" in res.json()["detail"] or "PDF" in res.json()["detail"]

    def test_upload_no_auth(self, client):
        """Upload without auth should fail."""
        res = client.post(
            "/api/upload",
            files={"file": ("test.docx", b"data", "application/octet-stream")},
        )
        assert res.status_code in (401, 403)


class TestProjectEndpoints:
    def test_list_projects(self, client, auth_headers):
        """GET /api/projects should return a list."""
        res = client.get("/api/projects", headers=auth_headers)
        assert res.status_code == 200
        assert "projects" in res.json()

    def test_specialists_list(self, client):
        """GET /api/specialists should return a list."""
        res = client.get("/api/specialists")
        assert res.status_code == 200
        assert "specialists" in res.json()

    def test_history_nonexistent(self, client):
        """GET /api/history/nonexistent should return empty."""
        res = client.get("/api/history/nonexistent_project_xyz")
        assert res.status_code == 200
        assert res.json()["alignments"] == []


class TestSayqallashEndpoints:
    def test_sayqallash_empty_text(self, client):
        """Empty text should return empty result."""
        res = client.post("/sayqallash", json={"text": "", "lang": "uz"})
        assert res.status_code == 200
        data = res.json()
        assert data["annotations"] == []
        assert data["corrected_text"] == ""

    def test_auto_notes_empty(self, client):
        """Auto notes with same v1/proposed should return empty."""
        res = client.post("/api/auto-notes", json={"v1": "test", "proposed": "test", "lang": "uz"})
        assert res.status_code == 200

    def test_learn_batch_empty(self, client):
        """Empty learn batch should return count 0."""
        res = client.post("/api/sayqallash/learn-batch", json={"corrections": [], "lang": "uz"})
        assert res.status_code == 200
        assert res.json()["count"] == 0


class TestDictionaryEndpoints:
    def test_autocomplete_short_prefix(self, client):
        """Prefix < 2 chars should return empty."""
        res = client.post("/api/dictionary/autocomplete", json={"prefix": "a"})
        assert res.status_code == 200
        assert res.json()["words"] == []

    def test_bert_synonyms_empty_word(self, client):
        """Empty word should return no synonyms."""
        res = client.post("/api/bert/synonyms", json={"word": "", "lang": "uz"})
        assert res.status_code == 200
        assert res.json()["synonyms"] == []


class TestTransliteration:
    def test_transliterate_empty(self, client):
        """Empty text should return empty."""
        res = client.post("/api/transliterate", json={"text": "", "target": "latin"})
        assert res.status_code == 200
        assert res.json()["text"] == ""

    def test_transliterate_batch_empty(self, client):
        """Empty batch should return empty."""
        res = client.post("/api/transliterate-batch", json={"texts": [], "target": "latin"})
        assert res.status_code == 200
        assert res.json()["texts"] == []
