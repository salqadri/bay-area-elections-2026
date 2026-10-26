/* Pure presentation helpers. No grade acceptance rules or confidence cutoffs. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.JevPlaygroundCore=api;})(typeof globalThis==='object'?globalThis:this,()=>{
  const percent=n=>typeof n==='number'&&Number.isFinite(n)?new Intl.NumberFormat('en-US',{style:'percent',maximumFractionDigits:1}).format(n):'Not returned';
  const defaultScoreGradeMapping={upper_bounds:Array.from({length:5},(_,i)=>(i+1)*5/6)};
  function validateMapping(mapping){
    const b=mapping?.upper_bounds;
    if(!mapping||Object.keys(mapping).length!==1||!Array.isArray(b)||b.length!==5||b.some((n,i)=>typeof n!=='number'||!Number.isFinite(n)||n<=(i?b[i-1]:0)||n>=5))throw new Error('Grade bounds must be five finite, strictly increasing numbers between 0 and 5.');
    return {upper_bounds:[...b]};
  }
  function scoreGrade(score,mapping=defaultScoreGradeMapping){const b=validateMapping(mapping).upper_bounds;if(typeof score!=='number'||!Number.isFinite(score)||score<0||score>5)return null;return 'FEDCBA'[[...b,5].findIndex(upper=>score<=upper)];}
  function derivedGrade(row,mapping=defaultScoreGradeMapping){const q=row.request?.questions?.pro_palestine_score,a=row.response?.answers?.pro_palestine_score;return row.status==='complete'&&q?.type==='score'&&Array.isArray(q.criteria)&&q.criteria.length===6&&a?.type==='score'?scoreGrade(a.score,mapping):null;}
  function withScoreGrades(run,mapping){return {...run,score_grade_mapping:validateMapping(mapping),rows:run.rows.map(row=>({...row,pro_palestine_score_grade:derivedGrade(row,mapping)}))};}
  function answerValue(answer,question){
    if(!answer)return 'Not run';
    if(answer.type==='choice')return String(answer.choice);
    if(answer.type==='score')return Number(answer.score).toFixed(2)+' / '+Math.max(0,(question?.criteria?.length||1)-1);
    if(answer.type==='noul')return percent(answer.noul)+' true';
    return JSON.stringify(answer);
  }
  function probabilityRows(answer,question){
    return Object.entries(answer.probabilities||{}).map(([key,probability])=>({key,probability,
      label:answer.type==='score'?(answer.legend?.[key]??question?.criteria?.[Number(key)]??key):(question?.criteria?.[key]??key),
      selected:answer.type==='choice'&&String(answer.choice)===key
    })).sort((a,b)=>b.probability-a.probability||a.key.localeCompare(b.key,'en-US',{numeric:true}));
  }
  const isHouse=r=>r.office_category==='U.S. House'||/^CD-\d+$/.test(r.district_or_seat||'');
  function raceLabel(r,districtLabel=r=>r.district_or_seat||''){
    if(isHouse(r))return districtLabel(r);
    return [...new Set([r.jurisdiction,r.office,districtLabel(r)].filter(Boolean))].join(' · ');
  }
  function sortRaces(races,label=code=>code){const compare=(a,b)=>String(a||'').localeCompare(String(b||''),'en-US',{numeric:true});return [...races].sort((a,b)=>label(a.state).localeCompare(label(b.state),'en-US')||Number(isHouse(b))-Number(isHouse(a))||(!isHouse(a)&&(compare(a.jurisdiction,b.jurisdiction)||compare(a.office,b.office)))||compare(a.district_or_seat,b.district_or_seat)||a.id.localeCompare(b.id));}
  function mergeDelta(run,delta){
    if(run.id!==delta.id)throw new Error('Run identity mismatch');
    const changes=new Map(delta.changes.map(row=>[row.id,row]));
    return {...run,...Object.fromEntries(Object.entries(delta).filter(([key])=>key!=='changes')),rows:run.rows.map(row=>changes.has(row.id)?{...row,...changes.get(row.id),request:row.request}:row)};
  }
  function catalogRows(snapshot,run){
    const rows=new Map(snapshot.candidates.map(c=>[c.id,{...c,status:'preview'}]));
    for(const row of run.rows)rows.set(row.id,{...row,cair_action:rows.get(row.id)?.cair_action??[]});
    return [...rows.values()];
  }
  function catalogRaces(snapshot,run){const races=new Map(snapshot.races.map(r=>[r.id,r]));for(const race of run.races)races.set(race.id,{...races.get(race.id),...race});return [...races.values()];}
  function candidateSiteUrl(row){const params=new URLSearchParams({id:row.position_id,status:'all',q:row.candidate,tab:'candidates'});return 'https://salqadri.github.io/bay-area-elections-2026/#'+params;}
  function countyMatches(race,county,counties){
    if(!county||county==='all')return true;
    return (race?.counties||[]).some(value=>county==='bay-area'?counties.includes(value):value===county);
  }
  function currentCair(row){return (row.cair_action||[]).filter(r=>r.historical!==true&&(!r.phase||['general','unspecified'].includes(r.phase)));}
  function cairLabel(record){return (record.shared&&record.relation==='endorsed'?'Jointly endorsed':{endorsed:'Endorsed',preferred:'Preferred',opposed:'Opposed'}[record.relation]||record.relation)+(record.historical?' · historical':'')+(record.phase==='primary'?' · primary':'');}
  function cairComparison(row,{gradeKey='gaza_grade',scoreKey='pro_palestine_score',mapping=defaultScoreGradeMapping}={}){
    const recommendations=currentCair(row),positive=recommendations.some(r=>['endorsed','preferred'].includes(r.relation));
    const questions=row.request?.questions||{},answers=row.status==='complete'?row.response?.answers||{}:{};
    const g=answers[gradeKey],gq=questions[gradeKey],s=answers[scoreKey],sq=questions[scoreKey];
    const letter=g?.type==='choice'&&gq?.type==='choice'?String(g.choice).trim().toUpperCase():'';
    const derived=gradeKey==='pro_palestine_score_grade'?derivedGrade(row,mapping):null;
    const grade=derived?{value:derived,confidence:answers.pro_palestine_score.confidence,derived:true}:/^[A-F]$/.test(letter)?{value:letter,confidence:g.confidence}:null;
    const score=s?.type==='score'&&sq?.type==='score'&&sq.criteria?.length===6&&typeof s.score==='number'&&Number.isFinite(s.score)&&s.score>=0&&s.score<=5?{value:s.score,confidence:s.confidence}:null;
    const reasons=[];if(positive&&grade&&'CDEF'.includes(grade.value))reasons.push(gradeKey+' = '+grade.value);
    if(positive&&score&&score.value<=2.5)reasons.push(scoreKey+' = '+String(score.value)+' / 5');
    return {recommendations,positive,grade,score,comparable:!!(grade||score),flagged:reasons.length>0,reasons};
  }
  function comparisonQuestions(rows){
    const grades=new Set(),scores=new Set();
    for(const row of rows)for(const [key,q]of Object.entries(row.request?.questions||{})){
      if(q.type==='choice'&&Object.keys(q.criteria||{}).length&&Object.keys(q.criteria).every(k=>/^[A-F]$/i.test(k)))grades.add(key);
      if(q.type==='score'&&q.criteria?.length===6)scores.add(key);
      if(key==='pro_palestine_score'&&q.type==='score'&&q.criteria?.length===6)grades.add('pro_palestine_score_grade');
    }
    return {grades:[...grades].sort(),scores:[...scores].sort()};
  }
  function parseQuestions(text){const q=JSON.parse(text);if(!q||Array.isArray(q)||typeof q!=='object'||!Object.keys(q).length)throw new Error('Provide a nonempty questions object.');for(const [name,v]of Object.entries(q)){if(!v||!['choice','score','noul'].includes(v.type))throw new Error(name+': use choice, score, or noul.');if(v.type==='score'&&(!Array.isArray(v.criteria)||!v.criteria.length||v.criteria.length>10))throw new Error(name+': provide 1–10 ordered score levels.');if(v.type==='choice'&&(!v.criteria||Array.isArray(v.criteria)||typeof v.criteria!=='object'||!Object.keys(v.criteria).length))throw new Error(name+': provide named choices in a criteria object.');}return q;}
  return {percent,defaultScoreGradeMapping,validateMapping,scoreGrade,derivedGrade,withScoreGrades,answerValue,probabilityRows,isHouse,raceLabel,sortRaces,mergeDelta,catalogRows,catalogRaces,candidateSiteUrl,countyMatches,currentCair,cairLabel,cairComparison,comparisonQuestions,parseQuestions};
});
