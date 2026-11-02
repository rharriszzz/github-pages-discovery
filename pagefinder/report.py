"""Generate an offline searchable catalog and CSV from ranked records."""
import csv
import html
import json
from pathlib import Path
from .core import ROOT, rank_all


def render():
    rows = rank_all()
    docs, reports = ROOT / 'docs', ROOT / 'reports'
    docs.mkdir(exist_ok=True)
    reports.mkdir(exist_ok=True)
    columns = ['score', 'url', 'owner', 'account_type', 'title', 'summary', 'repository',
               'site_status', 'interests', 'source', 'account_type_source']
    with (reports / 'results.csv').open('w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        for row in rows:
            writer.writerow({**{k: row.get(k, '') for k in columns},
                             'interests': '; '.join(row.get('interests', []))})
    (reports / 'results.json').write_text(json.dumps(rows, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    cards = []
    for r in rows:
        h = lambda value: html.escape(str(value or ''), quote=True)
        url = h(r['url'])
        cat = ', '.join(r.get('interests') or [])
        matches = []
        for finding in r.get('evidence', []):
            evidence = ', '.join(m['term'] + ' (' + '/'.join(m['evidence']) + ')'
                                 for m in finding['matches'])
            matches.append(f"<li><strong>{h(finding['topic'])}</strong>: {h(evidence)}</li>")
        details = '<ul>' + ''.join(matches) + '</ul>' if matches else '<p>No matches found in available text.</p>'
        title = h(r.get('title') or r.get('summary') or r['url'])
        cards.append(f'''<article class="card" data-kind="{h(r.get('account_type'))}" data-search="{h(' '.join([r['url'],r.get('owner',''),r.get('title',''),r.get('summary',''),cat]))}">
          <div class="top"><span class="score">{r['score']} / 100</span><span>{h(r.get('account_type', 'Unknown'))} account</span><span>{h(r.get('site_status', 'unchecked'))}</span></div>
          <h2><a href="{url}" rel="noopener noreferrer" target="_blank">{title}</a></h2>
          <p>{h(r.get('summary') or r.get('repo_description') or 'No description available.')}</p>
          <p class="meta">{h(r['url'])}<br>Owner: <a href="https://github.com/{h(r['owner'])}">{h(r['owner'])}</a> · Repository: <a href="{h(r.get('repo_url') or ('https://github.com/' + r.get('repository','')))}">{h(r.get('repository','unknown'))}</a><br>Interests: {h(cat or 'none detected')}</p>
          <details><summary>Why this rating? / provenance</summary>{details}<p>Discovery: {h(r.get('source'))}<br>Owner classification: {h(r.get('account_type_source'))}</p></details>
        </article>''')
    content = '''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>GitHub Pages Interest Finder</title><style>
:root{font-family:Arial,Tahoma,sans-serif;color:#293743;background:#fffdf7}body{margin:0 auto;padding:2rem 1rem;max-width:1000px;line-height:1.5}h1{margin-bottom:.3rem}
.lede{max-width:900px;color:#415363}.controls{display:flex;gap:.7rem;flex-wrap:wrap;margin:1.5rem 0}input,select{font:inherit;padding:.6rem;border:1px solid #9ba5aa;border-radius:.4rem;background:#fff;min-width:190px}input{flex:1}
#count{color:#40536b}.card{background:#fff;border:1px solid #d9dce0;border-radius:12px;padding:1rem 1.3rem;margin:1rem 0;box-shadow:0 1px 3px #0001}.card h2{font-size:1.22rem;margin:.6rem 0}.card p{margin:.5rem 0}
.top{display:flex;gap:.6rem;align-items:center;flex-wrap:wrap;color:#5e6873;font-size:.86rem}.top span{background:#edf1f4;border-radius:5px;padding:.1rem .4rem}.top .score{background:#dfefff;color:#1c465e;font-weight:700}
a{color:#075994}a:hover{text-decoration-thickness:2px}.meta{font-size:.88rem;color:#5d6571;overflow-wrap:anywhere}details{margin-top:.8rem;font-size:.91rem}summary{cursor:pointer}
footer{margin:2rem 0;color:#60686d;font-size:.88rem}ul{padding-left:1.25rem}
</style></head><body><h1>GitHub Pages Interest Finder</h1>
<p class="lede">A selective catalog of GitHub Pages sites and how they connect to the research and software interests in the configurable profile. Ranking is a transparent keyword heuristic, <strong>not an AI judgement of project quality</strong>. GitHub account type means User or Organization, not verified human or corporate ownership.</p>
<div class="controls"><input id="query" type="search" placeholder="Search titles, owners, and interests" aria-label="Search sites"><select id="owner" aria-label="Owner type"><option value="all">All account types</option><option value="User">Personal accounts</option><option value="Organization">Organizations</option><option value="Unknown">Unknown</option></select></div>
<p id="count"></p><main>''' + '\n'.join(cards) + '''</main>
<footer>Generated ''' + 'checked-in sample' + ''' · This is a bounded research sample, not a census of GitHub Pages. Source and ranking evidence are shown for each entry.</footer>
<script>const q=document.getElementById('query'),s=document.getElementById('owner'),cards=[...document.querySelectorAll('.card')],out=document.getElementById('count');function filter(){const v=q.value.toLowerCase(),k=s.value;let shown=0;for(const c of cards){const ok=c.dataset.search.toLowerCase().includes(v)&&(k==='all'||c.dataset.kind===k);c.hidden=!ok;if(ok)shown++}out.textContent=shown+' of '+cards.length+' sites shown'}q.addEventListener('input',filter);s.addEventListener('change',filter);filter()</script></body></html>'''
    (docs / 'index.html').write_text(content, encoding='utf-8')
    print(f'Wrote {len(rows)} sites to docs/index.html, reports/results.csv and results.json')
