/* Race-level support recommendations. Display only: every decision is computed
   by scripts/build_recommendations.py against the published grades and archived
   with the recommendation plan; the page never derives or reranks anything. */
const RecommendationDisplay = {
  render(positionId, { node, recs, confirmed }) {
    const r = recs && recs.byPosition && recs.byPosition[positionId];
    if (!r || !confirmed) return null;
    const box = node('div', 'race-recommendation ' + (r.recommended ? 'pick' : 'none'));
    const head = node('p', 'race-recommendation-head');
    if (r.recommended) {
      head.append(node('span', 'race-recommendation-label', 'Our pick:'),
                  node('strong', 'race-recommendation-name', r.recommended));
      if (r.category === 'muslim_community') head.append(node('span', 'race-recommendation-badge', 'Muslim community'));
    } else {
      head.append(node('span', 'race-recommendation-label', 'No recommendation'),
                  node('span', null, String(r.recommend_reason || '').replace(/^No recommendation due to a lack of /, 'for lack of ').replace(/^No recommendation due to /, '— ')));
    }
    box.append(head);
    const why = r.why && r.why.text;
    if (why) {
      const details = node('details', 'race-recommendation-why');
      details.append(node('summary', null, 'Why this pick?'));
      details.append(node('p', 'race-recommendation-text', why));
      details.append(node('p', 'race-recommendation-note', 'Written by ' + r.why.model + ' from the recorded evidence and published grades for the candidates in this race. Picks follow our published rules: a confirmed Muslim-community candidate first, otherwise the strongest published pro-Palestine record. Recommendation set dated ' + (recs.generated_on || '') + '.'));
      box.append(details);
    }
    return box;
  }
};
