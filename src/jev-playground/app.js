/* Local-only playground. The browser never receives or stores a Jev API credential. */
(() => {
  'use strict';
  const C=JevPlaygroundCore,$=id=>document.getElementById(id);
  const node=(tag,cls,text)=>{const n=document.createElement(tag);if(cls)n.className=cls;if(text!==undefined)n.textContent=text;return n;};
  let boot,run,selectedId='',view='state',editor=null,stateEditor=null,lastStateText='',pollTimer=null,loading=false,activeRunId=null,historyTimer=null;
  let comparisonGrade='gaza_grade',comparisonScore='pro_palestine_score',gradeMapping=C.defaultScoreGradeMapping;
  let baselineId='',answerSignature='',monacoReady=false;const expandedAnswers=new Set();
  const rows=()=>run?.scope==='latest'?run.rows:C.catalogRows(boot.snapshot,run),races=()=>run?.scope==='latest'?run.races:C.catalogRaces(boot.snapshot,run);
  const raceLabel=race=>C.raceLabel(race,ContestLabel.districtLabel);
  const latestMode=()=>run?.scope==='latest';
  const scopeLabel=scope=>scope==='bay-area'?'Bay Area':scope==='candidate'?'Selected candidate':'Full roster';
  function updateScope(){const current=boot.snapshot;$('scope').textContent=`${current.candidates.length} candidates · ${current.races.length} races · U.S. House + five Bay Area counties`;$('run').textContent='Run full roster ('+current.candidates.length+')';const bay=current.scope_counts?.['bay-area'];$('run-bay-area').textContent=bay?'Run Bay Area ('+bay.candidates+')':'Run Bay Area';$('run-bay-area').title=bay?bay.candidates+' candidates across '+bay.races+' races serving '+current.bay_area_counties.join(', '):'Restart the local server to load Bay Area batch support.';}
  const formatTime=value=>new Date(value).toLocaleString('en-US',{timeZone:'America/Los_Angeles',dateStyle:'medium',timeStyle:'short'})+' PT';
  const text=()=>editor?editor.getValue():$('questions').value;
  function setText(value){$('questions').value=value;if(editor)editor.setValue(value);validate();}
  async function api(path,options={}){const r=await fetch(path,{...options,headers:{'Content-Type':'application/json',...options.headers}});let data;try{data=await r.json();}catch{throw new Error('Local server returned an unreadable response.');}if(!r.ok)throw new Error(data.error||'Local request failed.');return data;}
  function error(message){$('fatal').textContent=message||'';$('fatal').hidden=!message;}
  function validate(){let valid=true;try{C.parseQuestions(text());$('question-error').hidden=true;}catch(e){valid=false;$('question-error').textContent=e.message;$('question-error').hidden=false;}
    const busy=!!activeRunId||run&&['running','cancelling'].includes(run.status);$('run').disabled=!valid||busy||!!activeRunId||loading||!boot?.key_configured;const selected=run?rows().find(r=>r.id===selectedId):null,eligible=!!boot?.snapshot.candidates.some(c=>c.id===selectedId);$('run-selected').disabled=$('run').disabled||!eligible;$('run-bay-area').disabled=$('run').disabled||!boot?.snapshot.scope_counts?.['bay-area']?.candidates;$('selected-target').textContent=selected?'Selected: '+selected.candidate:'';$('stop').hidden=!busy;$('stop').disabled=run?.status==='cancelling';$('run-selected').textContent=loading?'Starting…':busy?'Running…':'Run selected candidate';
    let differs=false;try{differs=JSON.stringify(C.parseQuestions(text()))!==JSON.stringify(selected?.request?.questions||run?.questions);}catch{}
    $('editor-status').textContent=differs?'Draft changed · saved results shown until rerun':'';if(run){resultNotice();if(rows().find(r=>r.id===selectedId)?.status==='preview')inspect();}return valid;
  }
  const matchesCounty=race=>C.countyMatches(race,$('county').value,boot.snapshot.bay_area_counties||[]);
  function setupCountyFilter(){const value=$('county').value||'all';$('county').replaceChildren();for(const [key,label]of [['all','All tracked candidates'],['bay-area','All 5 Bay Area counties'],...(boot.snapshot.bay_area_counties||[]).map(c=>[c,c])]){const option=node('option',null,label);option.value=key;$('county').append(option);}$('county').value=value;}
  function setupStates(){const prior=$('state').value;$('state').replaceChildren(node('option',null,'All states'));$('state').firstChild.value='';const states=[...new Set(races().map(r=>r.state))].sort((a,b)=>ContestLabel.stateLabel(a).localeCompare(ContestLabel.stateLabel(b)));for(const s of states){const o=node('option',null,ContestLabel.stateLabel(s));o.value=s;$('state').append(o);}$('state').value=states.includes(prior)?prior:'';}
  function orderedCandidates(){const catalog=rows(),ordered=[];for(const race of C.sortRaces(races(),ContestLabel.stateLabel).filter(matchesCounty))for(const row of catalog.filter(r=>r.position_id===race.id))ordered.push({row,race});return ordered;}
  function setupCandidatePicker(){const ordered=orderedCandidates();if(!ordered.some(c=>c.row.id===selectedId))selectedId=ordered[0]?.row.id||'';const fragment=document.createDocumentFragment();let group,state='';for(const {row,race} of ordered){if(state!==race.state){state=race.state;group=document.createElement('optgroup');group.label=ContestLabel.stateLabel(state);fragment.append(group);}const option=node('option',null,row.candidate+' · '+raceLabel(race));option.value=row.id;group.append(option);}$('candidate-picker').replaceChildren(fragment);$('candidate-picker').disabled=!ordered.length;$('county-count').textContent='Showing '+ordered.length+' of '+rows().length+' candidacies';syncCandidatePicker();}
  function syncCandidatePicker(){const candidates=orderedCandidates(),index=candidates.findIndex(c=>c.row.id===selectedId);$('candidate-picker').value=selectedId;$('previous-candidate').disabled=index<=0;$('next-candidate').disabled=index<0||index>=candidates.length-1;}
  function workspaceView(value){document.querySelector('.workbench').dataset.mobileView=value;for(const tab of document.querySelectorAll('[data-workspace-view]'))tab.setAttribute('aria-selected',String(tab.dataset.workspaceView===value));requestAnimationFrame(()=>{editor?.layout();stateEditor?.layout();});}
  function selectCandidate(id,fromBrowse=false){selectedId=id;$('results-panel').scrollTop=0;syncCandidatePicker();renderRaces();inspect();validate();if(fromBrowse){workspaceView('results');document.querySelector('.workbench').scrollIntoView({behavior:'smooth',block:'start'});}}
  function renderRaces(){if(!run)return;const oldFocus=document.activeElement?.dataset?.candidateId;const fragment=document.createDocumentFragment(),filter=$('state').value,q=$('search').value.trim().toLowerCase();let visible=0,lastState='',group;
    const byRace=new Map();for(const row of rows()){if(!byRace.has(row.position_id))byRace.set(row.position_id,[]);byRace.get(row.position_id).push(row);}
    for(const race of C.sortRaces(races(),ContestLabel.stateLabel)){if(!matchesCounty(race)||(filter&&race.state!==filter))continue;const label=raceLabel(race),rows=(byRace.get(race.id)||[]).filter(r=>!q||(`${r.candidate} ${label} ${(race.counties||[]).join(' ')} ${ContestLabel.stateLabel(race.state)}`).toLowerCase().includes(q));if(!rows.length)continue;
      if(lastState!==race.state){lastState=race.state;group=node('section','state-group');group.dataset.state=race.state;group.append(node('h3',null,ContestLabel.stateLabel(race.state)));fragment.append(group);}
      const raceEl=node('section','race');raceEl.dataset.race=race.id;raceEl.append(node('h4',null,label));
      for(const row of rows){visible++;const card=node('button','candidate');card.type='button';card.dataset.candidateId=row.id;card.setAttribute('aria-pressed',String(row.id===selectedId));const head=node('div','candidate-head');head.append(node('span','candidate-name',row.candidate),node('span','party',row.party||'Nonpartisan'));card.append(head);const recommendations=C.currentCair(row);card.append(node('p','candidate-cair-mini','CAIR Action: '+(recommendations.length?recommendations.map(C.cairLabel).join(' · '):'No current recommendation recorded')));
        if(row.status==='complete'&&row.response){const answers=node('div','answer-list');for(const [name,answer]of Object.entries(row.response.answers)){const a=node('div');a.append(node('span','answer-name',name),node('span','answer-value',C.answerValue(answer,row.request.questions[name])));a.append(node('span','answer-confidence',answer.type==='noul'?'Probability of yes / true':'Confidence '+C.percent(answer.confidence)));answers.append(a);}const grade=C.derivedGrade(row,gradeMapping);if(grade)answers.append(node('div','derived-grade-mini','pro_palestine_score_grade: '+grade+' · derived'));card.append(answers);}else card.append(node('p','candidate-status',row.status==='preview'?(latestMode()?'Not evaluated yet':'Not evaluated in this saved run'):row.status==='error'?row.error:row.status==='queued'?'Waiting to run':row.status==='cancelled'?'Not run · stopped':row.status));
        card.addEventListener('click',()=>selectCandidate(row.id,true));raceEl.append(card);
      }group.append(raceEl);
    }
    if(!visible)fragment.append(node('p','help','No candidates match these filters.'));
    $('races').replaceChildren(fragment);$('visible-count').textContent=visible+' of '+orderedCandidates().length+' candidates';
    if(oldFocus)for(const el of $('races').querySelectorAll('[data-candidate-id]'))if(el.dataset.candidateId===oldFocus)el.focus({preventScroll:true});
  }
  function inspect(){const row=run&&rows().find(r=>r.id===selectedId);$('copy').disabled=!row;if(!row){$('inspector-title').textContent='No candidates in this county view';$('selected-answers').replaceChildren();$('candidate-cair').replaceChildren();$('candidate-score-grade').replaceChildren();$('candidate-cair-flag').hidden=true;$('candidate-site').removeAttribute('href');$('result-meta').textContent='';$('evaluation-source').textContent='';$('result-notice').hidden=true;$('stale').hidden=true;$('state-json').textContent='No candidate selected.';lastStateText='No candidate selected.';stateEditor?.setValue(lastStateText);$('inspector-meta').textContent='';$('request-ref').textContent='';return;}const race=races().find(r=>r.id===row.position_id),preview=row.status==='preview';$('candidate-site').href=C.candidateSiteUrl(row);$('evaluation-source').textContent=row.evaluation?'Saved '+formatTime(row.evaluation.finished_at||row.evaluation.created_at):'';if(latestMode()){$('stale').hidden=!row.evaluation||(row.evaluation.dataset_sha256===boot.snapshot.dataset_sha256&&row.evaluation.state_version===boot.snapshot.state_version);$('stale').textContent='This candidate’s saved evaluation uses earlier evidence or an older input format. Rerun to use current data; the saved input below remains exact.';}renderCandidateCair(row);renderDerivedGrade(row);renderAnswers(row,race);resultNotice();$('inspector-title').textContent=row.candidate;$('inspector-meta').textContent=`${raceLabel(race)} · ${row.party||'Nonpartisan'} · ${preview?'Current input preview · not evaluated':'Exact '+(row.status==='queued'?'submitted':'stored')+' input'}`;
    let request=row.request;if(preview){let questions=null;try{questions=C.parseQuestions(text());}catch{}request={model:run.model,state:row.state,questions};}
    const value=view==='state'?request.state:view==='request'?request:row.response||{status:row.status,...(row.error?{error:row.error}:{})};const serialized=JSON.stringify(value,null,2);$('state-json').textContent=serialized;if(stateEditor&&serialized!==lastStateText)stateEditor.setValue(serialized);lastStateText=serialized;
    $('request-ref').textContent=preview?'Preview only · Run selected candidate reloads current data and submits the editor questions.':'Request SHA-256 · '+row.request_sha256;for(const tab of document.querySelectorAll('[data-view]'))tab.setAttribute('aria-selected',String(tab.dataset.view===view));$('inspect-panel').setAttribute('aria-labelledby','tab-'+view);
  }
  function status(){const terminal=['complete','error','cancelled','interrupted'].includes(run.status);
    if(latestMode()){
      activeRunId=run.active_run?.id||null;
      $('run-status').textContent='Latest per candidate · '+run.completed+' of '+run.rows.length+' evaluated'+(run.active_run?' · '+(run.status==='cancelling'?'Stopping':'Evaluating')+' '+scopeLabel(run.active_run.scope)+' · '+run.active_run.completed+'/'+run.active_run.total+' processed · '+run.active_run.errors+' errors':'');
    }else{
      const models=[...new Set(run.rows.map(r=>r.response?.model).filter(Boolean))].join(', ')||run.model;
      $('run-status').textContent=`${run.scope==='candidate'?'Single candidate · '+run.rows[0].candidate+' · ':''}${run.id===baselineId?'Stored House run':run.status[0].toUpperCase()+run.status.slice(1)} · ${run.completed} of ${run.rows.length} processed · ${run.errors} errors · ${models} · ${formatTime(run.created_at)}`;
      $('stale').hidden=run.dataset_sha256===boot.snapshot.dataset_sha256&&run.state_version===boot.snapshot.state_version;$('stale').textContent='Earlier dataset or input format. New evaluations use current candidate context; saved inputs remain exact.';
    }
    $('download').disabled=false;validate();return terminal;
  }
  function showRun(value,updateQuestions=true){run=value;$('results-panel').scrollTop=0;if(run.scope==='candidate'||!rows().some(r=>r.id===selectedId))selectedId=run.rows[0]?.id||'';setupCountyFilter();setupStates();setupCandidatePicker();if(updateQuestions)setText(JSON.stringify(run.questions,null,2));renderRaces();renderCairReview();inspect();status();clearTimeout(pollTimer);if(['running','cancelling'].includes(run.status))pollTimer=setTimeout(poll,700);}
  async function poll(){const id=run.id;try{const value=await api(latestMode()?'/api/latest':'/api/runs/'+encodeURIComponent(id)+'?after='+run.revision);if(run.id!==id)return;run=latestMode()?value:C.mergeDelta(run,value);renderRaces();renderCairReview();inspect();if(!status())pollTimer=setTimeout(poll,900);else await history();}catch(e){error(e.message+' The server may still be working; select Latest per candidate to reconnect.');}}
  async function history(){const entries=await api('/api/runs');activeRunId=entries.find(item=>['running','cancelling'].includes(item.status))?.id||null;clearTimeout(historyTimer);historyTimer=null;if(activeRunId&&run?.active_run?.id!==activeRunId&&run?.id!==activeRunId)historyTimer=setTimeout(()=>(latestMode()?refreshLatest():history()).catch(e=>error(e.message)),1200);validate();const selected=$('history').value;$('history').replaceChildren();const latest=node('option',null,'Latest per candidate');latest.value='latest';$('history').append(latest);const base=node('option',null,boot.baseline.label||'Stored House results · Oct 23');base.value=baselineId;$('history').append(base);for(const item of entries){const o=node('option',null,formatTime(item.created_at)+' · '+(item.scope==='candidate'?item.candidate:scopeLabel(item.scope))+' · '+item.status+' · '+item.completed+'/'+item.total+' · '+item.id.slice(-6));o.value=item.id;$('history').append(o);}$('history').value=run?.id||selected||'latest';}
  async function refreshLatest(){const value=await api('/api/latest');showRun(value,false);await history();}
  async function start(candidateId=null,scope='all'){const button=candidateId!==null?$('run-selected'):scope==='bay-area'?$('run-bay-area'):$('run');if(!validate()||button.disabled)return;loading=true;validate();error('');try{const questions=C.parseQuestions(text());boot.snapshot=await api('/api/snapshot');await api('/api/runs',{method:'POST',body:JSON.stringify({questions,...(candidateId!==null?{candidate_id:candidateId}:scope==='bay-area'?{scope}:{})})});updateScope();selectedId=candidateId||selectedId;await refreshLatest();workspaceView('results');await history();}catch(e){error(e.message);}finally{loading=false;validate();}}
  $('run').addEventListener('click',()=>start());$('run-bay-area').addEventListener('click',()=>start(null,'bay-area'));$('run-selected').addEventListener('click',()=>start(selectedId));$('stop').addEventListener('click',async()=>{try{await api('/api/runs/'+encodeURIComponent(activeRunId||run.id)+'/cancel',{method:'POST',body:'{}'});run.status='cancelling';status();}catch(e){error(e.message);}});
  $('questions').addEventListener('input',validate);$('questions').addEventListener('keydown',e=>{if((e.ctrlKey||e.metaKey)&&e.key==='Enter'){e.preventDefault();start(selectedId);}});
  $('format').addEventListener('click',()=>{try{setText(JSON.stringify(C.parseQuestions(text()),null,2));}catch(e){$('question-error').textContent=e.message;$('question-error').hidden=false;}});
  $('reset').addEventListener('click',()=>setText(JSON.stringify(boot.questions,null,2)));
  $('county').addEventListener('change',()=>{$('results-panel').scrollTop=0;setupCandidatePicker();renderRaces();renderCairReview();inspect();validate();});
  $('state').addEventListener('change',renderRaces);$('search').addEventListener('input',renderRaces);
  $('history').addEventListener('change',async()=>{error('');try{const id=$('history').value;showRun(id==='latest'?await api('/api/latest'):id===baselineId?boot.baseline:await api('/api/runs/'+encodeURIComponent(id)),id!=='latest');await history();}catch(e){error(e.message);}});
  for(const tab of document.querySelectorAll('[data-view]')){tab.addEventListener('click',()=>{view=tab.dataset.view;inspect();});tab.addEventListener('keydown',e=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(e.key)){e.preventDefault();const tabs=[...document.querySelectorAll('[data-view]')];let index=tabs.indexOf(tab);index=e.key==='Home'?0:e.key==='End'?tabs.length-1:(index+(e.key==='ArrowRight'?1:-1)+tabs.length)%tabs.length;tabs[index].focus();tabs[index].click();}});}
  $('copy').addEventListener('click',async()=>{try{await navigator.clipboard.writeText(lastStateText);$('copy').textContent='Copied';setTimeout(()=>$('copy').textContent='Copy JSON',1200);}catch{error('Clipboard unavailable. Select and copy from the JSON panel.');}});
  $('download').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(C.withScoreGrades(run,gradeMapping),null,2)+'\n'],{type:'application/json'}));const a=node('a');a.href=url;a.download='jev-'+run.id+'.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
  const comparisonOptions=()=>({gradeKey:comparisonGrade,scoreKey:comparisonScore,mapping:gradeMapping});
  function sourceLink(url,label){try{const value=new URL(url);if(!['https:','http:'].includes(value.protocol))return null;const a=node('a',null,label);a.href=value.href;a.target='_blank';a.rel='noopener noreferrer';return a;}catch{return null;}}
  function appendCair(parent,row){
    const records=row.cair_action;
    parent.append(node('strong',null,'CAIR Action'));
    if(!Array.isArray(records)){parent.append(node('p','help','Recommendation data is unavailable in this server snapshot.'));return;}
    if(!records.length){parent.append(node('p','help','No recommendation recorded in the current dataset.'));return;}
    for(const record of records){const item=node('div','cair-record');item.append(node('span','cair-tier '+record.relation,C.cairLabel(record)));item.append(node('span','help',({general:'General election',primary:'Primary election',unspecified:'Election phase not stated'}[record.phase]||'Election phase not stated')+(record.checked_on?' · checked '+record.checked_on:'')));const source=sourceLink(record.url,'Source ↗');if(source){if(record.quote)source.title=record.quote;item.append(source);}parent.append(item);}
  }

  function renderDerivedGrade(row){
    const panel=$('candidate-score-grade'),grade=C.derivedGrade(row,gradeMapping);panel.replaceChildren();
    panel.append(node('strong',null,'pro_palestine_score_grade'));
    if(!grade){panel.append(node('p','help','No compatible saved 0–5 pro_palestine_score.'));return;}
    panel.append(node('span','derived-grade-value',grade));
    panel.append(node('p','help','Derived from '+String(row.response.answers.pro_palestine_score.score)+' / 5 · Source score confidence: '+C.percent(row.response.answers.pro_palestine_score.confidence)+'. No separate model confidence.'));
    const tune=node('a',null,'Tune grade mapping ↑');tune.href='#grade-mapping';tune.addEventListener('click',()=>{$('grade-mapping').open=true;});panel.append(tune);
  }
  function setupGradeMapping(){
    const controls=$('grade-bounds');controls.replaceChildren();
    for(const [i,upper]of gradeMapping.upper_bounds.entries()){const label=node('label',null,'FEDCB'[i]+' upper bound (inclusive)'),input=node('input');input.id='grade-bound-'+i;input.type='number';input.step='any';input.min='0';input.max='5';input.required=true;input.value=String(upper);label.htmlFor=input.id;label.append(input);controls.append(label);}
  }
  async function applyGradeMapping(mapping){
    try{C.validateMapping(mapping);gradeMapping=await api('/api/score-grade-mapping',{method:'POST',body:JSON.stringify(mapping)});setupGradeMapping();$('grade-mapping-error').hidden=true;$('grade-mapping-status').textContent='Mapping saved locally. All derived grades updated; Jev answers are unchanged.';renderRaces();renderCairReview();inspect();}
    catch(e){$('grade-mapping-error').textContent=e.message;$('grade-mapping-error').hidden=false;}
  }
  $('grade-mapping-form').addEventListener('submit',event=>{event.preventDefault();applyGradeMapping({upper_bounds:Array.from({length:5},(_,i)=>$('grade-bound-'+i).value.trim()===''?null:Number($('grade-bound-'+i).value))});});
  $('reset-grade-mapping').addEventListener('click',()=>applyGradeMapping(boot.default_score_grade_mapping||C.defaultScoreGradeMapping));
  function renderCandidateCair(row){$('candidate-cair').replaceChildren();appendCair($('candidate-cair'),row);const comparison=C.cairComparison(row,comparisonOptions());$('candidate-cair-flag').textContent='Matches CAIR review rule: '+comparison.reasons.join(' or ');$('candidate-cair-flag').hidden=!comparison.flagged;}
  function questionPicker(id,keys,selected){const select=$(id);select.replaceChildren();const none=node('option',null,'Do not compare');none.value='';select.append(none);for(const key of keys){const option=node('option',null,key+(key==='pro_palestine_score_grade'?' (derived)':''));option.value=key;select.append(option);}if(selected&&!keys.includes(selected)){const missing=node('option',null,selected+' — not available in this view');missing.value=selected;select.append(missing);}select.value=selected;}
  function renderCairReview(){
    if(!run)return;
    const available=C.comparisonQuestions(rows());questionPicker('comparison-grade',available.grades,comparisonGrade);questionPicker('comparison-score',available.scores,comparisonScore);
    $('comparison-source').textContent=latestMode()?'Latest saved evaluation per candidate':'Selected saved run · '+formatTime(run.created_at);
    const ordered=orderedCandidates().map(item=>({...item,comparison:C.cairComparison(item.row,comparisonOptions())}));
    const recommended=ordered.filter(item=>item.comparison.positive),comparable=recommended.filter(item=>item.comparison.comparable),flagged=comparable.filter(item=>item.comparison.flagged);
    $('cair-review-count').textContent='('+flagged.length+')';$('cair-review-summary').textContent=flagged.length+' to review';
    $('comparison-coverage').textContent=flagged.length+' match the review rule · '+comparable.length+' of '+recommended.length+' Preferred/Endorsed candidacies have a compatible saved result · '+(recommended.length-comparable.length)+' have no compatible saved result. Only saved A–F grade and 0–5 score questions are compared.';
    const results=document.createDocumentFragment();
    if(!flagged.length)results.append(node('p','empty-result','No saved evaluations in this county view match the selected review rule.'));
    for(const {row,race,comparison} of flagged){
      const card=node('article','comparison-card');card.dataset.candidateId=row.id;
      const heading=node('div','section-head'),select=node('button','comparison-candidate',row.candidate);select.type='button';select.addEventListener('click',()=>selectCandidate(row.id,true));heading.append(select,node('span','help',raceLabel(race)));card.append(heading);
      const recommendation=node('div','comparison-recommendation');appendCair(recommendation,row);card.append(recommendation);
      const metrics=node('div','comparison-metrics');
      for(const [key,metric,type]of [[comparisonGrade,comparison.grade,'grade'],[comparisonScore,comparison.score,'score']]){const cell=node('div');cell.append(node('strong',null,key||'Question not selected'));cell.append(node('p',null,metric?(type==='score'?String(metric.value)+' / 5':metric.value):'No compatible saved answer'));if(metric)cell.append(node('span','help',(metric.derived?'Source score confidence: ':'Confidence: ')+C.percent(metric.confidence)));metrics.append(cell);}card.append(metrics);
      card.append(node('p','help','Review reason: '+comparison.reasons.join(' or ')));
      const footer=node('div','comparison-footer'),open=sourceLink(C.candidateSiteUrl(row),'Election site ↗');footer.append(node('span','help','Saved '+formatTime(row.evaluation?.finished_at||row.evaluation?.created_at||run.created_at)+' · '+(row.response?.model||run.model)));if(open)footer.append(open);card.append(footer);results.append(card);
    }
    $('comparison-results').replaceChildren(results);
  }
  $('review-jump').addEventListener('click',()=>{$('cair-review').open=true;});
  $('comparison-grade').addEventListener('change',()=>{comparisonGrade=$('comparison-grade').value;renderCairReview();inspect();});
  $('comparison-score').addEventListener('change',()=>{comparisonScore=$('comparison-score').value;renderCairReview();inspect();});
  function resultNotice(){if(!run)return;const row=rows().find(r=>r.id===selectedId);let edited=false;try{edited=JSON.stringify(C.parseQuestions(text()))!==JSON.stringify(row?.request?.questions||run.questions);}catch{edited=true;}
    const messages=[];
    if(row?.status==='preview')messages.push(latestMode()?'No saved evaluation yet. Run this candidate with the current questions.':'Not evaluated in this saved run. Choose Latest per candidate to see evaluations from other runs.');
    else if(edited)messages.push('These answers use a different saved prompt from the current editor. Run this candidate to evaluate the edited questions.');
    if(row?.latest_attempt){const attempt=row.latest_attempt;messages.push(attempt.status==='queued'?'A new evaluation is in progress; showing the latest saved answer.':attempt.status==='error'?'The latest attempt failed. Showing the previous successful evaluation. '+(attempt.error||''):'The latest attempt was stopped or interrupted. Showing the previous successful evaluation.');}
    const message=messages.join(' ');$('result-notice').textContent=message;$('result-notice').hidden=!message;
  }
  function jumpToQuestion(name){workspaceView('questions');const source=text(),offset=source.indexOf(JSON.stringify(name));if(offset<0){error('This question is no longer in the edited draft. Restore it or select its saved run to find it.');return;}if(editor){const position=editor.getModel().getPositionAt(Math.max(0,offset));editor.setPosition(position);editor.revealPositionInCenter(position);editor.focus();}else{$('questions').focus();$('questions').setSelectionRange(Math.max(0,offset),Math.max(0,offset)+JSON.stringify(name).length);}}
  function syncExpand(){const details=[...$('selected-answers').querySelectorAll('details')];$('expand-answers').disabled=!details.length;$('expand-answers').textContent=details.length&&details.every(d=>d.open)?'Collapse all':'Expand all';}
  function renderAnswers(row,race){
    $('result-meta').textContent=raceLabel(race)+' · '+(row.party||'Nonpartisan')+' · '+(row.response?.model||run.model);
    $('answer-model').textContent=row.response?.model||'Answer';
    const signature=JSON.stringify([row.evaluation?.run_id||run.id,row.id,row.status,row.response,row.request_sha256]);if(signature===answerSignature)return;answerSignature=signature;
    const fragment=document.createDocumentFragment();
    if(row.status!=='complete'||!row.response){const messages={preview:latestMode()?'No saved evaluation for this candidate yet.':'No result for this candidate in this saved run.',queued:'Running this prompt… Results will appear here.',cancelled:'Not evaluated · run stopped.',interrupted:'Evaluation interrupted. Run this candidate again.',error:row.error};fragment.append(node('p','empty-result',messages[row.status]||'No answers returned.'));}
    else for(const name of Object.keys(row.request.questions)){
      const answer=row.response.answers[name];
      const question=row.request.questions[name],probabilities=C.probabilityRows(answer,question),id=(row.evaluation?.run_id||run.id)+':'+row.id+':'+name;
      const detail=node('details','question-answer');detail.dataset.question=name;detail.open=expandedAnswers.has(id);
      const summary=node('summary','answer-summary'),questionCell=node('div','answer-question');questionCell.append(node('div','question-key',name));if(question.instructions)questionCell.append(node('p','question-instructions',question.instructions));summary.append(questionCell);
      const value=node('div','answer-result');value.append(node('div','result-value',C.answerValue(answer,question)));
      if(answer.type==='choice'&&probabilities.length){const preview=node('div','choice-preview'),top=probabilities.slice(0,3),selected=probabilities.find(p=>p.selected);if(selected&&!top.includes(selected))top.push(selected);for(const probability of top){const line=node('div','choice-option'+(probability.selected?' is-selected':''));line.append(node('span',null,probability.key+(probability.selected?' ✓':'')));const amount=node('span',null,C.percent(probability.probability)),bar=node('span','probability-mini'),fill=node('span');fill.style.width=(probability.probability*100)+'%';bar.append(fill);amount.append(bar);line.append(amount);preview.append(line);}value.append(preview);}
      value.append(node('div','result-confidence',answer.type==='noul'?'Probability of yes / true':'Confidence: '+C.percent(answer.confidence)));summary.append(value);
      const type=node('div','result-type');type.append(node('span','type-badge',{score:'Score',choice:'Choice',noul:'Yes / no'}[answer.type]));if(answer.type!=='noul')type.append(node('span','type-description',answer.type==='score'?question.criteria.length+' levels · 0–'+(question.criteria.length-1):Object.keys(question.criteria).length+' options'));summary.append(type);detail.append(summary);
      const body=node('div','answer-detail'),find=node('button','find-question','Find in questions ↗');find.type='button';find.addEventListener('click',()=>jumpToQuestion(name));body.append(find);
      if(probabilities.length){body.append(node('p','help','Returned probabilities · separate from confidence'));for(const probability of probabilities){const line=node('div','probability-row'),label=node('div','probability-label');label.append(node('b',null,probability.key+(probability.selected?' ✓':'')),document.createTextNode(String(probability.label)));const amount=node('div','probability-value',C.percent(probability.probability)),bar=node('div','probability-bar'),fill=node('span');fill.style.width=(probability.probability*100)+'%';bar.append(fill);amount.append(bar);line.append(label,amount);body.append(line);}}
      else if(answer.type==='noul')body.append(node('p','help','Jev returns a probability of true for this question type, with no separate confidence.'));
      else for(const [key,label]of Object.entries(question.criteria||{}))body.append(node('p','help',key+' · '+label));
      detail.append(body);detail.addEventListener('toggle',()=>{if(detail.open)expandedAnswers.add(id);else expandedAnswers.delete(id);syncExpand();});fragment.append(detail);
    }
    $('selected-answers').replaceChildren(fragment);syncExpand();
  }
  function ensureStateEditor(){if(!monacoReady||stateEditor||!$('input-details').open)return;$('monaco-state').hidden=false;stateEditor=monaco.editor.create($('monaco-state'),{language:'json',theme:'vs',automaticLayout:true,minimap:{enabled:false},wordWrap:'on',scrollBeyondLastLine:false,fontSize:11,readOnly:true,domReadOnly:true,value:lastStateText,ariaLabel:'Exact candidate JSON'});$('state-json').hidden=true;}
  $('input-details').addEventListener('toggle',()=>{ensureStateEditor();stateEditor?.layout();});
  $('candidate-picker').addEventListener('change',()=>selectCandidate($('candidate-picker').value));
  for(const [id,direction] of [['previous-candidate',-1],['next-candidate',1]])$(id).addEventListener('click',()=>{const ordered=orderedCandidates(),index=ordered.findIndex(c=>c.row.id===selectedId);if(ordered[index+direction])selectCandidate(ordered[index+direction].row.id);});
  for(const tab of document.querySelectorAll('[data-workspace-view]')){tab.addEventListener('click',()=>workspaceView(tab.dataset.workspaceView));tab.addEventListener('keydown',event=>{if(['ArrowLeft','ArrowRight','Home','End'].includes(event.key)){event.preventDefault();const target=event.key==='Home'?'questions':event.key==='End'?'results':tab.dataset.workspaceView==='questions'?'results':'questions';workspaceView(target);$('workspace-tab-'+target).focus();}});}
  $('expand-answers').addEventListener('click',()=>{const details=[...$('selected-answers').querySelectorAll('details')],open=details.some(d=>!d.open);for(const detail of details)detail.open=open;syncExpand();});
  function loadMonaco(){
    const base='https://cdn.jsdelivr.net/npm/monaco-editor@0.52.2/min/';
    window.MonacoEnvironment={getWorkerUrl(){const source=`self.MonacoEnvironment={baseUrl:'${base}'};importScripts('${base}vs/base/worker/workerMain.js');`;return URL.createObjectURL(new Blob([source],{type:'text/javascript'}));}};
    const script=document.createElement('script');script.src=base+'vs/loader.js';script.onload=()=>{if(typeof window.require!=='function')return;window.require.config({paths:{vs:base+'vs'}});window.require(['vs/editor/editor.main'],()=>{
      const settings={language:'json',theme:'vs',automaticLayout:true,minimap:{enabled:false},wordWrap:'on',scrollBeyondLastLine:false,fontSize:12,tabSize:2,formatOnPaste:true,accessibilitySupport:'on'};
      $('monaco-questions').hidden=false;editor=monaco.editor.create($('monaco-questions'),{...settings,value:$('questions').value,ariaLabel:'Jev questions JSON'});$('questions').hidden=true;editor.onDidChangeModelContent(validate);editor.addCommand(monaco.KeyMod.CtrlCmd|monaco.KeyCode.Enter,()=>start(selectedId));
      monacoReady=true;ensureStateEditor();
    },()=>{});};script.onerror=()=>{};document.head.append(script);
  }
  (async()=>{try{boot=await api('/api/bootstrap');gradeMapping=C.validateMapping(boot.score_grade_mapping||C.defaultScoreGradeMapping);setupGradeMapping();baselineId=boot.baseline.id;updateScope();$('connection').textContent=boot.key_configured?'Local server ready · Ctrl/Cmd + Enter runs selected':'Stored results ready · start the server with a Jev key to run';showRun(boot.latest||boot.baseline);await history();loadMonaco();}catch(e){error(e.message+' Start scripts/serve_jev_playground.py and open its local URL.');}})();
})();
