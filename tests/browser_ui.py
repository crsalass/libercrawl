"""Offline public UI regression checks and authentic screenshot capture.

Run with Playwright installed and a local Edge/Chromium browser. Everything runs
in a disposable copy under .local-backups/ui-review; no real engine is contacted.
See docs/UI_TESTING.md for commands, coverage and fixture disclosure.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request
from urllib.parse import urlsplit

from playwright.sync_api import expect, sync_playwright


ROOT = Path(__file__).resolve().parents[1]


def stress_review(page, context, work, audit, passed):
    """Bounded adversarial fixtures, supplied only through intercepted API responses."""
    long_url = 'https://example.org/' + 'a' * (2048 - len('https://example.org/'))
    rows = [{'id': f'44444444-4444-4444-8444-{i:012d}', 'kind': 'scrape',
             'status': 'failed', 'args': {'url': long_url}, 'completed': 0,
             'requested': 1, 'page_count': 1, 'created_at': '2026-10-23T12:00:00Z'}
            for i in range(75)]
    detail = {**rows[-1], 'error': 'E' * 700, 'pages': [
        {'id': 1, 'title': '資料 — مرحبا 👩🏽‍💻 <script>literal</script> ' + 'T' * 350,
         'url': long_url, 'markdown': 'M' * 6000, 'product': {}}]}
    detail['pages'][0]['title'] = detail['pages'][0]['title'][:400]
    page.route('**/api/jobs', lambda route: route.fulfill(json={'jobs': rows}))
    page.route('**/api/jobs/44444444-*', lambda route: route.fulfill(json=detail))
    page.reload(wait_until='domcontentloaded')
    expect(page.locator('#jobsBody .view-btn')).to_have_count(75)
    last = page.locator('#jobsBody .view-btn').last
    last.click()
    expect(page.locator('#detailsPanel')).to_be_focused()
    expect(page.locator('#detailSummary')).to_contain_text('E' * 700)
    for width in (1440, 1024, 768, 390, 320):
        page.set_viewport_size({'width': width, 'height': 1080})
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Long content overflow at {width}px'
        assert page.locator('#detailsPanel').evaluate('e=>e.scrollWidth <= e.clientWidth'), f'Inspector overflow at {width}px'
    page.locator('#pageList summary').click()
    assert page.locator('#pageList .preview').inner_text() == 'M' * 6000
    page.locator('#pageList .preview').focus()
    page.keyboard.press('End')
    assert page.locator('#pageList .preview').evaluate('e=>e.scrollTop > 0')
    assert page.locator('#pageList script').count() == 0
    audit('worst-case-inspector-320')
    page.screenshot(path=str(work / 'stress-mobile.png'))
    page.keyboard.press('Escape')
    expect(last).to_be_focused()
    bounds = last.bounding_box()
    assert bounds and 88 <= bounds['y'] and bounds['y'] + bounds['height'] <= 1080, bounds
    passed('75-row archive: long URLs/errors/titles, Unicode, literal markup and last-row focus return')

    # The upstream map array is stored as received; optional entries must not break Inspect.
    detail.update(kind='map', links=[long_url, {'url': 'https://example.org/資料'}, None, {}, ''], pages=[])
    last.click()
    expect(page.locator('#detailsPanel')).to_be_visible()
    expect(page.locator('#pageList .link-item')).to_have_count(5)
    expect(page.locator('#archiveNotice')).to_be_hidden()
    audit('partial-map-inspector-320')
    links = page.locator('#pageList .links')
    links.focus()
    page.keyboard.press('End')
    old_scroll = links.evaluate('e=>e.scrollTop')
    detail['completed'] = 1
    page.wait_for_timeout(5500)
    expect(links).to_be_focused()
    assert links.evaluate('e=>e.scrollTop') == old_scroll
    page.screenshot(path=str(work / 'partial-map-mobile.png'))
    passed('Partial upstream map entries keep the inspector usable')
    page.locator('#closeDetailsBtn').click()
    page.unroute('**/api/jobs/44444444-*')
    page.unroute('**/api/jobs')

    # Browser zoom changes the effective CSS viewport: 1440px at 200% is 720 CSS px.
    page.reload(wait_until='domcontentloaded')
    page.set_viewport_size({'width': 720, 'height': 540})
    for tab in ('scrape', 'batch', 'crawl', 'map', 'library'):
        page.locator(f'[data-tab="{tab}"]').click()
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), tab
    passed('200% zoom-equivalent reflow across all five workflows')

    page.set_viewport_size({'width': 1440, 'height': 1080})
    page.locator('[data-tab="scrape"]').click()
    cdp = context.new_cdp_session(page)
    cdp.send('Emulation.setEmulatedMedia', {'features': [
        {'name': 'prefers-reduced-transparency', 'value': 'reduce'}]})
    assert page.evaluate('matchMedia("(prefers-reduced-transparency: reduce)").matches')
    assert page.locator('.topbar').evaluate('e=>getComputedStyle(e).backdropFilter') == 'none'
    assert page.locator('.sidebar').evaluate('e=>getComputedStyle(e).backgroundColor.startsWith("rgb(")')
    assert page.locator('.main').evaluate('e=>getComputedStyle(e).backgroundImage') == 'none'
    page.screenshot(path=str(work / 'reduced-transparency.png'))
    cdp.send('Emulation.setEmulatedMedia', {'features': [
        {'name': 'prefers-contrast', 'value': 'more'}]})
    assert page.evaluate('matchMedia("(prefers-contrast: more)").matches')
    assert page.locator('.topbar').evaluate('e=>getComputedStyle(e).backdropFilter') == 'none'
    assert page.locator('.main').evaluate('e=>getComputedStyle(e).backgroundImage') == 'none'
    assert page.locator('.panel').first.evaluate('e=>getComputedStyle(e).borderTopColor') == 'rgb(151, 159, 173)'
    audit('increased-contrast')
    cdp.send('Emulation.setEmulatedMedia', {'features': []})
    cdp.detach()
    page.emulate_media(reduced_motion='reduce', forced_colors='active')
    expect(page.locator('#urlInput')).to_be_visible()
    assert page.locator('#urlInput').evaluate('e=>getComputedStyle(e).borderTopStyle') == 'solid'
    page.emulate_media(reduced_motion='reduce', forced_colors='none')
    passed('Reduced transparency, increased contrast and forced colors')

    touch = context.browser.new_context(viewport={'width': 390, 'height': 844},
                                        is_mobile=True, has_touch=True)
    try:
        preview_url = urlsplit(page.url)
        preview_origin = f'{preview_url.scheme}://{preview_url.netloc}/'
        touch_external, touch_errors = [], []
        def touch_restrict(route):
            if route.request.url.startswith(preview_origin):
                route.continue_()
            else:
                touch_external.append(route.request.url)
                route.abort()
        touch.route('**/*', touch_restrict)
        mobile = touch.new_page()
        mobile.on('pageerror', lambda error: touch_errors.append(str(error)))
        mobile.goto(preview_origin, wait_until='domcontentloaded')
        assert mobile.evaluate('matchMedia("(hover: none) and (pointer: coarse)").matches')
        button = mobile.locator('#submitBtn')
        before = button.evaluate('e=>getComputedStyle(e).backgroundColor')
        button.hover()  # Simulate a retained hover: coarse pointers must keep the base style.
        assert button.evaluate('e=>getComputedStyle(e).backgroundColor') == before
        mobile.locator('[data-tab="batch"]').tap()
        expect(mobile.locator('#batchInput')).to_be_visible()
        assert mobile.locator('#batchInput').evaluate('e=>getComputedStyle(e).fontSize') == '16px'
        assert mobile.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert not touch_external, touch_external
        assert not touch_errors, touch_errors
    finally:
        touch.close()
    passed('Touch-capability emulation: hover suppression and reachable batch workflow')


def run(channel: str, axe: Path | None, capture: bool, stress_only: bool = False) -> None:
    review_root = ROOT / '.local-backups' / 'ui-review'
    review_root.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix='public-', dir=review_root)).resolve()
    assert work.is_relative_to(review_root.resolve())
    shutil.copytree(ROOT / 'app', work / 'app',
                    ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
    assert not (work / '.env').exists()
    assets = ROOT / 'docs' / 'assets'
    results: dict = {'checks': [], 'viewports': [], 'axe': [], 'page_errors': [],
                     'external_requests': [], 'fixture_requests': []}

    # A bound, non-listening socket prevents contact with an existing engine.
    engine_socket = socket.socket()
    engine_socket.bind(('127.0.0.1', 0))
    with socket.socket() as port_probe:
        port_probe.bind(('127.0.0.1', 0))
        port = port_probe.getsockname()[1]
    origin = f'http://127.0.0.1:{port}'
    env = os.environ.copy()
    env.update(APP_DATA_DIR=str(work / 'preview-data'),
               LOCAL_ENGINE_URL=f'http://127.0.0.1:{engine_socket.getsockname()[1]}',
               PYTHONDONTWRITEBYTECODE='1')
    log = (work / 'server.log').open('w', encoding='utf-8')
    creationflags = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
    process = subprocess.Popen(
        [sys.executable, '-m', 'uvicorn', 'app.main:app', '--host', '127.0.0.1',
         '--port', str(port)], cwd=work, env=env, stdout=log, stderr=log,
        creationflags=creationflags)

    def passed(name: str) -> None:
        results['checks'].append(name)

    try:
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(60):
            try:
                with opener.open(origin + '/api/jobs', timeout=2) as response:
                    assert json.load(response)['jobs'] == []
                break
            except OSError:
                if process.poll() is not None:
                    raise RuntimeError(f'Preview failed; inspect {work / "server.log"}')
                time.sleep(.1)
        else:
            raise RuntimeError('Preview did not start')

        with sync_playwright() as p:
            context = p.chromium.launch_persistent_context(
                user_data_dir=str(work / 'browser-profile'), channel=channel,
                headless=True, viewport={'width': 1440, 'height': 1080},
                device_scale_factor=1, locale='en-GB', timezone_id='Europe/Madrid',
                reduced_motion='reduce', downloads_path=str(work / 'downloads'))
            try:
                results['browser'] = context.browser.version

                def restrict(route):
                    if not route.request.url.startswith(origin + '/'):
                        results['external_requests'].append(route.request.url)
                        route.abort()
                    else:
                        route.continue_()

                context.route('**/*', restrict)
                page = context.pages[0]
                page.on('pageerror', lambda error: results['page_errors'].append(str(error)))
                page.goto(origin, wait_until='domcontentloaded')
                expect(page.locator('#statEngine')).to_have_text('Offline', timeout=20000)
                expect(page.locator('#statJobs')).to_have_text('0')
                expect(page.locator('#jobsBody')).to_contain_text('Your next discovery')
                passed('Real isolated dashboard: offline engine and empty archive')
                expect(page.locator('#pageTitle')).to_contain_text('Extract the Web.')
                expect(page.locator('#pageTitle')).to_contain_text('Free the data.')

                def audit(name: str) -> None:
                    if axe is None:
                        return
                    page.evaluate(axe.read_text(encoding='utf-8'))
                    report = page.evaluate('''async () => {
                        const r = await axe.run(document, {
                            runOnly: {type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}
                        });
                        return {violations:r.violations.map(v => ({id:v.id,impact:v.impact,
                            description:v.description,nodes:v.nodes.map(n=>({target:n.target,
                            summary:n.failureSummary}))})), incomplete:r.incomplete.map(v=>({id:v.id,
                            nodes:v.nodes.map(n=>({target:n.target,summary:n.failureSummary}))}))};
                    }''')
                    results['axe'].append({'state': name, **report})
                    assert not report['violations'], (name, report['violations'])

                if stress_only:
                    stress_review(page, context, work, audit, passed)
                    assert not results['page_errors'], results['page_errors']
                    assert not results['external_requests'], results['external_requests']
                    return

                # Published captures contain only the genuine empty/offline state.
                for width in (1440, 1024, 768, 390, 320):
                    page.set_viewport_size({'width': width, 'height': 1080})
                    metrics = page.evaluate('''() => ({width:innerWidth,
                        scrollWidth:document.documentElement.scrollWidth,
                        invalidStyles:[...document.styleSheets].filter(s=>s.href&&s.cssRules.length===0).length})''')
                    assert metrics['scrollWidth'] == width, metrics
                    assert metrics['invalidStyles'] == 0
                    results['viewports'].append(metrics)
                    for tab in ('scrape', 'batch', 'crawl', 'map', 'library'):
                        page.locator(f'[data-tab="{tab}"]').click()
                        expect(page.locator(f'[data-tab="{tab}"]')).to_have_attribute('aria-current', 'page')
                        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    page.locator('[data-tab="scrape"]').click()
                    page.evaluate('scrollTo(0,0)')
                    page.screenshot(path=str(work / f'after-{width}.png'), full_page=True)
                    if capture and width in (1440, 390):
                        name = 'public-dashboard.png' if width == 1440 else 'ui-after-mobile.png'
                        shutil.copyfile(work / f'after-{width}.png', assets / name)
                    if width in (1440, 390):
                        audit(f'empty-{width}')
                passed('Five workflows at 1440, 1024, 768, 390 and 320 px without overflow')

                page.set_viewport_size({'width': 1440, 'height': 1080})
                page.goto(origin, wait_until='domcontentloaded')
                page.keyboard.press('Tab')
                expect(page.locator('.skip-link')).to_be_focused()
                page.keyboard.press('Enter')
                expect(page.locator('#mainContent')).to_be_focused()
                page.locator('[data-tab="batch"]').focus()
                page.keyboard.press('Enter')
                expect(page.locator('#batchInput')).to_be_enabled()
                expect(page.locator('#urlInput')).to_be_disabled()
                expect(page.locator('#limitInput')).to_be_disabled()
                page.locator('#batchInput').focus()
                page.keyboard.press('Tab')
                expect(page.locator('#submitBtn')).to_be_focused()
                passed('Keyboard skip link, workflow activation and form tab order')
                motion = page.evaluate('''() => ({scroll:getComputedStyle(document.documentElement).scrollBehavior,
                    transition:getComputedStyle(document.getElementById('submitBtn')).transitionDuration})''')
                assert motion == {'scroll': 'auto', 'transition': '0s'}, motion
                page.locator('[data-tab="scrape"]').click()
                normal_background = page.locator('#submitBtn').evaluate('(e)=>getComputedStyle(e).backgroundColor')
                page.locator('#submitBtn').hover()
                hover_background = page.locator('#submitBtn').evaluate('(e)=>getComputedStyle(e).backgroundColor')
                assert normal_background != hover_background
                page.locator('#urlInput').focus()
                assert page.locator('#urlInput').evaluate('(e)=>getComputedStyle(e).outlineStyle') == 'solid'
                passed('Reduced motion, button hover feedback and visible input focus')

                # Held requests test busy/disabled and validation error states.
                for kind in ('scrape', 'batch', 'crawl', 'map'):
                    page.locator(f'[data-tab="{kind}"]').click()
                    if kind == 'batch':
                        page.locator('#batchInput').fill('https://example.org/one\nhttps://example.org/two')
                    else:
                        page.locator('#urlInput').fill('https://example.org/ui-fixture')
                    held = []
                    pattern = f'**/api/{kind}'
                    page.route(pattern, lambda route: held.append(route))
                    page.locator('#submitBtn').click()
                    expect(page.locator('#submitBtn')).to_be_disabled()
                    expect(page.locator('#submitBtn')).to_have_attribute('aria-busy', 'true')
                    for _ in range(20):
                        if held:
                            break
                        page.wait_for_timeout(20)
                    assert held, kind
                    payload = held[0].request.post_data_json
                    assert ('urls' in payload) == (kind == 'batch'), payload
                    if kind == 'crawl':
                        assert payload['limit'] == 10 and payload['depth'] == 2
                    if kind == 'map':
                        assert payload['limit'] == 30 and 'depth' not in payload
                    results['fixture_requests'].append({'kind': kind, 'payload': payload})
                    held[0].fulfill(status=422, content_type='application/json',
                                    body='{"detail":"Offline UI validation fixture"}')
                    expect(page.locator('#notice')).to_contain_text('Offline UI validation fixture')
                    expect(page.locator('#submitBtn')).to_be_enabled()
                    page.unroute(pattern)
                    audit(f'{kind}-error')
                passed('All four request payloads, busy controls and visible form errors')

                seed = r'''from app.storage import Store
s=Store('preview-data')
for jid,kind,status,title in [
('33333333-3333-4333-8333-333333333333','crawl','running','Running UI fixture'),
('22222222-2222-4222-8222-222222222222','map','completed','Map UI fixture'),
('11111111-1111-4111-8111-111111111111','scrape','completed','UI test fixture — no live extraction')]:
    s.add_job(jid,kind,{'url':'https://example.org/ui-test-fixture'},1)
    if kind=='scrape':
        s.add_page(jid,{'metadata':{'sourceURL':'https://example.org/ui-test-fixture','title':title},
                       'markdown':'UI TEST FIXTURE. No website was fetched.\nUsed only to verify inspector, focus and downloads.'})
    s.update(jid,status=status,completed=0 if status=='running' else 1)
    with s.connect() as conn:
        conn.execute('UPDATE jobs SET created_at=? WHERE id=?',('2026-10-23T12:00:0'+('3' if kind=='scrape' else '2' if kind=='map' else '1')+'Z',jid))
'''
                subprocess.run([sys.executable, '-c', seed], cwd=work, env=env, check=True)
                page.locator('[data-tab="scrape"]').click()
                page.locator('#urlInput').fill('https://example.org/ui-test-fixture')
                page.route('**/api/scrape', lambda route: route.fulfill(status=202,
                    content_type='application/json',
                    body='{"id":"11111111-1111-4111-8111-111111111111","status":"queued","kind":"scrape"}'))
                page.locator('#submitBtn').click()
                expect(page.locator('#notice')).to_contain_text('Operation created')
                expect(page.locator('#detailsPanel')).to_be_visible()
                expect(page.locator('#submitBtn')).to_be_enabled()
                page.unroute('**/api/scrape')
                page.locator('#closeDetailsBtn').click()
                passed('Mocked accepted submission shows success and opens its real fixture record')
                page.locator('[data-tab="library"]').click()
                page.locator('#refreshBtn').click()
                first = page.locator('#jobsBody button[data-inspect-id]').first
                expect(first).to_have_attribute('data-inspect-id', '11111111-1111-4111-8111-111111111111')
                first.focus()
                page.keyboard.press('Enter')
                expect(page.locator('#detailsPanel')).to_be_visible()
                expect(page.locator('#detailsPanel')).to_be_focused()
                box = page.locator('#detailsPanel').bounding_box()
                assert box and 0 <= box['y'] < 1080, box
                page.locator('#pageList summary').click()
                expect(page.locator('#pageList details')).to_have_attribute('open', '')
                audit('scrape-inspector')
                if capture:
                    page.locator('#historyPanel').evaluate("e=>e.scrollIntoView({block:'start'})")
                    page.screenshot(path=str(assets / 'ui-after-inspect.png'))

                page.locator('#pageList summary').focus()
                page.wait_for_timeout(5500)
                expect(page.locator('#pageList summary')).to_be_focused()
                expect(page.locator('#pageList details')).to_have_attribute('open', '')
                page.keyboard.press('Escape')
                expect(page.locator('#detailsPanel')).to_be_hidden()
                expect(first).to_be_focused()
                page.wait_for_timeout(5500)
                expect(first).to_be_focused()
                passed('First Inspect focus/scroll, disclosure survives polling, Escape returns focus')
                passed('Inspect button focus survives archive polling')
                changed_jobs = page.request.get(origin + '/api/jobs').json()
                changed_jobs['jobs'][0]['completed'] = 2
                page.route('**/api/jobs', lambda route: route.fulfill(status=200,
                    content_type='application/json', body=json.dumps(changed_jobs)))
                page.wait_for_timeout(5500)
                expect(first).to_be_focused()
                page.unroute('**/api/jobs')
                passed('Inspect button focus survives changed archive rows')

                first.click()
                for width in (1024, 768, 390):
                    page.set_viewport_size({'width': width, 'height': 1080})
                    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
                    expect(page.locator('#detailsPanel')).to_be_visible()
                    assert page.locator('#historyPanel').evaluate('''panel => {
                        const bounds = panel.querySelector('.table-wrap').getBoundingClientRect();
                        return [...panel.querySelectorAll('.view-btn')].every(button => {
                            const b = button.getBoundingClientRect();
                            return b.left >= bounds.left && b.right <= bounds.right;
                        });
                    }'''), f'Archive action clipping at {width}px'
                    page.locator('#detailsPanel').evaluate("e=>e.scrollIntoView({block:'start'})")
                    page.screenshot(path=str(work / f'populated-{width}.png'))
                    audit(f'populated-inspector-{width}')
                page.set_viewport_size({'width': 1440, 'height': 1080})
                passed('Populated archive and inspector at tablet and mobile sizes')
                for fmt in ('json', 'jsonl', 'csv', 'markdown'):
                    with page.expect_download() as download:
                        page.locator(f'[data-format="{fmt}"]').click()
                    assert download.value.failure() is None
                    content = Path(download.value.path()).read_text(encoding='utf-8')
                    assert 'UI test fixture' in content or 'UI TEST FIXTURE' in content
                passed('Four real public export routes download fixture data')
                page.locator('#closeDetailsBtn').click()
                map_button = page.locator('[data-inspect-id="22222222-2222-4222-8222-222222222222"]')
                map_button.click()
                expect(page.locator('[data-format="json"]')).to_be_enabled()
                for fmt in ('jsonl', 'csv', 'markdown'):
                    expect(page.locator(f'[data-format="{fmt}"]')).to_be_disabled()
                audit('map-inspector')
                page.locator('#closeDetailsBtn').click()
                page.locator('[data-inspect-id="33333333-3333-4333-8333-333333333333"]').click()
                expect(page.locator('#cancelBtn')).to_be_visible()
                page.locator('#cancelBtn').click()
                expect(page.locator('#detailTitle')).to_contain_text('cancelled')
                passed('Map export restrictions and real cancellation of a disposable fixture')
                page.locator('#closeDetailsBtn').click()

                pattern = '**/api/jobs/11111111-1111-4111-8111-111111111111'
                page.route(pattern, lambda route: route.fulfill(status=500,
                    content_type='application/json', body='{"detail":"Inspector failure fixture"}'))
                first.click()
                expect(page.locator('#archiveNotice')).to_be_visible()
                expect(page.locator('#archiveNotice')).to_contain_text('Inspector failure fixture')
                page.unroute(pattern)
                passed('Inspector API failure appears in archiveNotice')

                first.click()
                expect(page.locator('#detailsPanel')).to_be_visible()
                page.locator('#pageList summary').click()
                # Poll a changed record: expanded content and focused controls survive.
                changed = page.request.get(origin + '/api/jobs/11111111-1111-4111-8111-111111111111').json()
                changed['completed'] = 2
                page.route(pattern, lambda route: route.fulfill(status=200,
                    content_type='application/json', body=json.dumps(changed)))
                page.locator('#pageList summary').focus()
                page.wait_for_timeout(5500)
                expect(page.locator('#pageList summary')).to_be_focused()
                expect(page.locator('#pageList details')).to_have_attribute('open', '')
                page.locator('#pageList .preview').focus()
                changed['completed'] = 3
                page.wait_for_timeout(5500)
                expect(page.locator('#pageList .preview')).to_be_focused()
                page.unroute(pattern)
                passed('Inspector summary/preview focus and expanded content survive changed polling data')

                page.route(pattern, lambda route: route.fulfill(status=500,
                    content_type='application/json', body='{"detail":"Polling failure fixture"}'))
                page.wait_for_timeout(5500)
                expect(page.locator('#archiveNotice')).to_contain_text('Polling failure fixture')
                page.unroute(pattern)
                page.wait_for_timeout(5500)
                expect(page.locator('#archiveNotice')).to_be_hidden()
                passed('Inspector polling failure clears after recovery')
                page.locator('#closeDetailsBtn').click()

                page.route('**/api/jobs', lambda route: route.fulfill(status=500,
                    content_type='application/json', body='{"detail":"Archive failure fixture"}'))
                page.locator('#refreshBtn').click()
                expect(page.locator('#archiveNotice')).to_contain_text('Archive failure fixture')
                page.unroute('**/api/jobs')
                page.locator('#refreshBtn').click()
                expect(page.locator('#archiveNotice')).to_be_hidden()
                passed('Archive refresh failure is visible and clears after recovery')

                page.route('**/api/jobs', lambda route: route.fulfill(status=500,
                    content_type='application/json', body='{"detail":"Initial archive failure fixture"}'))
                page.reload(wait_until='domcontentloaded')
                expect(page.locator('#jobsBody')).to_contain_text('Archive unavailable')
                expect(page.locator('#archiveNotice')).to_contain_text('Initial archive failure fixture')
                page.unroute('**/api/jobs')
                page.locator('#refreshBtn').click()
                expect(page.locator('#archiveNotice')).to_be_hidden()
                expect(page.locator('#jobsBody button[data-inspect-id]')).to_have_count(3)
                passed('Initial archive failure and manual recovery')

                page.route('**/api/status', lambda route: route.fulfill(status=200,
                    content_type='application/json', body='{"engine":"online"}'))
                page.reload(wait_until='domcontentloaded')
                expect(page.locator('#statEngine')).to_have_text('Online')
                expect(page.locator('#engineBadge')).to_contain_text('Engine online')
                page.unroute('**/api/status')
                passed('Mocked online state; no live engine claim')

                page.route('**/api/status', lambda route: route.fulfill(status=503,
                    content_type='application/json', body='{}'))
                page.reload(wait_until='domcontentloaded')
                expect(page.locator('#statEngine')).to_have_text('Unknown')
                expect(page.locator('#engineBadge')).to_contain_text('Engine unavailable')
                passed('Engine API failure has a readable unavailable state')

                stress_review(page, context, work, audit, passed)
                assert not results['page_errors'], results['page_errors']
                assert not results['external_requests'], results['external_requests']
                passed('No uncaught page errors or external browser requests')
            finally:
                context.close()
    finally:
        process.terminate()
        process.wait(timeout=15)
        engine_socket.close()
        log.close()
        (work / 'results.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8')
        print(json.dumps({'results': str(work / 'results.json'), 'checks': results['checks'],
                          'viewports': results['viewports'],
                          'axe_summary': [{'state': r['state'], 'violations': len(r['violations']),
                                           'manual_review': [i['id'] for i in r['incomplete']]}
                                          for r in results['axe']],
                          'page_errors': results['page_errors'],
                          'external_requests': results['external_requests']}, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--channel', default='msedge', help='Installed browser channel')
    parser.add_argument('--axe', type=Path, help='Local axe-core axe.min.js (optional)')
    parser.add_argument('--capture', action='store_true', help='Refresh documented after screenshots')
    parser.add_argument('--stress-only', action='store_true', help='Run only the bounded UI resilience checks')
    args = parser.parse_args()
    run(args.channel, args.axe, args.capture, args.stress_only)
