'use strict';
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const {chromium}=require(process.env.PLAYWRIGHT_MODULE||(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES?path.join(process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES,'playwright'):'playwright'));
const base=process.env.TALL_TEST_BASE_URL||'http://127.0.0.1:4173';
const out=path.resolve(__dirname,'../../.checks/tall-guide');fs.mkdirSync(out,{recursive:true});
const address='200 E Santa Clara St, San Jose, CA 95113';
// Public-building address with synthetic, named geography. This is a UI/matching
// fixture, not an assertion about the building's real election districts.
const match={matchedAddress:address.toUpperCase(),coordinates:{x:-121.89,y:37.34},addressComponents:{city:'SAN JOSE',state:'CA',zip:'95113'},geographies:{States:[{STATE:'06'}],Counties:[{STATE:'06',COUNTY:'085',BASENAME:'Santa Clara'}],'Incorporated Places':[{STATE:'06',BASENAME:'San Jose'}],'120th Congressional Districts':[{STATE:'06',CDSESSN:'120',CD120:'17'}],'2026 State Legislative Districts - Upper':[{STATE:'06',SLDU:'15'}],'2026 State Legislative Districts - Lower':[{STATE:'06',SLDL:'24'}]}};
const pages=[];
(async()=>{
  const browser=await chromium.launch({headless:true,args:['--no-sandbox']});
  const errors=[];
  async function page(width=1440,height=1080){const p=await browser.newPage({viewport:{width,height}});p.on('pageerror',e=>errors.push(e.message));pages.push(p);return p;}
  async function ready(p,url='/'){await p.goto(base+url);await p.waitForFunction(()=>document.querySelector('#browse-county').options.length===6);}
  async function census(p,mode='success'){
    await p.route('https://geocoding.geo.census.gov/**',async route=>{
      const u=new URL(route.request().url()),cb=u.searchParams.get('callback');
      let matches=[structuredClone(match)];
      if(mode==='none')matches=[];
      if(mode==='multiple'){const second=structuredClone(match);second.matchedAddress='1 DR CARLTON B GOODLETT PL, SAN FRANCISCO, CA';second.geographies.Counties=[{STATE:'06',COUNTY:'075',BASENAME:'San Francisco'}];second.geographies['Incorporated Places']=[{STATE:'06',BASENAME:'San Francisco'}];matches.push(second);}
      if(mode==='outside'){matches[0].geographies={States:[{STATE:'32'}],Counties:[{STATE:'32',COUNTY:'003',BASENAME:'Clark'}]};}
      await route.fulfill({status:200,contentType:'application/javascript',body:cb+'('+JSON.stringify({result:{addressMatches:matches}})+');'});
    });
  }
  async function submit(p,value=address){await p.locator('#address').fill(value);await p.locator('#find-ballot').click();}
  async function noOverflow(p){assert.equal(await p.evaluate(()=>document.documentElement.scrollWidth>innerWidth),false,'Horizontal page overflow');}
  try{
    const desktop=await page();await ready(desktop);await noOverflow(desktop);
    await desktop.screenshot({path:path.join(out,'desktop-home.png'),fullPage:true});
    const mobile=await page(390,844);await ready(mobile);await noOverflow(mobile);await mobile.screenshot({path:path.join(out,'mobile-home.png'),fullPage:true});
    for(const width of [320,768,1024]){await mobile.setViewportSize({width,height:900});await noOverflow(mobile);}
    await mobile.setViewportSize({width:390,height:844});
    await census(desktop);await submit(desktop);await desktop.waitForSelector('#results:not([hidden])');
    assert.ok((await desktop.locator('#result-count').textContent()).includes('expected'));
    assert.ok((await desktop.locator('.race-card').count())>0);
    assert.equal(await desktop.locator('#possible-races').getAttribute('open'),null);
    const firstDistrict=await desktop.locator('.race-card .race-district').first().textContent();assert.equal(firstDistrict,'Statewide');
    const firstCard=desktop.locator('.race-card').first();await firstCard.locator('.race-candidates>summary').click();assert.ok(await firstCard.locator('.candidate').count()>0);
    const why=desktop.locator('.read-more').first();await why.click();assert.equal(await why.getAttribute('aria-expanded'),'true');
    await desktop.screenshot({path:path.join(out,'desktop-ballot.png'),fullPage:true});
    await desktop.locator('#possible-races>summary').click();await desktop.screenshot({path:path.join(out,'district-confirmation.png'),fullPage:false});
    await desktop.emulateMedia({media:'print'});
    assert.equal(await desktop.locator('#hero').isVisible(),false);
    assert.equal((await desktop.locator('body').innerText()).includes(address),false);
    await desktop.emulateMedia({media:'screen'});
    assert.equal(await desktop.evaluate(()=>localStorage.length+sessionStorage.length),0);
    assert.equal(new URL(desktop.url()).search,'');
    // Keyboard-accessible county browsing and intentionally broad matches.
    await mobile.locator('#browse-counties').click();await mobile.locator('#browse-county').selectOption('Santa Clara');await mobile.locator('#browse-county-go').click();
    await mobile.waitForSelector('#results:not([hidden])');assert.ok((await mobile.locator('#result-count').textContent()).includes('possibilities'));await noOverflow(mobile);
    await mobile.screenshot({path:path.join(out,'mobile-county.png'),fullPage:false});
    const all=await page(1440,1080);await ready(all,'/candidates.html');await all.waitForSelector('.race-card');
    assert.equal(await all.locator('.race-card').count(),24);
    assert.equal(await all.locator('#candidates-tab').getAttribute('aria-current'),'page');
    await all.locator('#filter-county').selectOption('Santa Clara');await all.locator('#filter-search').fill('Ro Khanna');
    assert.equal(await all.locator('.race-card').count(),1);assert.equal(await all.locator('.candidate h4').filter({hasText:'Ro Khanna'}).count(),1);
    await all.screenshot({path:path.join(out,'all-candidates.png'),fullPage:true});
    await all.setViewportSize({width:390,height:844});await noOverflow(all);await all.screenshot({path:path.join(out,'mobile-candidates.png'),fullPage:true});
    await all.locator('#filter-search').fill('no such test candidate');assert.equal(await all.locator('#empty-state').isVisible(),true);
    await all.locator('#filter-search').fill('');await all.locator('#filter-county').selectOption('');await all.locator('#load-more').click();assert.equal(await all.locator('.race-card').count(),48);
    const schoolLink=all.locator('#section-nav a').filter({hasText:'Schools & colleges'});await schoolLink.click();assert.equal(await all.locator('#section-6').count(),1);
    const none=await page();await census(none,'none');await ready(none);await submit(none);await none.waitForSelector('#lookup-error:not([hidden])');assert.equal(await none.locator('#results').isVisible(),false);
    const multiple=await page();await census(multiple,'multiple');await ready(multiple);await submit(multiple);await multiple.waitForSelector('#address-matches:not([hidden])');assert.equal(await multiple.locator('#address-match option').count(),3);assert.equal(await multiple.locator('#results-title').textContent(),'Possible races across matches');await multiple.locator('#address-match').selectOption('0');assert.equal(await multiple.locator('#results-title').textContent(),'Your ballot guide');
    const outside=await page();await census(outside,'outside');await ready(outside);await submit(outside);await outside.waitForSelector('#empty-state:not([hidden])');assert.ok((await outside.locator('#empty-message').textContent()).includes('outside'));
    // A superseded request may not overwrite a newer county result.
    const pending=await page();let pendingRoute;await pending.route('https://geocoding.geo.census.gov/**',r=>{pendingRoute=r;});await ready(pending);await submit(pending);await pending.waitForFunction(()=>document.querySelector('#find-ballot').disabled);await pending.locator('#browse-counties').click();await pending.locator('#browse-county').selectOption('Alameda');await pending.locator('#browse-county-go').click();await pending.waitForSelector('#results:not([hidden])');assert.ok((await pending.locator('#result-context').textContent()).includes('Alameda'));if(pendingRoute)await pendingRoute.abort().catch(()=>{});
    // Official widget contract, selected-address fields, and manual fallback.
    const google=await page();await google.route('**/config.js',r=>r.fulfill({contentType:'application/javascript',body:'window.TALL_CONFIG={googleMapsApiKey:"fixture-browser-key"};'}));
    await google.route('https://maps.googleapis.com/**',route=>{const cb=new URL(route.request().url()).searchParams.get('callback');return route.fulfill({contentType:'application/javascript',body:`class MockAutocomplete extends HTMLElement {constructor(options){super();window.mockOptions=options;}};customElements.define('gmp-place-autocomplete',MockAutocomplete);window.google={maps:{importLibrary:async()=>({PlaceAutocompleteElement:MockAutocomplete})}};window.${cb}();`});});
    await census(google);await ready(google);await google.waitForSelector('gmp-place-autocomplete');assert.equal(await google.locator('#manual-fields').isVisible(),false);
    await google.evaluate(address=>{const e=new Event('gmp-select');e.placePrediction={toPlace:()=>({formattedAddress:address,fetchFields:async options=>{window.mockFields=options.fields;}})};document.querySelector('gmp-place-autocomplete').dispatchEvent(e);},address);
    await google.waitForSelector('#results:not([hidden])');assert.deepEqual(await google.evaluate(()=>mockFields),['formattedAddress']);assert.deepEqual(await google.evaluate(()=>mockOptions.includedRegionCodes),['us']);await google.locator('#use-manual').click();assert.equal(await google.locator('#manual-fields').isVisible(),true);
    const failedGoogle=await page();await failedGoogle.route('**/config.js',r=>r.fulfill({contentType:'application/javascript',body:'window.TALL_CONFIG={googleMapsApiKey:"fixture-browser-key"};'}));await failedGoogle.route('https://maps.googleapis.com/**',r=>r.abort());await ready(failedGoogle);await failedGoogle.waitForSelector('#lookup-error:not([hidden])');assert.equal(await failedGoogle.locator('#manual-fields').isVisible(),true);
    await desktop.locator('[data-open-dialog="privacy-dialog"]').first().click();assert.equal(await desktop.locator('#privacy-dialog').isVisible(),true);await desktop.keyboard.press('Escape');assert.equal(await desktop.locator('#privacy-dialog').isVisible(),false);
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(out,'browser-results.json'),JSON.stringify({passed:true,checks:['desktop/mobile layout','California order','expand candidate/rationale','county alternatives','candidate filters/pagination','no match','ambiguous matches','outside coverage','cancellation','Google selected address','Google failure/manual fallback','print privacy','no storage','dialog keyboard'],uncaughtErrors:errors},null,2));
    console.log('PASS 14 browser scenarios, 4 viewport widths; no uncaught page errors');
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;});
