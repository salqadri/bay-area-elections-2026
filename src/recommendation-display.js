/* Race-level support recommendations. Display only: every decision is computed
   by scripts/build_recommendations.py against the published grades and archived
   with the recommendation plan; the page never derives or reranks anything. */
const RecommendationDisplay = {
  whyKey: 'recommendation-why',
  whyCollapsed() {
    try { return localStorage.getItem(this.whyKey) === 'collapsed'; } catch { return false; }
  },
  rememberWhy(open) {
    try { open ? localStorage.removeItem(this.whyKey) : localStorage.setItem(this.whyKey, 'collapsed'); } catch {}
  },
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
      // Expanded by default; one explicit collapse is remembered across races.
      if (!this.whyCollapsed()) details.open = true;
      details.addEventListener('toggle', () => this.rememberWhy(!!details.open));
      details.append(node('summary', null, 'Why this pick?'));
      details.append(node('p', 'race-recommendation-text', why));
      if (recs.generated_on) details.append(node('p', 'race-recommendation-note', 'Recommendation set dated ' + recs.generated_on + '.'));
      box.append(details);
    }
    return box;
  }
};
