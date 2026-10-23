/* Pure presentation helpers. No grade acceptance rules or confidence cutoffs. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.JevPlaygroundCore=api;})(typeof globalThis==='object'?globalThis:this,()=>{
  const percent=n=>typeof n==='number'&&Number.isFinite(n)?new Intl.NumberFormat('en-US',{style:'percent',maximumFractionDigits:1}).format(n):'Not returned';
  function answerValue(answer,question){
    if(!answer)return 'Not run';
    if(answer.type==='choice')return String(answer.choice);
    if(answer.type==='score')return Number(answer.score).toFixed(2)+' / '+Math.max(0,(question?.criteria?.length||1)-1);
    if(answer.type==='noul')return percent(answer.noul)+' true';
    return JSON.stringify(answer);
  }
  function sortRaces(races,label=code=>code){return [...races].sort((a,b)=>label(a.state).localeCompare(label(b.state),'en-US')||String(a.district_or_seat).localeCompare(String(b.district_or_seat),'en-US',{numeric:true})||a.id.localeCompare(b.id));}
  function mergeDelta(run,delta){
    if(run.id!==delta.id)throw new Error('Run identity mismatch');
    const changes=new Map(delta.changes.map(row=>[row.id,row]));
    return {...run,...Object.fromEntries(Object.entries(delta).filter(([key])=>key!=='changes')),rows:run.rows.map(row=>changes.has(row.id)?{...row,...changes.get(row.id),request:row.request}:row)};
  }
  function catalogRows(snapshot,run){
    const rows=new Map(snapshot.candidates.map(c=>[c.id,{...c,status:'preview'}]));
    for(const row of run.rows)rows.set(row.id,row);
    return [...rows.values()];
  }
  function catalogRaces(snapshot,run){return [...new Map([...snapshot.races,...run.races].map(r=>[r.id,r])).values()];}
  function parseQuestions(text){const q=JSON.parse(text);if(!q||Array.isArray(q)||typeof q!=='object'||!Object.keys(q).length)throw new Error('Provide a nonempty questions object.');for(const [name,v]of Object.entries(q)){if(!v||!['choice','score','noul'].includes(v.type))throw new Error(name+': use choice, score, or noul.');if(v.type==='score'&&(!Array.isArray(v.criteria)||!v.criteria.length||v.criteria.length>10))throw new Error(name+': provide 1–10 ordered score levels.');if(v.type==='choice'&&(!v.criteria||Array.isArray(v.criteria)||typeof v.criteria!=='object'||!Object.keys(v.criteria).length))throw new Error(name+': provide named choices in a criteria object.');}return q;}
  return {percent,answerValue,sortRaces,mergeDelta,catalogRows,catalogRaces,parseQuestions};
});
