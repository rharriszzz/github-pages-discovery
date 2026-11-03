'use strict';
const cards = [...document.querySelectorAll('article')];
const investigations = [...document.querySelectorAll('.investigation')];
const saved = structuredClone(BOOTSTRAP.reviews);
const online = Boolean(BOOTSTRAP.token) && location.protocol === 'http:';
document.querySelector('#mode').textContent = online ? 'Save writes to your private SQLite store.' : 'Offline preview: download feedback, then import it with creator-feedback.';
if (!online) for (const el of document.querySelectorAll('#refresh,.serverlink')) el.hidden = true;
function filter() {
  const q = document.querySelector('#search').value.toLowerCase();
  for (const c of [...cards, ...investigations]) {
    c.hidden = !c.textContent.toLowerCase().includes(q) || ['subject', 'method', 'direction', 'confidence'].some(k => {
      const v = document.getElementById(k).value;
      if (!v) return false;
      return k === 'subject' || k === 'method' ? !JSON.parse(c.dataset[k + 's']).includes(v) : c.dataset[k] !== v;
    });
  }
  if (document.querySelector('#confidence').value && document.querySelector('#confidence').value !== 'verified') document.querySelector('.audit').open = true;
  document.querySelector('#count').textContent = `${cards.filter(c => !c.hidden).length} of ${cards.length} candidates shown · ${investigations.filter(c => !c.hidden).length} investigations match`;
}
for (const el of document.querySelectorAll('.filters input,.filters select')) el.addEventListener('input', filter);
filter();
for (const card of cards) {
  const output = card.querySelector('output');
  const button = card.querySelector('.save');
  for (const control of card.querySelectorAll('select,textarea')) control.addEventListener('input', () => {
    output.textContent = 'Unsaved changes';
  });
  button.addEventListener('click', async () => {
    const row = {entity_id: card.dataset.id, decision: card.querySelector('.decision').value, reason: card.querySelector('textarea').value};
    if (!online) {
      saved[row.entity_id] = row;
      output.textContent = 'Ready to download; use Download feedback to retain this review.';
      return;
    }
    button.disabled = true;
    try {
      const res = await fetch('/api/review', {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Review-Token': BOOTSTRAP.token}, body: JSON.stringify({version: 1, reviews: [row]})});
      if (!res.ok) throw Error('Request failed');
      saved[row.entity_id] = row;
      output.textContent = 'Saved to private store';
    } catch (_) { output.textContent = 'Save failed; your text is still here. Retry or download feedback.'; }
    finally { button.disabled = false; }
  });
}
document.querySelector('#export').addEventListener('click', () => {
  // Export current controls too, including notes not yet saved to the server.
  const reviews = cards.map(c => ({entity_id: c.dataset.id, decision: c.querySelector('.decision').value, reason: c.querySelector('textarea').value}));
  const blob = new Blob([JSON.stringify({version: 1, reviews}, null, 2)], {type: 'application/json'});
  const url = URL.createObjectURL(blob), a = document.createElement('a');
  a.href = url; a.download = 'creator-feedback.json'; a.click(); setTimeout(() => URL.revokeObjectURL(url), 1000);
});
window.addEventListener('beforeunload', e => {
  if (cards.some(c => c.querySelector('.decision').value !== saved[c.dataset.id]?.decision || c.querySelector('textarea').value !== saved[c.dataset.id]?.reason)) { e.preventDefault(); e.returnValue = ''; }
});
