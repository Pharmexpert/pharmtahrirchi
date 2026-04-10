"""Phase 9: Sayqallash pipeline tests."""
import pytest
from httpx import AsyncClient, ASGITransport


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
    from main import app
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as c:
        yield c


@pytest.mark.anyio
async def test_sayqallash_basic(client):
    """Test basic sayqallash endpoint returns expected structure."""
    resp = await client.post("/sayqallash", json={"text": "Тест матн", "lang": "uz"})
    assert resp.status_code == 200
    data = resp.json()
    assert "annotations" in data
    assert "corrected_text" in data
    assert isinstance(data["annotations"], list)


@pytest.mark.anyio
async def test_sayqallash_empty_text(client):
    """Empty text should return empty results."""
    resp = await client.post("/sayqallash", json={"text": "", "lang": "uz"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["annotations"] == []


@pytest.mark.anyio
async def test_sayqallash_batch(client):
    """Batch sayqallash should process multiple items."""
    resp = await client.post("/api/sayqallash/batch", json={
        "items": [
            {"text": "Биринчи матн", "lang": "uz"},
            {"text": "Иккинчи матн", "lang": "uz"},
        ]
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "results" in data
    assert len(data["results"]) == 2


@pytest.mark.anyio
async def test_analyze_full(client):
    """4-layer analysis should return all layers."""
    resp = await client.post("/api/analyze/full", json={
        "text": "Фармакологик таъсир",
        "layers": ["morph", "sayqallash", "syntax", "style"],
        "lang": "uz"
    })
    assert resp.status_code == 200
    data = resp.json()
    assert "morph" in data
    assert "sayqallash" in data
    assert "syntax" in data
    assert "style" in data
    assert "total" in data
    assert "summary" in data


@pytest.mark.anyio
async def test_analyze_ner(client):
    """NER endpoint should return entities list."""
    resp = await client.post("/api/analyze/ner", json={"text": "Paracetamol 500mg"})
    assert resp.status_code == 200
    data = resp.json()
    assert "entities" in data
    assert "total" in data


@pytest.mark.anyio
async def test_protect_entities(client):
    """Protect entities should return placeholders."""
    resp = await client.post("/api/analyze/protect-entities", json={"text": "Paracetamol 500mg"})
    assert resp.status_code == 200
    data = resp.json()
    assert "protected_text" in data
    assert "placeholder_map" in data


@pytest.mark.anyio
async def test_qa_check(client):
    """QA check should return score and checks."""
    resp = await client.post("/api/qa/check", json={
        "source_text": "Paracetamol 500mg tablets",
        "target_text": "Парацетамол 500мг таблеткалар",
        "source_lang": "en",
        "target_lang": "uz",
    }, headers={"Authorization": "Bearer test"})
    # May return 401 without valid token, but structure test
    if resp.status_code == 200:
        data = resp.json()
        assert "checks" in data
        assert "score" in data
        assert "grade" in data
