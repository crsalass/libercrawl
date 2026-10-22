'use strict';

const $ = (id) => document.getElementById(id);
const tabs = {
  scrape: {crumb:'Single scrape', title:'Extract the Web.<br><em>Free the data.</em>', desc:'Fetch structured information from public webpages, process it with your own local extraction engine, and keep every result under your control.', form:'Single page scrape', button:'Run local scrape', help:'Extract Markdown, HTML, links and deterministic JSON-LD product candidates.'},
  batch: {crumb:'Batch scrape', title:'Many URLs.<br><em>One workspace.</em>', desc:'Extract several webpages using a bounded local queue, with each result archived independently.', form:'Batch scrape', button:'Run batch scrape', help:'Each public URL is fetched in sequence. Partial successes are saved.'},
  crawl: {crumb:'Crawl site', title:'Explore further.<br><em>Stay in control.</em>', desc:'Discover and scrape pages on a domain while maintaining clear limits on depth and page count.', form:'Website crawl', button:'Start local crawl', help:'A local crawl job collects public pages from the same site.'},
  map: {crumb:'Map URLs', title:'Discover first.<br><em>Extract later.</em>', desc:'Find the URLs on a website before committing to a full scrape.', form:'URL discovery', button:'Map website', help:'Mapping returns URLs only, without archived page content.'},
  library: {crumb:'Archive', title:'Every result.<br><em>Under your control.</em>', desc:'Explore your local history, inspect saved pages and export them in the format you need.', form:'Create another scrape', button:'Run local scrape', help:'Select an operation below to inspect its results.'}
};
let currentTab = 'scrape';
let selectedJob = null;
let jobs = [];
let refreshTimer = null;
let inspectorRequest = 0;

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
function notice(id, value, error = false) {
  const element = $(id);
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
  $('formHelp').textContent = info.help;
  $('submitBtn').querySelector('.submit-label').textContent = info.button;
  $('batchBlock').classList.toggle('hidden', tab !== 'batch');
  $('crawlOptions').classList.toggle('hidden', !['crawl','map'].includes(tab));
  $('depthWrap').classList.toggle('hidden', tab !== 'crawl');
  $('urlInput').classList.toggle('hidden', tab === 'batch');
  $('urlLabel').classList.toggle('hidden', tab === 'batch');
  $('urlInput').required = tab !== 'batch';
  $('batchInput').required = tab === 'batch';
  $('limitInput').max = tab === 'map' ? '250' : '50';
  $('limitInput').value = tab === 'map' ? '30' : '10';
  $('operationPanel').classList.toggle('hidden', tab === 'library');
  clearNotice('notice');
  if (tab === 'library') $('historyPanel').scrollIntoView({block:'start',behavior:'smooth'});
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
    $('engineBadge').classList.toggle('offline', !online);
    $('engineBadge').querySelector('.engine-label').textContent = online ? 'Engine online' : 'Engine offline';
    $('engineBadge').title = online ? 'Local local extraction engine connected' : data.engine_error || 'Engine unavailable';
    $('statEngine').textContent = online ? 'Online' : 'Offline';
    $('statEngine').style.color = online ? 'var(--success)' : 'var(--danger)';
  } catch (error) {
    $('engineBadge').classList.add('offline');
    $('engineBadge').querySelector('.engine-label').textContent = 'Engine unavailable';
    $('statEngine').textContent = 'Unavailable';
    $('statEngine').style.color = 'var(--danger)';
    $('engineBadge').title = error.message;
  }
}
async function updateJobs() {
  try {
    const data = await api('/jobs');
    jobs = Array.isArray(data.jobs) ? data.jobs : [];
    $('statJobs').textContent = String(jobs.length);
    $('statPages').textContent = String(jobs.reduce((count,j) => count + (j.kind === 'map' ? 0 : (j.page_count || 0)), 0));
    renderJobs();
    if (selectedJob && !$('detailsPanel').classList.contains('hidden')) {
      await showJob(selectedJob, false, true);
    }
  } catch (error) {
    notice('archiveNotice', `Could not refresh archive: ${error.message}`, true);
  }
}
function renderJobs() {
  const tbody = $('jobsBody');
  tbody.replaceChildren();
  if (!jobs.length) {
    append(append(tbody,'tr'),'td','empty','No operations yet. Start by extracting a website.').colSpan = 5;
    return;
  }
  for (const item of jobs) {
    const row = append(tbody,'tr');
    const op = append(row,'td');
    op.dataset.label = 'Operation';
    append(op,'div','type',item.kind);
    const url = item.args?.url || item.args?.urls?.[0] || '';
    append(op,'div','muted',url.length > 52 ? `${url.slice(0,50)}…` : url);
    append(row,'td','',`${item.completed} / ${item.requested}`).dataset.label = 'Progress';
    const statusCell = append(row,'td');
    statusCell.dataset.label = 'Status';
    append(statusCell,'span',`tag ${item.status}`,item.status);
    append(row,'td','muted',fmtDate(item.created_at)).dataset.label = 'Created';
    const actionCell = append(row,'td');
    actionCell.dataset.label = 'Action';
    const button = append(actionCell,'button','view-btn','Inspect ↗');
    button.type = 'button';
    button.dataset.inspectId = item.id;
    button.setAttribute('aria-label',`Inspect ${item.kind} operation`);
    button.setAttribute('aria-pressed',String(item.id === selectedJob));
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
  try {
    const result = await api('/'+route,{method:'POST',body:JSON.stringify(payload)});
    notice('notice','Operation created. Its progress and extracted content are available in the archive.');
    await updateJobs();
    await showJob(result.id,true);
  } catch(error) { notice('notice',error.message,true); }
  finally { submit.disabled = false; }
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
    selectedJob = id;
    renderJobs();
    const details = $('detailsPanel');
    details.classList.remove('hidden');
    $('detailTitle').textContent = `${String(job.kind).charAt(0).toUpperCase()+String(job.kind).slice(1)} · ${job.status}`;
    $('detailSummary').textContent = `${job.completed}/${job.requested} processed · ${fmtDate(job.created_at)}${job.error ? ' · '+job.error : ''}`;
    $('cancelBtn').classList.toggle('hidden',!['queued','running'].includes(job.status));
    $('exportToolbar').querySelectorAll('button').forEach((button) => {
      button.disabled = job.kind === 'map' && button.dataset.format !== 'json';
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
      for (const url of job.links || []) append(links,'div','link-item',typeof url === 'string' ? url : url.url || JSON.stringify(url));
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
      append(disclosure,'summary','',`Inspect extracted content (${(page.markdown || '').length} Markdown characters)`);
      append(disclosure,'pre','preview',(page.markdown || 'No Markdown content was returned').slice(0,6000));
    }
    clearNotice('archiveNotice');
    if (scroll) {
      details.scrollIntoView({behavior:'smooth',block:'start'});
      details.focus({preventScroll:true});
    }
  } catch (error) {
    if (requestId !== inspectorRequest) return;
    // Archive is always visible, including on the Archive-only tab.
    notice('archiveNotice',`Couldn't open this operation: ${error.message}`,true);
  }
}
async function cancelJob() {
  if (!selectedJob) return;
  try { await api(`/jobs/${encodeURIComponent(selectedJob)}/cancel`,{method:'POST'}); await updateJobs(); }
  catch (error) { notice('archiveNotice',error.message,true); }
}
function closeDetails() {
  inspectorRequest += 1;
  selectedJob = null;
  $('detailsPanel').classList.add('hidden');
  clearNotice('archiveNotice');
  renderJobs();
  $('historyPanel').scrollIntoView({block:'start',behavior:'smooth'});
}
window.addEventListener('DOMContentLoaded',() => {
  document.querySelectorAll('.nav-item').forEach(button => button.addEventListener('click',() => switchTab(button.dataset.tab)));
  $('jobsBody').addEventListener('click',(event) => {
    const button = event.target.closest('button[data-inspect-id]');
    if (button) void showJob(button.dataset.inspectId,true);
  });
  $('operationForm').addEventListener('submit',submitForm);
  $('refreshBtn').addEventListener('click',updateJobs);
  $('cancelBtn').addEventListener('click',cancelJob);
  $('closeDetailsBtn').addEventListener('click',closeDetails);
  switchTab('scrape');
  void updateStatus();
  void updateJobs();
  refreshTimer = setInterval(() => { void updateStatus(); void updateJobs(); },5000);
});
