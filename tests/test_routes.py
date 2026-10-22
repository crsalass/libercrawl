import asyncio
import json
import time
from fastapi.testclient import TestClient
import httpx
import app.main as server
from app.storage import Store
from app.engine import LocalEngineClient


def test_api_local_scrape_and_download(tmp_path, monkeypatch):
    monkeypatch.setattr(server, "store", Store(tmp_path))
    def handler(req):
        if req.url.path == '/v2/scrape' and req.content == b'{}':
            return httpx.Response(422, json={'success':False,'error':'Missing URL'})
        if req.url.path == '/v2/scrape':
            return httpx.Response(200, json={'success':True, 'data': {
                'metadata': {'sourceURL':'https://example.org/item', 'title':'Hello'},
                'markdown':'# Hello', 'html':'<script type="application/ld+json">{"@type":"Product","name":"Hello","offers":{"price":12,"priceCurrency":"EUR"}}</script>',
                'links': []}})
        return httpx.Response(400, json={'success':False,'error':'bad endpoint'})
    monkeypatch.setattr(server, 'engine', LocalEngineClient('http://127.0.0.1:3002',transport=httpx.MockTransport(handler)))
    import app.security as security
    import socket
    monkeypatch.setattr(security.socket, 'getaddrinfo', lambda host, port, **kwargs:
                        [(socket.AF_INET, socket.SOCK_STREAM, 6, '', ('93.184.216.34', port))])
    with TestClient(server.app) as client:
        assert client.get('/api/status').json()['engine'] == 'online'
        response=client.post('/api/scrape',json={'url':'https://example.org/item'})
        assert response.status_code == 202
        jid=response.json()['id']
        for _ in range(60):
            d=client.get('/api/jobs/'+jid).json()
            if d['status'] not in ('queued','running'):break
            time.sleep(.02)
        assert d['status'] == 'completed', d
        assert d['pages'][0]['product']['price'] == '12'
        csv_result=client.get(f'/api/jobs/{jid}/export?format=csv')
        assert csv_result.status_code == 200 and 'Hello' in csv_result.text
        assert client.get(f'/api/jobs/{jid}/export?format=estilo').status_code == 422
        monkeypatch.setenv('LIBERCRAWL_ENABLE_ESTILO', '1')
        assert client.get(f'/api/jobs/{jid}/export?format=estilo').status_code == 422
        assert 'estilo' not in client.get('/api/status').json()['features']
        assert client.get('/api/jobs').json()['jobs'][0]['page_count'] == 1
        assert client.post('/api/scrape',json={'url':'http://127.0.0.1/'}).status_code == 422
        assert client.get('/api/jobs/00000000-0000-0000-0000-000000000000').status_code == 404
