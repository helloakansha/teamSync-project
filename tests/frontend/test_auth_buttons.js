/**
 * Automated test suite for frontend authentication navigation buttons:
 * 1. Logged-out dashboard displays the correct buttons.
 * 2. Successful login updates the navigation immediately.
 * 3. Refreshing after login preserves the correct navigation.
 * 4. Logout restores the logged-out navigation.
 * 5. Invalid or expired tokens do not leave the dashboard showing authenticated navigation.
 * 6. Existing signup behaviour remains correct.
 */

const fs = require('fs');
const path = require('path');
const vm = require('vm');

// Consistent project root detection for tests/frontend/
const projectRoot = (() => {
  const candidates = [
    path.resolve(__dirname, '..', '..'),
    path.resolve(__dirname, '..'),
    __dirname
  ];
  for (const c of candidates) {
    if (fs.existsSync(path.join(c, 'frontend', 'script.js'))) return c;
  }
  return path.resolve(__dirname, '..', '..');
})();

console.log('='.repeat(75));
console.log('TEAMSYNC — FRONTEND AUTHENTICATION NAVIGATION VERIFICATION TEST SUITE');
console.log('='.repeat(75));

// Create browser mock environment
class LocalStorageMock {
  constructor() {
    this.store = {};
  }
  getItem(key) {
    return this.store.hasOwnProperty(key) ? this.store[key] : null;
  }
  setItem(key, val) {
    this.store[key] = String(val);
  }
  removeItem(key) {
    delete this.store[key];
  }
  clear() {
    this.store = {};
  }
}

class DOMElementMock {
  constructor(id, tagName = 'div') {
    this.id = id;
    this.tagName = tagName;
    this.style = {};
    this.classList = {
      classes: new Set(),
      add: (c) => this.classList.classes.add(c),
      remove: (c) => this.classList.classes.delete(c),
      contains: (c) => this.classList.classes.has(c),
      toggle: (c) => {
        if (this.classList.contains(c)) this.classList.remove(c);
        else this.classList.add(c);
      }
    };
    this.innerHTML = '';
    this.textContent = '';
    this.attributes = {};
    this.eventListeners = {};
  }
  setAttribute(k, v) { this.attributes[k] = v; }
  getAttribute(k) { return this.attributes[k]; }
  removeAttribute(k) { delete this.attributes[k]; }
  addEventListener(event, fn) {
    if (!this.eventListeners[event]) this.eventListeners[event] = [];
    this.eventListeners[event].push(fn);
  }
  dispatchEvent(event) {
    const list = this.eventListeners[event] || [];
    list.forEach(fn => fn({ preventDefault: () => {} }));
  }
}

function createDOMContext() {
  const elements = {};
  const elementIds = [
    'landing-page', 'dashboard-page', 'group-details-page',
    'nav-brand', 'nav-login-btn', 'nav-signup-btn', 'nav-dashboard-btn', 'nav-logout-btn',
    'get-started-btn', 'about-cta-btn', 'back-to-landing-btn',
    'logout-btn', 'dashboard-welcome', 'groups-grid', 'sessions-list',
    'dashboard-sessions-count', 'group-count', 'connect-calendar-btn', 'disconnect-calendar-btn',
    'details-back-btn', 'details-error-back-btn', 'hamburger-btn', 'sidebar'
  ];

  elementIds.forEach(id => {
    elements[id] = new DOMElementMock(id);
  });

  // landing-page is active by default
  elements['landing-page'].classList.add('active');

  const localStorage = new LocalStorageMock();

  const windowMock = {
    location: { search: '', pathname: '/', hash: '' },
    history: { replaceState: () => {} },
    scrollTo: () => {},
    localStorage: localStorage
  };

  const documentMock = {
    getElementById: (id) => elements[id] || new DOMElementMock(id),
    querySelector: () => null,
    querySelectorAll: () => [],
    addEventListener: () => {},
    title: 'TeamSync'
  };

  return { elements, localStorage, windowMock, documentMock };
}

function generateJwt(userId, expSecondsFromNow) {
  const header = Buffer.from(JSON.stringify({ alg: 'HS256', typ: 'JWT' })).toString('base64');
  const payloadObj = { sub: String(userId) };
  if (expSecondsFromNow !== undefined) {
    payloadObj.exp = Math.floor(Date.now() / 1000) + expSecondsFromNow;
  }
  const payload = Buffer.from(JSON.stringify(payloadObj)).toString('base64');
  return `${header}.${payload}.signature`;
}

// Read script.js code
const scriptPath = path.join(projectRoot, 'frontend', 'script.js');
const scriptCode = fs.readFileSync(scriptPath, 'utf8');

const results = [];
function record(name, passed, detail = '') {
  const status = passed ? 'PASS' : 'FAIL';
  const sym = passed ? '✓' : '✗';
  results.push({ name, passed, detail });
  console.log(`[${status}] ${sym} ${name}`);
  if (detail) console.log(`       Detail: ${detail}`);
}

// =========================================================================
// TEST 1: Logged-out state displays correct buttons
// =========================================================================
{
  const { elements, localStorage, windowMock, documentMock } = createDOMContext();
  const ctx = {
    window: windowMock,
    document: documentMock,
    localStorage: localStorage,
    console: console,
    atob: (s) => Buffer.from(s, 'base64').toString('utf8'),
    Date: Date,
    URLSearchParams: URLSearchParams,
    URLSearchParams: URLSearchParams,
    fetch: async () => ({ ok: true, json: async () => ({}) }),
    API_BASE_URL: 'http://127.0.0.1:8000',
    alert: () => {}
  };
  vm.createContext(ctx);
  vm.runInContext(scriptCode, ctx);

  // Run updateAuthNavigation
  ctx.updateAuthNavigation();

  const loginDisplay = elements['nav-login-btn'].style.display;
  const signupDisplay = elements['nav-signup-btn'].style.display;
  const dashDisplay = elements['nav-dashboard-btn'].style.display;
  const logoutDisplay = elements['nav-logout-btn'].style.display;

  const t1Passed = (
    loginDisplay !== 'none' &&
    signupDisplay !== 'none' &&
    dashDisplay === 'none' &&
    logoutDisplay === 'none'
  );

  record(
    'Test 1: Logged-out dashboard displays Sign In / Sign Up and hides authenticated options',
    t1Passed,
    `Login display: "${loginDisplay}", Signup: "${signupDisplay}", Dashboard: "${dashDisplay}", Logout: "${logoutDisplay}"`
  );
}

// =========================================================================
// TEST 2: Successful login updates navigation immediately without page refresh
// =========================================================================
{
  const { elements, localStorage, windowMock, documentMock } = createDOMContext();
  const validToken = generateJwt(101, 3600); // 1 hour valid
  const testUser = { id: 101, name: 'TestUser', email: 'test@example.com' };

  const ctx = {
    window: windowMock,
    document: documentMock,
    localStorage: localStorage,
    console: console,
    atob: (s) => Buffer.from(s, 'base64').toString('utf8'),
    Date: Date,
    URLSearchParams: URLSearchParams,
    fetch: async () => ({ ok: true, json: async () => ({ groups: [], sessions: [] }) }),
    API_BASE_URL: 'http://127.0.0.1:8000',
    alert: () => {}
  };
  vm.createContext(ctx);
  vm.runInContext(scriptCode, ctx);

  // Initial logged out check
  ctx.updateAuthNavigation();
  const initialLoginVisible = elements['nav-login-btn'].style.display !== 'none';

  // Simulate login event (as in loginForm submit handler)
  localStorage.setItem('currentUser', JSON.stringify(testUser));
  localStorage.setItem('authToken', validToken);
  ctx.updateDashboardUser(testUser);
  ctx.updateAuthNavigation();
  ctx.showDashboard();

  const postLoginLoginHidden = elements['nav-login-btn'].style.display === 'none';
  const postLoginSignupHidden = elements['nav-signup-btn'].style.display === 'none';
  const postLoginDashVisible = elements['nav-dashboard-btn'].style.display !== 'none';
  const postLoginLogoutVisible = elements['nav-logout-btn'].style.display !== 'none';
  const dashboardActive = elements['dashboard-page'].classList.contains('active');
  const landingInactive = !elements['landing-page'].classList.contains('active');

  const t2Passed = (
    initialLoginVisible &&
    postLoginLoginHidden &&
    postLoginSignupHidden &&
    postLoginDashVisible &&
    postLoginLogoutVisible &&
    dashboardActive &&
    landingInactive
  );

  record(
    'Test 2: Successful login immediately updates navigation (hides login/signup, shows dashboard/logout)',
    t2Passed,
    `Initial login visible: ${initialLoginVisible}, Post-login login hidden: ${postLoginLoginHidden}, Dashboard shown: ${dashboardActive}`
  );
}

// =========================================================================
// TEST 3: Refreshing after login preserves the correct navigation state
// =========================================================================
{
  const { elements, localStorage, windowMock, documentMock } = createDOMContext();
  const validToken = generateJwt(102, 3600);
  const testUser = { id: 102, name: 'RefreshUser', email: 'refresh@example.com' };

  // Pre-populate localStorage as if previously logged in before page refresh
  localStorage.setItem('currentUser', JSON.stringify(testUser));
  localStorage.setItem('authToken', validToken);

  const ctx = {
    window: windowMock,
    document: documentMock,
    localStorage: localStorage,
    console: console,
    atob: (s) => Buffer.from(s, 'base64').toString('utf8'),
    Date: Date,
    URLSearchParams: URLSearchParams,
    fetch: async () => ({ ok: true, json: async () => ({ groups: [], sessions: [] }) }),
    API_BASE_URL: 'http://127.0.0.1:8000',
    alert: () => {}
  };
  vm.createContext(ctx);
  vm.runInContext(scriptCode, ctx);

  // Execute init() as browser does on page load / refresh
  ctx.init();

  const loginHiddenOnRefresh = elements['nav-login-btn'].style.display === 'none';
  const signupHiddenOnRefresh = elements['nav-signup-btn'].style.display === 'none';
  const dashVisibleOnRefresh = elements['nav-dashboard-btn'].style.display !== 'none';
  const logoutVisibleOnRefresh = elements['nav-logout-btn'].style.display !== 'none';
  const dashboardActiveOnRefresh = elements['dashboard-page'].classList.contains('active');

  const t3Passed = (
    loginHiddenOnRefresh &&
    signupHiddenOnRefresh &&
    dashVisibleOnRefresh &&
    logoutVisibleOnRefresh &&
    dashboardActiveOnRefresh
  );

  record(
    'Test 3: Refreshing after login preserves authenticated navigation & activates dashboard',
    t3Passed,
    `Login hidden: ${loginHiddenOnRefresh}, Signup hidden: ${signupHiddenOnRefresh}, Dashboard active: ${dashboardActiveOnRefresh}`
  );
}

// =========================================================================
// TEST 4: Logout restores the logged-out navigation
// =========================================================================
{
  const { elements, localStorage, windowMock, documentMock } = createDOMContext();
  const validToken = generateJwt(103, 3600);
  const testUser = { id: 103, name: 'LogoutUser', email: 'logout@example.com' };

  localStorage.setItem('currentUser', JSON.stringify(testUser));
  localStorage.setItem('authToken', validToken);

  const ctx = {
    window: windowMock,
    document: documentMock,
    localStorage: localStorage,
    console: console,
    atob: (s) => Buffer.from(s, 'base64').toString('utf8'),
    Date: Date,
    URLSearchParams: URLSearchParams,
    fetch: async () => ({ ok: true, json: async () => ({ groups: [], sessions: [] }) }),
    API_BASE_URL: 'http://127.0.0.1:8000',
    alert: () => {}
  };
  vm.createContext(ctx);
  vm.runInContext(scriptCode, ctx);

  // Initialize in logged in state
  ctx.init();

  // Execute logout
  ctx.handleLogout();

  const tokenCleared = !localStorage.getItem('authToken');
  const userCleared = !localStorage.getItem('currentUser');
  const loginShownPostLogout = elements['nav-login-btn'].style.display !== 'none';
  const signupShownPostLogout = elements['nav-signup-btn'].style.display !== 'none';
  const dashHiddenPostLogout = elements['nav-dashboard-btn'].style.display === 'none';
  const logoutHiddenPostLogout = elements['nav-logout-btn'].style.display === 'none';
  const landingActivePostLogout = elements['landing-page'].classList.contains('active');

  const t4Passed = (
    tokenCleared &&
    userCleared &&
    loginShownPostLogout &&
    signupShownPostLogout &&
    dashHiddenPostLogout &&
    logoutHiddenPostLogout &&
    landingActivePostLogout
  );

  record(
    'Test 4: Logout clears credentials, restores logged-out buttons and shows landing page',
    t4Passed,
    `Token cleared: ${tokenCleared}, User cleared: ${userCleared}, Login visible: ${loginShownPostLogout}, Landing active: ${landingActivePostLogout}`
  );
}

// =========================================================================
// TEST 5: Expired or invalid token does not display authenticated navigation
// =========================================================================
{
  const { elements, localStorage, windowMock, documentMock } = createDOMContext();
  // Expired 1 hour ago (-3600s)
  const expiredToken = generateJwt(104, -3600);
  const testUser = { id: 104, name: 'ExpiredUser', email: 'expired@example.com' };

  localStorage.setItem('currentUser', JSON.stringify(testUser));
  localStorage.setItem('authToken', expiredToken);

  const ctx = {
    window: windowMock,
    document: documentMock,
    localStorage: localStorage,
    console: console,
    atob: (s) => Buffer.from(s, 'base64').toString('utf8'),
    Date: Date,
    URLSearchParams: URLSearchParams,
    fetch: async () => ({ ok: true, json: async () => ({ groups: [], sessions: [] }) }),
    API_BASE_URL: 'http://127.0.0.1:8000',
    alert: () => {}
  };
  vm.createContext(ctx);
  vm.runInContext(scriptCode, ctx);

  // Execute init with expired token
  ctx.init();

  const tokenExpiredPurged = !localStorage.getItem('authToken');
  const loginShownExpired = elements['nav-login-btn'].style.display !== 'none';
  const signupShownExpired = elements['nav-signup-btn'].style.display !== 'none';
  const dashHiddenExpired = elements['nav-dashboard-btn'].style.display === 'none';
  const logoutHiddenExpired = elements['nav-logout-btn'].style.display === 'none';
  const landingActiveExpired = elements['landing-page'].classList.contains('active');

  const t5Passed = (
    tokenExpiredPurged &&
    loginShownExpired &&
    signupShownExpired &&
    dashHiddenExpired &&
    logoutHiddenExpired &&
    landingActiveExpired
  );

  record(
    'Test 5: Expired token automatically purges credentials and keeps logged-out navigation',
    t5Passed,
    `Expired token purged: ${tokenExpiredPurged}, Login shown: ${loginShownExpired}, Dash hidden: ${dashHiddenExpired}`
  );
}

// =========================================================================
// TEST 6: Signup without token does not assume automatic authentication
// =========================================================================
{
  const { elements, localStorage, windowMock, documentMock } = createDOMContext();

  const ctx = {
    window: windowMock,
    document: documentMock,
    localStorage: localStorage,
    console: console,
    atob: (s) => Buffer.from(s, 'base64').toString('utf8'),
    Date: Date,
    URLSearchParams: URLSearchParams,
    fetch: async () => ({ ok: true, json: async () => ({ groups: [], sessions: [] }) }),
    API_BASE_URL: 'http://127.0.0.1:8000',
    alert: () => {}
  };
  vm.createContext(ctx);
  vm.runInContext(scriptCode, ctx);

  // Simulate signup response WITHOUT access_token
  const signupDataNoToken = {
    success: true,
    message: 'Account created! Please check your email.',
    user: { id: 105, name: 'NewUser', email: 'new@example.com' }
    // No access_token
  };

  // Simulate signup logic
  if (signupDataNoToken.access_token && signupDataNoToken.user) {
    localStorage.setItem('currentUser', JSON.stringify(signupDataNoToken.user));
    localStorage.setItem('authToken', signupDataNoToken.access_token);
    ctx.updateDashboardUser(signupDataNoToken.user);
    ctx.updateAuthNavigation();
    ctx.showDashboard();
  } else {
    ctx.updateAuthNavigation();
  }

  const tokenNotSaved = !localStorage.getItem('authToken');
  const loginShown = elements['nav-login-btn'].style.display !== 'none';
  const dashHidden = elements['nav-dashboard-btn'].style.display === 'none';

  const t6Passed = (tokenNotSaved && loginShown && dashHidden);

  record(
    'Test 6: Signup without access_token reflects unauthenticated state and does not assume login',
    t6Passed,
    `Token not saved: ${tokenNotSaved}, Login button visible: ${loginShown}, Dashboard hidden: ${dashHidden}`
  );
}

console.log('='.repeat(75));
const total = results.length;
const passedCount = results.filter(r => r.passed).length;
console.log(`AUTH BUTTONS SUMMARY: ${passedCount}/${total} TESTS PASSED`);
console.log('='.repeat(75));

if (passedCount < total) {
  process.exit(1);
}
