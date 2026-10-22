"""Fake backend integration for map, crawl and partial batch failures."""
import asyncio
import uuid
from app.storage import Store
from app.engine import EngineError
import app.main as server


class FakeEngine:
    def __init__(self):
        self.polls = 0

    async def map(self, url, limit):
        return {'success':True,'links':[url+'/a',url+'/b']}

    async def crawl(self, url, limit, depth):
        return {'success':True,'id':str(uuid.uuid4())}

    async def crawl_status(self, id):
        self.polls += 1
        return {'status':'completed','data':[{'metadata':{'sourceURL':'https://example.org/a','title':'a'},'markdown':'hi'}]}

    async def scrape(self, url):
        if url.endswith('/fail'):
            raise EngineError('Blocked on site')
        return {'success': True, 'data':{'markdown':'hello','metadata':{'sourceURL':url,'title':'t'}}}


def test_fake_map_crawl_batch(tmp_path, monkeypatch):
    fake = FakeEngine()
    monkeypatch.setattr(server, 'store', Store(tmp_path))
    monkeypatch.setattr(server, 'engine', fake)
    monkeypatch.setattr(server, 'validate_target', lambda url, resolve_dns=True:url)
    async def run():
        for kind, args, count in [
            ('map', {'url':'https://example.org','limit':10}, 2),
            ('crawl', {'url':'https://example.org','limit':4,'depth':1}, 1),
            ('batch', {'urls':['https://example.org/a','https://example.org/fail']}, 1)]:
            jid = str(uuid.uuid4())
            server.store.add_job(jid,kind,args,2)
            await server.worker(jid,kind,args)
            job=server.store.job(jid)
            assert job['status'] == 'completed', job
            assert (len(job['links']) if kind=='map' else len(server.store.pages(jid))) == count
            if kind=='batch':
                assert 'Blocked on site' in job['error']
    asyncio.run(run())
    assert fake.polls == 1
