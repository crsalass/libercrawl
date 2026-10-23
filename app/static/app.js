'use strict';

const $ = (id) => document.getElementById(id);
const tabs = {
  scrape: {crumb:'Single scrape', title:'Extract the Web.<br><em>Free the data.</em>', desc:'Turn public webpages into useful data. Extract with your local engine, inspect the results, and make them yours.', form:'Single page scrape', subtitle:'One page. Ready for your next idea.', button:'Run local scrape', help:'Markdown, HTML, links, and product hints from the source.'},
  batch: {crumb:'Batch scrape', title:'Many URLs.<br><em>One workspace.</em>', desc:'Bring a list of public pages. Extract them in sequence, with successful results saved along the way.', form:'Batch scrape', subtitle:'A list of pages. One operation.', button:'Run batch scrape', help:'Each URL runs in sequence. Successful pages are kept if others fail.'},
  crawl: {crumb:'Crawl site', title:'Explore further.<br><em>Stay in control.</em>', desc:'Follow a website from page to page. Set the boundaries, then inspect what your local engine finds.', form:'Website crawl', subtitle:'A little discovery. Clear boundaries.', button:'Start local crawl', help:'Set a page limit and discovery depth. External links are excluded.'},
  map: {crumb:'Map URLs', title:'Discover first.<br><em>Extract later.</em>', desc:'Find the URLs on a website before deciding what to extract. A clearer view of where to go next.', form:'URL discovery', subtitle:'Find the pages worth exploring.', button:'Map website', help:'Returns a URL list without page content. Download as JSON.'},
  library: {crumb:'Archive', title:'Every result.<br><em>Under your control.</em>', desc:'Your recent operations, all in one place. Inspect saved content, review errors, and take your data with you.', form:'Single page scrape', subtitle:'One page. Ready for your next idea.', button:'Run local scrape', help:'Select an operation below to inspect its results.'}
};
let currentTab = 'scrape';
let selectedJob = null;
let jobs = [];
let refreshTimer = null;
let inspectorRequest = 0;
let inspectorSnapshot = '';
let renderedJobs = '';
let archiveLoaded = false;

function make(tag, cls, value) {
  const element = document.createElement(tag);
  if (cls) element.className = cls;
  if (value !== undefined && value !== null) element.textContent = String(value);
  return element;
}
function append(parent, tag, cls, value) {
  const element = make(tag, cls, value);
  parent.appendChild(element);
  return element;
}
function icon(name) {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.classList.add('icon');
  svg.setAttribute('aria-hidden', 'true');
  const use = document.createElementNS('http://www.w3.org/2000/svg', 'use');
  use.setAttribute('href', `#icon-${name}`);
  svg.appendChild(use);
  return svg;
}
function notice(id, value, error = false) {
  const element = $(id);
  element.dataset.source = '';
  element.textContent = value;
  element.classList.remove('hidden');
  element.classList.toggle('error', error);
}
function clearNotice(id) { $(id).classList.add('hidden'); }
function fmtDate(value) {
  if (!value) return '—';
  const date = new Date(value);
  return Number.isNaN(+date) ? String(value) : date.toLocaleString();
}
function switchTab(tab) {
  if (!Object.hasOwn(tabs, tab)) return;
  currentTab = tab;
  document.querySelectorAll('.nav-item').forEach((button) => {
    const active = button.dataset.tab === tab;
    button.classList.toggle('active', active);
    if (active) button.setAttribute('aria-current', 'page');
    else button.removeAttribute('aria-current');
  });
  const info = tabs[tab];
  $('crumb').textContent = info.crumb;
  // HTML is exclusively from the static local tabs object, never user/API data.
  $('pageTitle').innerHTML = info.title;
  $('pageDescription').textContent = info.desc;
  $('formTitle').textContent = info.form;
  $('formSubtitle').textContent = info.subtitle;
  $('operationIcon').setAttribute('href', `#icon-${tab === 'library' ? 'scrape' : tab}`);
  $('formHelp').textContent = info.help;
  $('submitBtn').querySelector('.submit-label').textContent = info.button;
  $('batchBlock').classList.toggle('hidden', tab !== 'batch');
  $('crawlOptions').classList.toggle('hidden', !['crawl','map'].includes(tab));
  $('depthWrap').classList.toggle('hidden', tab !== 'crawl');
  $('urlField').classList.toggle('hidden', tab === 'batch');
  $('urlLabelRow').classList.toggle('hidden', tab === 'batch');
  $('urlInput').disabled = tab === 'batch';
  $('batchInput').disabled = tab !== 'batch';
  $('urlInput').required = tab !== 'batch';
  $('batchInput').required = tab === 'batch';
  $('limitInput').disabled = !['crawl', 'map'].includes(tab);
  $('depthInput').disabled = tab !== 'crawl';
  $('limitLabel').textContent = tab === 'map' ? 'URL limit' : 'Page limit';
  $('limitInput').max = tab === 'map' ? '250' : '50';
  $('limitInput').value = tab === 'map' ? '30' : '10';
  $('operationPanel').classList.toggle('hidden', tab === 'library');
  clearNotice('notice');
  if (tab === 'library') $('historyPanel').scrollIntoView({block:'start',behavior:'instant'});
}
async function api(path, options = {}) {
  const response = await fetch('/api'+path, {headers:{'Content-Type':'application/json'},...options});
  let body = {};
  try { body = await response.json(); } catch { /* Error text handled below. */ }
  if (!response.ok) {
    const details = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail || body);
    throw new Error(details && details !== '{}' ? details : `Request failed (HTTP ${response.status})`);
  }
  return body;
}
async function updateStatus() {
  try {
    const data = await api('/status');
    const online = data.engine === 'online';
    $('engineBadge').classList.remove('checking');
    $('engineBadge').classList.toggle('offline', !online);
    $('engineBadge').querySelector('.engine-label').textContent = online ? 'Engine online' : 'Engine offline';
    $('engineBadge').title = online ? 'Local extraction engine connected' : data.engine_error || 'Engine unavailable';
    $('statEngine').textContent = online ? 'Online' : 'Offline';
    $('statEngine').closest('.engine-stat').dataset.state = online ? 'online' : 'offline';
  } catch (error) {
    $('engineBadge').classList.remove('checking');
    $('engineBadge').classList.add('offline');
    $('engineBadge').querySelector('.engine-label').textContent = 'Engine unavailable';
    $('statEngine').textContent = 'Unknown';
    $('statEngine').closest('.engine-stat').dataset.state = 'offline';
    $('engineBadge').title = error.message;
  }
}
async function updateJobs(manual = false) {
  if (manual) {
    $('refreshBtn').disabled = true;
    $('refreshBtn').setAttribute('aria-busy', 'true');
    $('refreshBtn').setAttribute('aria-label', 'Refreshing archive');
  }
  try {
    const data = await api('/jobs');
    jobs = Array.isArray(data.jobs) ? data.jobs : [];
    archiveLoaded = true;
    if ($('archiveNotice').dataset.source === 'refresh') clearNotice('archiveNotice');
    $('statJobs').textContent = String(jobs.length);
    $('statPages').textContent = String(jobs.reduce((count,j) => count + (j.kind === 'map' ? 0 : (j.page_count || 0)), 0));
    renderJobs();
    if (selectedJob && !$('detailsPanel').classList.contains('hidden')) {
      await showJob(selectedJob, false, true);
    }
  } catch (error) {
    if (!archiveLoaded) {
      $('jobsBody').replaceChildren();
      append(append($('jobsBody'), 'tr'), 'td', 'empty', 'Archive unavailable. Use Refresh to try again.').colSpan = 5;
    }
    notice('archiveNotice', `Could not refresh archive: ${error.message}`, true);
    $('archiveNotice').dataset.source = 'refresh';
  } finally {
    if (manual) {
      $('refreshBtn').disabled = false;
      $('refreshBtn').removeAttribute('aria-busy');
      $('refreshBtn').setAttribute('aria-label', 'Refresh archive');
    }
  }
}
function renderJobs() {
  const snapshot = JSON.stringify([jobs, selectedJob]);
  if (snapshot === renderedJobs) return;
  renderedJobs = snapshot;
  const focusedJob = document.activeElement?.dataset.inspectId;
  const tbody = $('jobsBody');
  tbody.replaceChildren();
  if (!jobs.length) {
    const cell = append(append(tbody, 'tr'), 'td', 'empty');
    cell.colSpan = 5;
    const empty = append(cell, 'div', 'empty-state');
    append(empty, 'span', 'empty-icon').appendChild(icon('archive'));
    append(empty, 'strong', '', 'Your next discovery starts here');
    append(empty, 'p', '', 'Run your first extraction. Its progress and saved content will appear here.');
    return;
  }
  for (const item of jobs) {
    const row = append(tbody,'tr');
    const op = append(row,'td');
    op.dataset.label = 'Operation';
    append(op,'div','type',item.kind);
    const url = item.args?.url || item.args?.urls?.[0] || '';
    const address = append(op,'div','muted operation-url',url);
    address.title = url;
    append(row,'td','progress-text',`${item.completed} / ${item.requested}`).dataset.label = 'Progress';
    const statusCell = append(row,'td');
    statusCell.dataset.label = 'Status';
    append(statusCell,'span',`tag ${item.status}`,item.status);
    append(row,'td','muted',fmtDate(item.created_at)).dataset.label = 'Created';
    const actionCell = append(row,'td');
    actionCell.dataset.label = 'Action';
    const button = append(actionCell,'button','view-btn','Inspect');
    button.appendChild(icon('arrow'));
    button.type = 'button';
    button.dataset.inspectId = item.id;
    button.setAttribute('aria-label',`Inspect ${item.kind} operation for ${url}`);
    button.setAttribute('aria-pressed',String(item.id === selectedJob));
  }
  if (focusedJob) {
    const replacement = Array.from(tbody.querySelectorAll('[data-inspect-id]')).find(button => button.dataset.inspectId === focusedJob);
    replacement?.focus({preventScroll:true});
  }
}
async function submitForm(event) {
  event.preventDefault();
  const submit = $('submitBtn');
  const route = currentTab === 'library' ? 'scrape' : currentTab;
  let payload;
  if (route === 'batch') payload = {urls:$('batchInput').value.split(/\r?\n/).map(x=>x.trim()).filter(Boolean)};
  else {
    payload = {url:$('urlInput').value.trim()};
    if (route === 'map' || route === 'crawl') payload.limit = Number($('limitInput').value);
    if (route === 'crawl') payload.depth = Number($('depthInput').value);
  }
  submit.disabled = true;
  submit.setAttribute('aria-busy', 'true');
  submit.querySelector('.submit-label').textContent = 'Creating operation…';
  try {
    const result = await api('/'+route,{method:'POST',body:JSON.stringify(payload)});
    notice('notice','Operation created. Its progress and extracted content are available in the archive.');
    await updateJobs();
    await showJob(result.id,true);
  } catch(error) { notice('notice',error.message,true); }
  finally {
    submit.disabled = false;
    submit.removeAttribute('aria-busy');
    submit.querySelector('.submit-label').textContent = tabs[currentTab].button;
  }
}
async function showJob(id, scroll = true, quiet = false) {
  const requestId = ++inspectorRequest;
  if (!quiet) {
    clearNotice('archiveNotice');
    notice('archiveNotice','Opening inspector…');
  }
  try {
    const job = await api(`/jobs/${encodeURIComponent(id)}`);
    if (requestId !== inspectorRequest) return;
    const snapshot = JSON.stringify(job);
    if (quiet && selectedJob === id && snapshot === inspectorSnapshot) {
      if ($('archiveNotice').dataset.source === 'inspector') clearNotice('archiveNotice');
      return;
    }
    const expandedPages = new Set(Array.from($('pageList').querySelectorAll('details[open]')).map(element => element.dataset.pageId));
    const focusedDisclosure = document.activeElement?.closest('#pageList details')?.dataset.pageId;
    const focusedPreview = document.activeElement?.matches('#pageList .preview');
    const focusedLinks = document.activeElement?.matches('#pageList .links');
    const contentScroll = focusedPreview || focusedLinks ? document.activeElement.scrollTop : 0;
    const sameJob = selectedJob === id;
    inspectorSnapshot = snapshot;
    selectedJob = id;
    renderJobs();
    const details = $('detailsPanel');
    details.classList.remove('hidden');
    $('detailTitle').textContent = `${String(job.kind).charAt(0).toUpperCase()+String(job.kind).slice(1)} · ${job.status}`;
    $('detailSummary').textContent = `${job.completed}/${job.requested} processed · ${fmtDate(job.created_at)}${job.error ? ' · '+job.error : ''}`;
    $('cancelBtn').classList.toggle('hidden',!['queued','running'].includes(job.status));
    $('exportToolbar').querySelectorAll('button').forEach((button) => {
      button.disabled = job.kind === 'map' && button.dataset.format !== 'json';
      button.title = button.disabled ? 'URL maps support JSON export only' : `Download ${button.textContent}`;
      button.onclick = () => {
        window.location.assign(`/api/jobs/${encodeURIComponent(job.id)}/export?format=${encodeURIComponent(button.dataset.format)}`);
      };
    });
    const pages = $('pageList');
    pages.replaceChildren();
    if (job.kind === 'map') {
      const block = append(pages,'div','page-item');
      append(block,'strong','',`Discovered ${(job.links || []).length} links`);
      const links = append(block,'div','links');
      links.tabIndex = 0;
      links.setAttribute('role','region');
      links.setAttribute('aria-label','Discovered URL list');
      for (const url of job.links || []) {
        const label = typeof url === 'string' ? url : url?.url || (url == null ? '' : JSON.stringify(url));
        append(links,'div','link-item',label || 'Unavailable URL');
      }
    } else if (!job.pages?.length) {
      append(pages,'div','empty','No documents saved yet. Refresh the archive to check for updates.');
    }
    for (const page of job.pages || []) {
      const block = append(pages,'article','page-item');
      append(append(block,'div','page-top'),'strong','',page.title || 'Untitled page');
      append(block,'div','page-url',page.url);
      const chips = append(block,'div','product-strip');
      const product = page.product || {};
      if (product.name) append(chips,'span','chip',`Product: ${String(product.name).slice(0,65)}`);
      if (product.price) append(chips,'span','chip',`${product.price} ${product.currency || ''}`);
      if (product.brand) append(chips,'span','chip',`Brand: ${product.brand}`);
      if (product.sizes?.length) append(chips,'span','chip',`Sizes: ${product.sizes.join(', ')}`);
      if (product.missing_fields?.length) append(chips,'span','chip',`Missing: ${product.missing_fields.join(', ')}`);
      const disclosure = append(block,'details');
      disclosure.dataset.pageId = String(page.id);
      disclosure.open = sameJob && expandedPages.has(String(page.id));
      append(disclosure,'summary','',`Inspect extracted content (${(page.markdown || '').length} Markdown characters)`);
      const preview = append(disclosure,'pre','preview',(page.markdown || 'No Markdown content was returned').slice(0,6000));
      preview.tabIndex = 0;
      preview.setAttribute('role','region');
      preview.setAttribute('aria-label','Extracted Markdown preview');
    }
    clearNotice('archiveNotice');
    if (quiet && focusedDisclosure) {
      const disclosure = Array.from(pages.querySelectorAll('details')).find(element => element.dataset.pageId === focusedDisclosure);
      const control = disclosure?.querySelector(focusedPreview ? '.preview' : 'summary');
      control?.focus({preventScroll:true});
      if (focusedPreview && control) control.scrollTop = contentScroll;
    } else if (quiet && focusedLinks) {
      const links = pages.querySelector('.links');
      links?.focus({preventScroll:true});
      if (links) links.scrollTop = contentScroll;
    }
    if (scroll) {
      details.scrollIntoView({behavior:'instant',block:'start'});
      details.focus({preventScroll:true});
    }
  } catch (error) {
    if (requestId !== inspectorRequest) return;
    // Archive is always visible, including on the Archive-only tab.
    notice('archiveNotice',`Couldn't open this operation: ${error.message}`,true);
    $('archiveNotice').dataset.source = 'inspector';
  }
}
async function cancelJob() {
  if (!selectedJob) return;
  $('cancelBtn').disabled = true;
  $('cancelBtn').textContent = 'Cancelling…';
  try { await api(`/jobs/${encodeURIComponent(selectedJob)}/cancel`,{method:'POST'}); await updateJobs(); }
  catch (error) { notice('archiveNotice',error.message,true); }
  finally { $('cancelBtn').disabled = false; $('cancelBtn').textContent = 'Cancel job'; }
}
function closeDetails() {
  const previousJob = selectedJob;
  inspectorRequest += 1;
  selectedJob = null;
  inspectorSnapshot = '';
  $('detailsPanel').classList.add('hidden');
  clearNotice('archiveNotice');
  renderJobs();
  const button = Array.from($('jobsBody').querySelectorAll('[data-inspect-id]')).find(element => element.dataset.inspectId === previousJob);
  const target = button || $('historyPanel');
  target.scrollIntoView({block:'center',behavior:'instant'});
  button?.focus({preventScroll:true});
}
window.addEventListener('DOMContentLoaded',() => {
  document.querySelectorAll('.nav-item').forEach(button => button.addEventListener('click',() => switchTab(button.dataset.tab)));
  $('jobsBody').addEventListener('click',(event) => {
    const button = event.target.closest('button[data-inspect-id]');
    if (button) void showJob(button.dataset.inspectId,true);
  });
  $('operationForm').addEventListener('submit',submitForm);
  $('refreshBtn').addEventListener('click',() => { void updateJobs(true); });
  $('cancelBtn').addEventListener('click',cancelJob);
  $('closeDetailsBtn').addEventListener('click',closeDetails);
  $('detailsPanel').addEventListener('keydown',event => {
    if (event.key === 'Escape') { event.preventDefault(); closeDetails(); }
  });
  switchTab('scrape');
  void updateStatus();
  void updateJobs();
  refreshTimer = setInterval(() => { void updateStatus(); void updateJobs(); },5000);
});
