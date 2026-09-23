'use strict';
const $ = id => document.getElementById(id);
let credential = sessionStorage.getItem('levelground-access') || '';
let project = null, stage = 'pre_bid', reportId = null;
const drafts = new Map();
const names = {pre_bid: 'Plan & budget review', bid_gap: 'Builder bid review'};
const statuses = {awaiting_answer: 'Awaiting your answer', answer_received_needs_review: 'Saved · awaiting review', review_accepted: 'Reviewed · resolved', review_needs_clarification: 'More detail needed', review_rejected: 'Answer needs correction'};
function node(tag, text, className) { const el = document.createElement(tag); if (text !== undefined) el.textContent = text; if (className) el.className = className; return el; }
function message(text, error = false) { $('message').textContent = text; $('message').className = error ? 'error' : ''; }
function lock() { credential = ''; project = null; drafts.clear(); sessionStorage.removeItem('levelground-access'); $('project').hidden = true; $('access').hidden = false; $('sign-out').hidden = true; $('reviewer-tools').hidden = true; $('access-code').value = ''; for (const id of ['case-label','report','questions','documents','reviewer-bid-list']) $(id).replaceChildren(); }
async function api(path, payload) {
  const response = await fetch(path, {method: payload === undefined ? 'GET' : 'POST', headers: {Authorization: `Bearer ${credential}`, ...(payload === undefined ? {} : {'Content-Type': 'application/json'})}, body: payload === undefined ? undefined : JSON.stringify(payload), cache: 'no-store'});
  if (!response.ok) { if (response.status === 401) { lock(); throw new Error('Your access code has expired or is no longer valid. Open the project with a current code.'); } const detail = await response.json(); throw new Error(detail.error || 'The request could not be saved. Try again.'); }
  return response;
}
async function run(button, action) { button.disabled = true; try { await action(); } catch (error) { message(error.message, true); } finally { button.disabled = false; } }
async function refresh() {
  const access = credential;
  const [current, session] = await Promise.all([api('/api/case').then(r => r.json()), api('/api/session').then(r => r.json())]);
  if (credential !== access) return;
  project = current;
  sessionStorage.setItem('levelground-access', credential);
  $('access-code').value = ''; $('access').hidden = true; $('project').hidden = false; $('sign-out').hidden = false;
  $('case-label').textContent = project.label; renderDocuments(); renderStage();
  await renderReviewer(session.role, access);
}
async function renderReviewer(role, access) {
  $('reviewer-bid-list').replaceChildren(); $('reviewer-tools').hidden = role !== 'reviewer';
  if (role !== 'reviewer') return;
  const queue = await (await api('/api/reviewer-queue')).json();
  if (credential !== access || !project) return;
  const items = queue.items.filter(item => item.trade_bid_drafts_request);
  if (!items.length) $('reviewer-bid-list').append(node('p', 'Bid drafts become available after a plan is selected and its sheets and measurements are prepared.'));
  for (const item of items) {
    const section = node('section', undefined, 'finding'), button = node('button', 'Open current drafts'), content = node('div');
    button.type = 'button'; section.append(node('h3', item.filename || 'Reviewed plan'), button, content);
    button.addEventListener('click', () => run(button, async () => {
      const result = await (await api(item.trade_bid_drafts_request.url)).json();
      if (credential !== access || !section.isConnected) return;
      renderTradeDrafts(content, result, item.trade_bid_drafts_request.url, access);
    }));
    $('reviewer-bid-list').append(section);
  }
}
function renderTradeDrafts(target, result, endpoint, access) {
  target.replaceChildren();
  target.append(node('p', result.notice, 'hint'));
  if (!result.drafts.length) target.append(node('p', 'No supported trade drafts are available for this plan yet.'));
  for (const draft of result.drafts) {
    const detail = node('details'), download = node('button', 'Download ' + draft.trade.toLowerCase() + ' draft');
    const status = {current:'Saved draft matches this revision.', older_revision:'Saved draft is older; the text below uses the current revision.', not_saved:'Current draft has not been saved yet.'};
    detail.append(node('summary', draft.trade + (draft.scope_kind === 'company_scope_additions' ? ' · Scope additions' : ' · Bid request')),
      node('p', status[draft.saved_snapshot_status] + ' Revision ' + result.measurement_version + '.', 'hint'), node('pre', draft.markdown));
    download.type = 'button';
    download.addEventListener('click', () => run(download, async () => {
      const fresh = await (await api(endpoint)).json();
      if (credential !== access || !target.isConnected) return;
      const current = fresh.drafts.find(item => item.trade === draft.trade && item.scope_kind === draft.scope_kind);
      renderTradeDrafts(target, fresh, endpoint, access);
      if (!current) throw new Error('This scope is no longer available. Review the current drafts.');
      const blob = new Blob([current.markdown], {type:'text/markdown;charset=utf-8'}), url = URL.createObjectURL(blob), link = node('a');
      link.href = url; link.download = current.trade.toLowerCase() + '-draft-revision-' + fresh.measurement_version + '.md';
      document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
      message('Download requested for the current ' + current.trade.toLowerCase() + ' draft. Check your browser downloads. Nothing was sent.');
    }));
    detail.append(download); target.append(detail);
  }
}
function renderDocuments() {
  $('documents').replaceChildren();
  if (!project.documents.length) $('documents').append(node('li', 'No documents yet. Add your plans or your builder’s bid above.'));
  for (const file of project.documents) {
    const item = node('li'); item.append(node('strong', file.filename), node('div', `${Math.ceil(file.bytes / 1024)} KB · saved`, 'hint'));
    const button = node('button', 'Download document'); button.type = 'button';
    button.addEventListener('click', () => run(button, async () => {
      const blob = await (await api('/api/evidence/' + encodeURIComponent(file.id))).blob();
      const url = URL.createObjectURL(blob), link = node('a'); link.href = url; link.download = file.filename; document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
    })); item.append(button); $('documents').append(item);
  }
}
function renderStage() {
  for (const button of document.querySelectorAll('[data-stage]')) button.setAttribute('aria-pressed', String(button.dataset.stage === stage));
  $('review-title').textContent = names[stage];
  const reports = project.reports.filter(report => report.stage === stage);
  if (!reports.some(report => report.id === reportId)) reportId = reports.at(-1)?.id || null;
  $('report-version').replaceChildren(); $('report-version').disabled = !reports.length;
  $('download-report').hidden = !reportId;
  reports.forEach((report, index) => { const option = node('option', `Version ${index + 1} · ${new Date(report.created_at).toLocaleDateString()}`); option.value = report.id; option.selected = report.id === reportId; $('report-version').append(option); });
  $('report').replaceChildren(); $('questions').replaceChildren();
  if (!reportId) { $('report').append(node('p', stage === 'pre_bid' ? 'Your plan review will appear here when it is ready. Start by uploading your plans.' : 'Your bid review will appear here when it is ready. Upload your builder’s bid when you receive it.', 'summary')); $('questions').append(node('p', 'Questions will appear with your review.')); return; }
  const report = reports.find(item => item.id === reportId), source = report.current_report_view || report.source_report;
  const summary = node('div', undefined, 'summary');
  if (source.meta?.is_sample) summary.append(node('p', 'Sample project · demonstration only', 'status'));
  summary.append(node('p', source.meta?.verdict_note || 'Read the findings and answer the questions below.'));
  const money = value => typeof value === 'number' && Number.isFinite(value) ? new Intl.NumberFormat('en-US', {style:'currency',currency:'USD',maximumFractionDigits:0}).format(value) : 'Not established';
  const totals = node('dl'); totals.append(node('dt', 'Builder bid'), node('dd', money(source.meta?.bid_total)), node('dt', 'Budget range'), node('dd', source.meta?.our_range?.low != null && source.meta?.our_range?.high != null ? `${money(source.meta.our_range.low)} – ${money(source.meta.our_range.high)}` : 'Not established')); summary.append(totals);
  for (const finding of source.findings || []) { const section = node('div', undefined, 'finding'); section.append(node('h3', finding.title), node('p', finding.detail)); if (finding.basis) section.append(node('p', finding.basis, 'hint')); summary.append(section); }
  if (source.quantities?.length) {
    const detail = node('details'), scroll = node('div', undefined, 'table-scroll'), table = node('table'), head = node('tr');
    detail.append(node('summary', 'Measurements in this report')); for (const text of ['Item','Quantity','Source']) { const th = node('th', text); th.scope = 'col'; head.append(th); } table.append(head);
    for (const quantity of source.quantities) { const row = node('tr'); row.append(node('td', quantity.item), node('td', `${quantity.qty ?? 'Not measured'} ${quantity.unit || ''}`), node('td', `${quantity.source || 'Source pending'}${quantity.confidence ? ' · ' + quantity.confidence : ''}`)); table.append(row); } scroll.append(table); detail.append(scroll); summary.append(detail);
  }
  if (source.unknowns?.length) { const detail = node('details'); detail.append(node('summary', 'What still needs to be established')); const list = node('ul'); source.unknowns.forEach(text => list.append(node('li', text))); detail.append(list); summary.append(detail); }
  summary.append(node('p', 'Answer reviews update the questions below. Measurements, prices and original findings require a separate report revision.', 'hint')); $('report').append(summary);
  if (!report.questions.length) $('questions').append(node('p', 'There are no questions in this report.'));
  report.questions.forEach((question, index) => renderQuestion(report, question, index));
}
function renderQuestion(report, question, index) {
  const form = node('form', undefined, 'question'), label = node('label', `${index + 1}. ${question.text}`), input = node('textarea');
  input.id = 'answer-' + question.id; label.htmlFor = input.id; input.required = true;
  const latest = question.answers.at(-1), key = report.id + ':' + question.id, draft = drafts.get(key);
  input.value = draft?.text ?? latest?.text ?? '';
  form.append(node('span', statuses[question.status] || 'Awaiting review', 'status'), label, input);
  const review = latest?.reviews.at(-1); if (review) form.append(node('p', review.rationale, 'review-note'));
  const evidence = node('fieldset'); evidence.append(node('legend', 'Supporting documents (optional)'));
  for (const file of project.documents) { const choice = node('label', undefined, 'check'), checkbox = node('input'); checkbox.type = 'checkbox'; checkbox.value = 'evidence:' + file.id; checkbox.checked = (draft?.evidence_refs ?? latest?.evidence_refs ?? []).includes(checkbox.value); choice.append(checkbox, node('span', file.filename)); evidence.append(choice); }
  if (!project.documents.length) evidence.append(node('p', 'Upload a written clarification to attach it here.', 'hint'));
  form.append(evidence); const button = node('button', latest ? 'Save updated answer' : 'Save answer'); button.type = 'submit'; form.append(button);
  function remember() {
    const refs = [...evidence.querySelectorAll('input:checked')].map(item => item.value);
    const value = {text: input.value, evidence_refs: [...refs, ...(latest?.evidence_refs || []).filter(ref => !ref.startsWith('evidence:'))]};
    drafts.set(key, value); return value;
  }
  form.addEventListener('input', remember);
  form.addEventListener('change', remember);
  form.addEventListener('submit', event => { event.preventDefault(); run(button, async () => {
    const submitted = remember();
    await api('/api/answers', {report_id:report.id, question_id:question.id, ...submitted});
    if (JSON.stringify(drafts.get(key)) === JSON.stringify(submitted)) drafts.delete(key);
    await refresh(); message('Answer saved. Your reviewer will check it against the supporting information.');
  }); });
  $('questions').append(form);
}
$('access-form').addEventListener('submit', event => { event.preventDefault(); run(event.submitter, async () => { credential = $('access-code').value.trim(); await refresh(); message('Project opened.'); }); });
$('sign-out').addEventListener('click', () => { lock(); message('Project closed on this device.'); });
$('refresh').addEventListener('click', event => run(event.currentTarget, async () => { await refresh(); message('Project refreshed.'); }));
document.querySelectorAll('[data-stage]').forEach(button => button.addEventListener('click', () => { stage = button.dataset.stage; reportId = null; renderStage(); }));
$('report-version').addEventListener('change', event => { reportId = event.target.value; renderStage(); });
$('download-report').addEventListener('click', event => run(event.currentTarget, async () => {
  const selected = reportId, access = credential;
  if (!selected) return;
  const blob = await (await api('/api/reports/' + encodeURIComponent(selected) + '/download')).blob();
  if (credential !== access || !project) return;
  const url = URL.createObjectURL(blob), link = node('a');
  link.href = url; link.download = 'level-ground-review-' + selected + '.html';
  document.body.append(link); link.click(); link.remove(); setTimeout(() => URL.revokeObjectURL(url), 1000);
  message('Review downloaded. Open the HTML file to read or print it. Only saved answers are included.');
}));
$('upload-form').addEventListener('submit', event => { event.preventDefault(); run(event.submitter, async () => {
  const file = $('document-file').files[0]; if (!file || !file.size || file.size > 25 * 1024 * 1024) throw new Error('Choose a nonempty file no larger than 25 MB.');
  const encoded = await new Promise((resolve, reject) => { const reader = new FileReader(); reader.onload = () => resolve(reader.result.split(',')[1]); reader.onerror = () => reject(new Error('This file could not be read. Choose it again.')); reader.readAsDataURL(file); });
  await api('/api/evidence', {filename:file.name,content_base64:encoded}); $('upload-form').reset(); await refresh(); message('Document uploaded and saved for review.');
}); });
if (credential) refresh().catch(error => message(error.message, true));
