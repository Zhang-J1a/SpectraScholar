from fastapi.testclient import TestClient

from spectrascholar.main import app


def test_health_and_demo_research():
    with TestClient(app) as client:
        assert client.get('/api/v1/health').status_code == 200
        r=client.post('/api/v1/research',json={"topic":"比较高光谱分类中的动态图方法", "domain":"hyperspectral"})
        assert r.status_code == 202
        job=client.get('/api/v1/research/'+r.json()['job_id'])
        assert job.status_code == 200
        assert job.json()['status'] in ('completed','running','queued')
        if job.json()['status']=='completed':
            assert '演示模式' in job.json()['report']


def test_invalid_upload():
    with TestClient(app) as client:
        r=client.post('/api/v1/documents',files={'file':('evil.pdf',b'not pdf','application/pdf')})
        assert r.status_code == 415
