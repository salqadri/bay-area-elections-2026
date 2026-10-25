// Optional production-only analytics; the readers never depend on this network request.
// Firebase's web configuration identifies the public app, not an administrative credential.
let analyticsStarted = false;
async function startPublishedAnalytics(location, loadSdk = () => Promise.all([
  import('https://www.gstatic.com/firebasejs/13.1.0/firebase-app.js'),
  import('https://www.gstatic.com/firebasejs/13.1.0/firebase-analytics.js')
])) {
  const publicOrigin = 'https://salqadri.github.io';
  const basePath = '/bay-area-elections-2026/';
  if (analyticsStarted || location.origin !== publicOrigin ||
      ![basePath, basePath + 'index.html', basePath + 'ballot.html'].includes(location.pathname)) return false;
  analyticsStarted = true;
  try {
    const [{initializeApp}, {initializeAnalytics, isSupported}] = await loadSdk();
    if (!await isSupported()) return false;
    const firebaseConfig = {
      apiKey: 'AIzaSyD8ALTnr2PWLhY5Wz7NA6TeYNY3LK3GvGM',
      authDomain: 'bay-area-elections-research.firebaseapp.com',
      projectId: 'bay-area-elections-research',
      storageBucket: 'bay-area-elections-research.firebasestorage.app',
      messagingSenderId: '693468629214',
      appId: '1:693468629214:web:04e5a5f66ac3d549e39a4f',
      measurementId: 'G-QKNPZZ1CDJ'
    };
    initializeAnalytics(initializeApp(firebaseConfig), {config: {
      // Never supply search text, candidate selections, addresses or referrer queries.
      // Treat / and /index.html as the same page in reports.
      page_location: publicOrigin + basePath + (location.pathname.endsWith('ballot.html') ? 'ballot.html' : ''),
      page_referrer: '',
      allow_google_signals: false,
      allow_ad_personalization_signals: false,
      cookie_domain: 'salqadri.github.io',
      cookie_path: basePath,
      cookie_prefix: 'bay_area_elections'
    }});
    return true;
  } catch (_) {
    // Ad blockers, offline browsers and unsupported environments must not break the app.
    console.warn('Optional site analytics could not be loaded.');
    return false;
  }
}
void startPublishedAnalytics(window.location);
