'use strict';
const $=s=>document.querySelector(s);
let view='', generation=0;
const el=(tag,text,cls)=>{const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(cls)n.className=cls;return n;};
function link(url,text){const a=el('a',text);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;}
async function request(path,data){const res=await fetch(path,data===undefined?{}:{method:'POST',headers:{'Content-Type':'application/json','X-Review-Token':TOKEN},body:JSON.stringify(data)});const body=await res.json();if(!res.ok)throw Error(body.error||'The private service could not complete this request.');return body;}
function status(sources){const missing=Object.entries(sources).filter(([name,s])=>name!=='index'&&s.status==='unavailable').map(([name])=>name==='shelf'?'arXiv Shelf':'Discovery');$('#source-warning').hidden=!missing.length;$('#source-warning').textContent=missing.length?missing.join(' and ')+' unavailable. Available and cached works remain searchable; see Sources and freshness below.':'';$('#sources').replaceChildren();for(const [name,s] of Object.entries(sources)){const line=el('p');line.textContent=name==='index'?`${s.active_works} works · ${s.researched} additionally researched · refreshed ${new Date(s.refreshed_at).toLocaleString()}`:`${name==='shelf'?'arXiv Shelf':'Discovery'}: ${s.status}${s.papers!==undefined?` · ${s.papers} papers · ${s.rated} rated`:''}${s.creator_cards?` · ${s.creator_cards} creator cards`:''}${s.message?' · '+s.message:''}`;$('#sources').append(line);}}
function card(w){
 const a=el('article');a.dataset.id=w.id;
 const authors=w.authors||[];const byline=authors.slice(0,3).join(', ')+(authors.length>3?` + ${authors.length-3} others`:'');
 a.append(el('div',`${w.kind.toUpperCase()} · ${w.origins.join(' + ')}${w.verified_at?' · checked '+w.verified_at.slice(0,10):''}`,'meta'),el('h2',w.title),el('p',byline||'Author not established','byline'));
 a.append(el('p',w.learn),el('p',w.relation+': '+w.reason,'reason'),el('p',w.effort,'meta'));
 if(w.start_here)a.append(el('p','Start here: '+w.start_here,'start'));
 if(w.active===false)a.append(el('p','This work is retained from your feedback; it is no longer in the current source index.','meta'));
 if(w.kind==='paper')a.append(el('p',`Shelf stars: ${w.star_rating?'★'.repeat(w.star_rating):'unrated'} · ${w.pdf_status==='verified_local'?'PDF verified on this machine':'local PDF not verified'} · collection and rating do not imply reading`,'meta'));
 const actions=el('div',undefined,'actions');const open=link(w.start_url||w.url,'Open');open.className='open';actions.append(open);
 const output=el('output',undefined,'feedback-message');output.setAttribute('aria-live','polite');
 const buttons=[];
 const specs=[['saved','Save for later',()=>w.feedback.saved],['completed','Already read / watched',()=>w.feedback.completed],['useful','Useful',()=>w.feedback.useful===1],['dismissed','Not for me',()=>w.feedback.useful===-1]];
 const notes=el('textarea');notes.rows=2;notes.maxLength=4000;notes.value=w.feedback.notes;
 const update=()=>{for(const [button,pressed] of buttons)button.setAttribute('aria-pressed',String(pressed()));};
 async function save(action,value,button){button.disabled=true;try{const state=await request('/api/learning-feedback',{id:w.id,action,value,notes:notes.value});w.feedback={...w.feedback,...state};update();notes.dataset.saved=notes.value;output.textContent='Saved privately';}catch(e){output.textContent=e.message+' Your notes are still here.';}finally{button.disabled=false;}}
 for(const [action,label,pressed] of specs){const b=el('button',label);b.type='button';b.addEventListener('click',()=>save(action,!pressed(),b));buttons.push([b,pressed]);actions.append(b);}update();a.append(actions);
 const details=el('details');details.append(el('summary','Evidence, prerequisites and learning details'));
 if(w.prerequisites)details.append(el('p','Suggested background: '+w.prerequisites));
 for(const [name,value] of Object.entries(w.facets))details.append(el('p',name.replaceAll('_',' ')+': '+value));
 if(w.abstract)details.append(el('p','Abstract: '+w.abstract));
 if(authors.length>3)details.append(el('p','Authors: '+authors.join(', ')));
 const sources=el('ul');for(const e of w.evidence||[]){const li=el('li');li.append(link(e.url,'Source'),document.createTextNode(' — '+e.note+(e.retrieved_at?' ('+e.retrieved_at.slice(0,10)+')':'')));sources.append(li);}details.append(sources);
 const limits=el('ul');for(const limitation of w.limitations||[])limits.append(el('li',limitation));details.append(limits);a.append(details);
 const label=el('label','Optional notes','notes-label');label.append(notes);notes.dataset.saved=notes.value;notes.addEventListener('input',()=>{output.textContent='Unsaved notes';});const saveNotes=el('button','Save notes');saveNotes.type='button';saveNotes.addEventListener('click',()=>save('notes',undefined,saveNotes));a.append(label,saveNotes,output);return a;
}
function hasUnsaved(){return [...document.querySelectorAll('textarea')].some(n=>n.value!==n.dataset.saved);}
async function run(){
 if(hasUnsaved()&&!confirm('There are unsaved notes. Leave them and run this search?'))return;
 const current=++generation;$('#message').textContent='Finding specific works…';
 const params=new URLSearchParams({q:$('#query').value,goal:$('#goal').value,time:$('#time').value,format:$('#format').value,view});
 try{const data=await request('/api/search?'+params);if(current!==generation)return;
 $('#results').replaceChildren(...data.results.map(card));$('#message').textContent=data.message+(data.results.length?` Showing ${data.results.length} of ${data.matched} matching works.`:'');status(data.sources);
 $('#related').replaceChildren();$('#related').hidden=!data.related;if(data.related){$('#related').append(el('h2','Optional related concept: '+data.related.label),el('p',data.related.explanation));for(const u of data.related.sources)$('#related').append(link(u,'Explore the source'),document.createTextNode(' · '));}
 for(const b of document.querySelectorAll('[data-view]'))b.setAttribute('aria-pressed',String(b.dataset.view===view));
 }catch(e){$('#message').textContent=e.message;}
}
$('#search-form').addEventListener('submit',e=>{e.preventDefault();run();});
for(const b of document.querySelectorAll('.examples button'))b.addEventListener('click',()=>{$('#query').value=b.textContent;view='';run();});
for(const b of document.querySelectorAll('[data-view]'))b.addEventListener('click',()=>{view=b.dataset.view;$('#query').value='';run();});
$('#refresh').addEventListener('click',async()=>{const b=$('#refresh');b.disabled=true;try{status(await request('/api/refresh',{}));$('#message').textContent='Local sources refreshed. No external requests were made.';}catch(e){$('#message').textContent=e.message;}finally{b.disabled=false;}});
window.addEventListener('beforeunload',e=>{if(hasUnsaved()){e.preventDefault();e.returnValue='';}});
request('/api/status').then(status).catch(e=>{$('#message').textContent=e.message;});
