from __future__ import annotations

from fastapi.testclient import TestClient
from app.main import app

# Monkeypatch transcript and embeddings to avoid network/model load
from app.services import transcript as transcript_service
from app.services import embeddings as embeddings_service


def fake_load_youtube_transcript(url: str):
    # 3 segments of 20s
    return [
        {"start_time": 0.0, "end_time": 20.0, "text": "machine learning is the study of algorithms"},
        {"start_time": 15.0, "end_time": 40.0, "text": "supervised learning uses labeled data"},
        {"start_time": 40.0, "end_time": 60.0, "text": "unsupervised learning finds structure in data"},
    ]


def fake_embed_texts(texts):
    # tiny deterministic vectors
    import numpy as np
    vecs = []
    for t in texts:
        v = np.zeros(8)
        for ch in t:
            v[ord(ch) % 8] += 1.0
        n = np.linalg.norm(v) or 1.0
        vecs.append((v / n).tolist())
    return vecs


def test_health():
    client = TestClient(app)
    r = client.get('/health')
    assert r.status_code == 200
    assert r.json().get('status') == 'ok'


def test_ingest_and_search(monkeypatch):
    monkeypatch.setattr(transcript_service, 'load_youtube_transcript', fake_load_youtube_transcript)
    monkeypatch.setattr(embeddings_service, 'embed_texts', fake_embed_texts)

    client = TestClient(app)

    # ingest
    r = client.post('/api/ingest_video', json={"video_url": "https://www.youtube.com/watch?v=TEST123"})
    assert r.status_code == 200
    vid = r.json()['video_id']

    # search
    r2 = client.post('/api/search_timestamps', json={"query": "what is machine learning", "k": 3, "video_id": vid})
    assert r2.status_code == 200
    data = r2.json()
    assert 'results' in data and len(data['results']) >= 1
    assert isinstance(data.get('answer', ''), str)



