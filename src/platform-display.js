/* Shared campaign platform positions renderer. Text and links are created as DOM nodes. */
const PlatformDisplay = {
  render(candidate, {node, link, dateLabel, className = 'candidate-evidence platform-positions'}) {
    const platform = candidate.platform_positions;
    if (!platform) return null;
    const disclosure = node('details', className);
    disclosure.append(node('summary', null, 'What they stand for · Campaign platform'));
    // Guard here as well as in each reader's general-purpose link helper.
    const sourceLink = (url, text) => {
      try {
        const parsed = new URL(url);
        if (['http:', 'https:'].includes(parsed.protocol)) return link(parsed.href, text, 'platform-source');
      } catch {}
      return node('span', 'platform-source', text + ' (link unavailable)');
    };
    const statuses = {
      positions_found: 'Policy positions quoted from the campaign’s own website.',
      no_positions_found: 'No policy position was found on the reviewed campaign website pages. This is not proof that none exists elsewhere.',
      unavailable: 'Campaign website review unavailable or incomplete.',
      no_website: 'No verified campaign website is recorded in this inventory.'
    };
    disclosure.append(node('p', 'platform-status', statuses[platform.status] || 'Platform review unresolved.'));
    for (const point of platform.points || []) {
      const item = node('div', 'platform-point');
      item.append(node('span', 'platform-topic', point.topic));
      item.append(node('p', 'platform-summary', point.summary));
      if (point.quote) item.append(node('blockquote', 'platform-quote', '“' + point.quote + '”'));
      if (point.source_url) {
        const source = node('p', 'platform-links');
        source.append(sourceLink(point.source_url, 'Source page ↗'));
        item.append(source);
      }
      disclosure.append(item);
    }
    if (platform.scope_note) disclosure.append(node('p', 'platform-note', platform.scope_note));
    if (platform.checked_on) disclosure.append(node('p', 'platform-note', 'Snapshot checked ' + dateLabel(platform.checked_on)));
    if (platform.pages?.length) {
      const pages = node('details', 'platform-pages');
      pages.append(node('summary', null, 'Reviewed pages · ' + platform.pages.length));
      const list = node('ul');
      for (const page of platform.pages) {
        const item = node('li');
        item.append(sourceLink(page.url, page.title || page.url));
        list.append(item);
      }
      pages.append(list);
      disclosure.append(pages);
    }
    return disclosure;
  }
};
