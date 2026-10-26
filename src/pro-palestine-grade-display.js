/* Project-owned Jev model scores; separate from source-publisher grades. */
const ProPalestineGradeDisplay = {
  render(candidate, data, {node}) {
    const grade=candidate.pro_palestine_score_grade,score=candidate.pro_palestine_score,meta=candidate.pro_palestine_evaluation;
    const valid=meta&&typeof score==='number'&&Number.isFinite(score)&&score>=0&&score<=5&&/^[A-F]$/.test(grade);
    const badge=node('a','pro-palestine-grade grade-'+(valid?grade.toLowerCase():'na'),valid?grade+' ('+score.toFixed(2)+' / 5)':'N/A');
    badge.href=data.pro_palestine_grading?.methodology_url||'https://github.com/salqadri/bay-area-elections-2026/blob/main/docs/PUBLISHED_GRADES.md';
    badge.target='_blank';badge.rel='noopener noreferrer';
    let description='Jev pro-Palestine model grade: '+(valid?grade+', score '+score.toFixed(2)+' out of 5':meta?'N/A: insufficient evidence (below 0.10 / 1)':'N/A: no saved evaluation');
    if(meta){description+=' · Model score confidence: '+(meta.confidence*100).toFixed(1)+'% · Evidence: '+meta.evidence_score+' / 1 · Evaluated '+new Date(meta.evaluated_at).toLocaleString('en-US',{timeZone:'America/Los_Angeles',dateStyle:'medium',timeStyle:'short'})+' PT';if(!valid)description+=' · Saved model score: '+score+' / 5';}
    description+=' · View rubric and methodology';badge.title=description;badge.setAttribute('aria-label',description);
    return badge;
  }
};
