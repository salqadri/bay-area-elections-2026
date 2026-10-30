/* Display-only guide. Addresses and results are never persisted or put in URLs. */
'use strict';
(() => {
  const $=id=>document.getElementById(id);
  const state={data:null,mode:location.pathname.endsWith('/candidates.html')?'all':'ballot',estimate:null,request:0,controller:null,matches:[],limit:24,county:'',office:'',search:''};
  const order=globalThis.TallBallotOrder;
  const matcher=globalThis.ElectionAddressMatcher;
  const service=globalThis.ElectionAddressService;
  let manualOnly=true;
  const node=(tag,className,text)=>{const e=document.createElement(tag);if(className)e.className=className;if(text!==undefined)e.textContent=String(text);return e;};
  const slug=text=>'section-'+order.groups.indexOf(text);
  const link=(url,text)=>{const a=node('a',null,text);a.href=url;a.target='_blank';a.rel='noopener noreferrer';return a;};
  const option=(value,label)=>{const e=node('option',null,label);e.value=value;return e;};
  function error(message){$('lookup-error').textContent=message;$('lookup-error').hidden=false;}
  function setBusy(busy){$('find-ballot').disabled=busy;$('address-form').setAttribute('aria-busy',String(busy));$('lookup-status').textContent=busy?'Finding your address and voting districts…':'';}
  function party(candidate,position){return candidate.party?(state.data.codes.party[candidate.party]||candidate.party):(position.partisan?'Party not recorded':'Nonpartisan');}
  function renderCandidate(candidate,position){
    const li=node('li','candidate');
    const head=node('div','candidate-head'),identity=node('div');
    identity.append(node('h4',null,candidate.name));
    const meta=node('p','candidate-meta');meta.append(node('span',null,party(candidate,position)));
    if(candidate.incumbent===true)meta.append(node('span',null,'Incumbent'));
    if(candidate.write_in===true)meta.append(node('span',null,'Qualified write-in'));
    identity.append(meta);head.append(identity);
    if(position.recommendation.candidate===candidate.name)head.append(node('span','candidate-pick','✓ Recommended'));
    li.append(head);
    li.append(node('p',candidate.blurb?'blurb':'missing-blurb',candidate.blurb||'No published candidate summary is available.'));
    return li;
  }
  function renderRace(race,{showCandidates=false}={}){
    const p=race.position,rec=p.recommendation;
    const card=node('article','race-card');card.dataset.contestId=p.id;
    const main=node('div','race-main'),top=node('div','race-top');
    top.append(node('span','race-district',p.district_or_seat||p.office_category));
    const voteInstruction=p.election_type==='retention'?'Yes / No retention vote':Number.isInteger(p.seats)?'Vote for up to '+p.seats:'';
    top.append(node('span','race-seats',voteInstruction));
    main.append(top,node('h3',null,p.office),node('p','jurisdiction',p.jurisdiction+(p.term?' · '+p.term:'')));
    if(race.confidence&&race.confidence!=='expected')main.append(node('p','confidence-note',race.reason||'Confirm your district on your official ballot.'));
    const pick=node('div','pick-line'+(rec.candidate?'':' no-pick'));
    pick.append(node('span','pick-icon'+(rec.candidate?'':' none'),rec.candidate?'✓':'—'));
    const pickText=node('div','pick-text');pickText.append(node('span','pick-label',rec.candidate?'RECOMMENDED':'THIS RACE'),node('strong','pick-name',rec.candidate||'No recommendation'));
    pick.append(pickText);main.append(pick);
    const reason=node('p','recommendation-reason',rec.reason);
    reason.id='why-'+p.id;
    if(rec.reason.length>400){
      reason.classList.add('clamped');
      const toggle=node('button','read-more','Read full rationale');toggle.type='button';toggle.setAttribute('aria-expanded','false');toggle.setAttribute('aria-controls',reason.id);
      toggle.addEventListener('click',()=>{const expanded=toggle.getAttribute('aria-expanded')!=='true';toggle.setAttribute('aria-expanded',String(expanded));reason.classList.toggle('clamped',!expanded);toggle.textContent=expanded?'Show less':'Read full rationale';});
      main.append(reason,toggle);
    }else main.append(reason);
    card.append(main);
    const details=node('details','race-candidates');details.open=showCandidates;
    const candidates=p.candidates||[];
    details.append(node('summary',null,candidates.length?'Compare '+candidates.length+(candidates.length===1?' candidate':' candidates'):'Candidate list unavailable'));
    const ul=node('ul','candidate-list');
    for(const candidate of candidates)ul.append(renderCandidate(candidate,p));
    if(!candidates.length)ul.append(node('li','candidate','The published roster has not been verified.'));
    details.append(ul);card.append(details);
    return card;
  }
  function groupRaces(races){
    const groups=new Map();for(const race of [...races].sort((a,b)=>order.compare(a.position,b.position))){const name=order.group(race.position);if(!groups.has(name))groups.set(name,[]);groups.get(name).push(race);}return groups;
  }
  function addGroups(parent,races,{possible=false}={}){
    for(const [name,values]of groupRaces(races)){
      const section=node('section','race-group');section.id=slug(name)+(possible?'-possible':'');
      const heading=node('div','group-heading');heading.append(node('h2',null,name),node('span',null,values.length+(values.length===1?' race':' races')));section.append(heading);
      for(const race of values)section.append(renderRace(race,{showCandidates:state.mode==='all'}));
      parent.append(section);
    }
  }
  function allRaces(){
    return state.data.positions.filter(p=>(!state.county||p.counties.includes(state.county))&&(!state.office||order.group(p)===state.office)&&(!state.search||[p.office,p.jurisdiction,p.district_or_seat,...(p.candidates||[]).map(c=>c.name)].join(' ').toLocaleLowerCase().includes(state.search))).sort(order.compare).map(position=>({position}));
  }
  function renderNavigation(races){
    $('section-nav').replaceChildren();
    for(const[name,values]of groupRaces(races)){
      const a=node('a',null,name);a.href='#'+slug(name);a.append(node('span',null,values.length));
      a.addEventListener('click',event=>{
        event.preventDefault();
        if(state.mode==='all'){
          const index=races.findIndex(r=>order.group(r.position)===name);state.limit=Math.max(state.limit,index+24);renderRaces();
        }
        let target=$(slug(name));
        if(!target){target=$(slug(name)+'-possible');if(target){const details=target.closest('details');if(details)details.open=true;}}
        target?.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
      });
      $('section-nav').append(a);
    }
  }
  function renderRaces(){
    const list=$('race-list');list.replaceChildren();
    let races=state.mode==='all'?allRaces():(state.estimate?.races||[]);
    $('empty-state').hidden=races.length>0;
    $('load-more').hidden=true;
    if(state.mode==='all'){
      addGroups(list,races.slice(0,state.limit));
      const shown=Math.min(state.limit,races.length);
      $('result-count').textContent=races.length+' races · '+races.reduce((n,r)=>n+(r.position.candidates||[]).length,0)+' candidates'+(shown<races.length?' · Showing '+shown+' races':'');
      $('load-more').hidden=shown>=races.length;
    }else{
      const expected=races.filter(r=>r.confidence==='expected'),possible=races.filter(r=>r.confidence!=='expected');
      addGroups(list,expected);
      if(possible.length){
        const details=node('details','possible-section');details.id='possible-races';details.open=!!state.estimate.summary?.manual||!expected.length;
        const summary=node('summary'),text=node('div');text.append(node('strong',null,possible.length+' additional '+(possible.length===1?'race':'races')+' to confirm'),node('small',null,'These districts could not be resolved. Only some may appear on your ballot.'));summary.append(text);details.append(summary);
        const body=node('div','possible-body');body.append(node('p','possible-intro','Check your county’s official ballot before using these recommendations. Alternative districts are kept here so uncertain races aren’t silently left out.'));addGroups(body,possible,{possible:true});details.append(body);list.append(details);
      }
      $('result-count').textContent=state.estimate.summary?.manual?races.length+' county-wide possibilities · Use an address to narrow your guide':expected.length+' expected '+(expected.length===1?'race':'races')+(possible.length?' · '+possible.length+' additional to confirm':'');
    }
    renderNavigation(races);
  }
  function officialLinks(counties){
    $('official-links').replaceChildren();
    for(const county of counties){const url=state.data.county_election_urls[county];if(url)$('official-links').append(link(url,county+' official ballot ↗'));}
  }
  function showEstimate(estimate){
    state.estimate=estimate;
    document.body.classList.add('lookup-view');$('results').hidden=false;$('intro-strip').hidden=true;
    $('results-title').textContent=estimate.summary?.manual?'Explore your county':estimate.summary?.matchedAddresses?.length>1?'Possible races across matches':'Your ballot guide';
    $('results-eyebrow').textContent=estimate.summary?.manual?'COUNTY BROWSING':'YOUR NOVEMBER GUIDE';
    $('results-description').textContent=estimate.summary?.manual?'A broad view of confirmed contests in this county. Many will not apply to your address.':'An estimate of the elected offices at your address, with the published recommendations.';
    $('result-context').replaceChildren();
    const s=estimate.summary||{};
    for(const text of [...(s.counties||[]).map(c=>c+' County'),...(s.places||[]),...Object.entries(s.districts||{}).flatMap(([k,values])=>values.map(v=>k+'-'+v))])$('result-context').append(node('span','context-pill',text));
    officialLinks(s.counties||[]);
    $('empty-message').textContent=estimate.status==='outside_scope'?'This address is outside the five covered Bay Area counties. This does not mean there are no races at your address. Check your county’s election website.':estimate.status==='needs_county'?'We couldn’t identify a covered California county. Try a complete street address with city, state and ZIP, or browse by county.':'No confirmed contests were matched in this inventory. Check your county’s official ballot for complete election information.';
    $('scope-note').textContent='An independent guide to elected offices. Ballot measures are not included. Compare this estimate with your county’s official ballot.';
    $('matching-warnings').replaceChildren();
    $('matching-notes').hidden=!estimate.warnings?.length;
    for(const warning of estimate.warnings||[])$('matching-warnings').append(node('li',null,warning));
    renderRaces();$('results-title').focus({preventScroll:true});$('results').scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});
  }
  async function lookup(address){
    if(!state.data)return;
    if(!address.trim()){error('Enter a complete street address, city and ZIP code.');$('address').focus();return;}
    const request=++state.request;state.controller?.abort();state.controller=new AbortController();
    $('lookup-error').hidden=true;$('address-matches').hidden=true;setBusy(true);
    // Clear previous output immediately; it must not look like the new address's ballot.
    state.estimate=null;$('results').hidden=true;
    try{
      const response=await service.lookup(address,{signal:state.controller.signal});
      if(request!==state.request)return;
      if(!response.matches.length){error('We couldn’t match that address. Check the street, city and ZIP, or browse by county.');return;}
      state.matches=response.matches.map(match=>matcher.estimateBallot(state.data,matcher.geographyFromMatch(match)));
      if(state.matches.length>1){
        const select=$('address-match');select.replaceChildren(option('all','Show possibilities across all matches'));
        response.matches.forEach((match,i)=>select.append(option(String(i),match.matchedAddress)));
        $('address-matches').hidden=false;
      }
      showEstimate(matcher.combineEstimates(state.data,state.matches));
    }catch(e){if(e.name!=='AbortError'&&request===state.request)error(e.message||'Address lookup is unavailable. Try again or browse by county.');}
    finally{if(request===state.request)setBusy(false);}
  }
  function useManual(){manualOnly=true;$('google-address').hidden=true;$('manual-fields').hidden=false;$('use-manual').hidden=true;$('address').focus();}
  async function init(){
    try{
      const response=await fetch('./guide.json',{cache:'no-cache'});if(!response.ok)throw new Error('Guide unavailable');
      const data=await response.json();if(data.format!=='tall-voter-guide/v1')throw new Error('Guide format unsupported');state.data=data;
    }catch(e){error('The guide couldn’t load. Please refresh or try again shortly.');$('find-ballot').disabled=true;return;}
    const counties=state.data.election.counties_in_scope.map(c=>c.name);
    for(const county of counties){$('browse-county').append(option(county,county));$('filter-county').append(option(county,county));}
    for(const group of order.groups)if(state.data.positions.some(p=>order.group(p)===group))$('filter-office').append(option(group,group));
    $('publication-note').textContent='November 3, 2026 · Recommendations dated '+new Date(state.data.recommendations_date+'T12:00:00').toLocaleDateString('en-US',{month:'short',day:'numeric',year:'numeric'});
    if(state.mode==='all'){
      document.body.classList.add('all-view');$('results').hidden=false;$('all-filters').hidden=false;$('change-address').hidden=true;
      $('ballot-tab').removeAttribute('aria-current');$('candidates-tab').setAttribute('aria-current','page');
      $('results-eyebrow').textContent='THE WHOLE PICTURE';$('results-title').textContent='All candidates.';
      $('results-description').textContent='Explore the confirmed races across our five Bay Area counties. Filter by county, office or candidate name.';
      document.title='All Candidates · The TALL Voter Guide';officialLinks(counties);renderRaces();
    }else if(globalThis.TALL_CONFIG?.googleMapsApiKey){
      $('provider-note').textContent='Google suggests addresses; Census finds districts. We don’t save your address.';
      try{
        await globalThis.TallGoogleAutocomplete.attach({key:TALL_CONFIG.googleMapsApiKey,container:$('google-address'),onSelect:address=>{$('address').value=address;lookup(address);},onError:e=>{error(e.message);useManual();}});
        manualOnly=false;$('google-address').hidden=false;$('manual-fields').hidden=true;$('use-manual').hidden=false;
      }catch(e){error('Address suggestions are unavailable. You can still enter your address manually.');}
    }
  }
  $('address-form').addEventListener('submit',event=>{event.preventDefault();if(manualOnly)lookup($('address').value);});
  $('use-manual').addEventListener('click',useManual);
  $('address-match').addEventListener('change',event=>{showEstimate(event.target.value==='all'?matcher.combineEstimates(state.data,state.matches):state.matches[Number(event.target.value)]);});
  $('browse-counties').addEventListener('click',()=>{$('county-picker').hidden=!$('county-picker').hidden;if(!$('county-picker').hidden)$('browse-county').focus();});
  $('browse-county-go').addEventListener('click',()=>{
    const county=$('browse-county').value;if(!county){$('browse-county').focus();return;}
    state.request++;state.controller?.abort();setBusy(false);$('lookup-error').hidden=true;$('address-matches').hidden=true;
    showEstimate(matcher.estimateBallot(state.data,matcher.manualCounty(county)));$('county-picker').hidden=true;
  });
  $('change-address').addEventListener('click',()=>{document.body.classList.remove('lookup-view');$('hero').scrollIntoView();if(manualOnly)$('address').focus();else $('google-address').querySelector('gmp-place-autocomplete')?.focus();});
  for(const[id,key]of[['filter-county','county'],['filter-office','office'],['filter-search','search']])$(id).addEventListener(id==='filter-search'?'input':'change',event=>{state[key]=event.target.value.toLocaleLowerCase().trim();if(key!=='search')state[key]=event.target.value;state.limit=24;renderRaces();});
  $('load-more').addEventListener('click',()=>{const old=state.limit;state.limit+=24;renderRaces();const cards=document.querySelectorAll('.race-card');const card=cards[old];if(card){card.tabIndex=-1;card.focus({preventScroll:true});}});
  let priorLimit;
  addEventListener('beforeprint',()=>{priorLimit=state.limit;if(state.mode==='all'){state.limit=Infinity;renderRaces();}});
  addEventListener('afterprint',()=>{if(priorLimit!==undefined){state.limit=priorLimit;if(state.mode==='all')renderRaces();}});
  $('print-guide').addEventListener('click',()=>window.print());
  document.querySelectorAll('[data-open-dialog]').forEach(button=>button.addEventListener('click',()=>$(button.dataset.openDialog).showModal()));
  document.querySelectorAll('[data-close-dialog]').forEach(button=>button.addEventListener('click',()=>button.closest('dialog').close()));
  document.querySelectorAll('dialog').forEach(dialog=>dialog.addEventListener('click',e=>{if(e.target===dialog){const box=dialog.getBoundingClientRect();if(e.clientX<box.left||e.clientX>box.right||e.clientY<box.top||e.clientY>box.bottom)dialog.close();}}));
  init();
})();
