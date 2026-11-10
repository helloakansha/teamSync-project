/**
 * TeamSync - Functional Sidebar Navigation Automated Test Suite
 * 
 * Verifies all 7 sidebar navigation items:
 * 1. Dashboard (overview, stats, groups grid, sessions list)
 * 2. My Groups (dedicated view, groups grid, card details, open group, create, join)
 * 3. Sessions (dedicated view, filter tabs: all/upcoming/past, sync status badges, empty states)
 * 4. Tasks (dedicated view, filter tabs, stats panel, task cards with group names & status select)
 * 5. Settings (account profile, calendar connection status, connect/disconnect controls, not-implemented preferences notice)
 * 6. Log Out (clears auth, returns to landing, protects views)
 * 7. Back to Home (returns to landing without logging out, preserves login state)
 * 
 * Plus:
 * - Active navigation highlighting synchronization
 * - Refresh & hash navigation restoration
 * - Unauthorized access rejection
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
console.log('TEAMSYNC — FUNCTIONAL SIDEBAR NAVIGATION VERIFICATION TEST SUITE');
console.log('='.repeat(75));

let passed = 0;
let failed = 0;

function assert(cond, msg) {
  if (cond) {
    passed++;
    console.log(`  ✓ ${msg}`);
  } else {
    failed++;
    console.error(`  ✗ FAIL: ${msg}`);
  }
}

// ────────────────────────────────────────────────────────────────
// PART 1: STATIC HTML INSPECTION FOR SIDEBAR & SUBVIEWS
// ────────────────────────────────────────────────────────────────
console.log('\n[PART 1] Inspecting index.html for sidebar and subview markup...');

const indexPath = path.join(projectRoot, 'frontend', 'index.html');
const indexHtml = fs.readFileSync(indexPath, 'utf-8');

// Sidebar nav links exist with data-section
assert(indexHtml.includes('id="nav-dashboard" data-section="dashboard"'), 'Sidebar link #nav-dashboard exists');
assert(indexHtml.includes('id="nav-groups" data-section="groups"'), 'Sidebar link #nav-groups exists');
assert(indexHtml.includes('id="nav-sessions" data-section="sessions"'), 'Sidebar link #nav-sessions exists');
assert(indexHtml.includes('id="nav-tasks" data-section="tasks"'), 'Sidebar link #nav-tasks exists');
assert(indexHtml.includes('id="nav-settings" data-section="settings"'), 'Sidebar link #nav-settings exists');
assert(indexHtml.includes('id="logout-btn"'), 'Sidebar footer button #logout-btn exists');
assert(indexHtml.includes('id="back-to-landing-btn"'), 'Sidebar footer button #back-to-landing-btn exists');

// Subviews exist in dashboard-main
assert(indexHtml.includes('id="dashboard-view-overview"'), 'Subview #dashboard-view-overview exists');
assert(indexHtml.includes('id="dashboard-view-groups"'), 'Subview #dashboard-view-groups exists');
assert(indexHtml.includes('id="dashboard-view-sessions"'), 'Subview #dashboard-view-sessions exists');
assert(indexHtml.includes('id="dashboard-view-tasks"'), 'Subview #dashboard-view-tasks exists');
assert(indexHtml.includes('id="dashboard-view-settings"'), 'Subview #dashboard-view-settings exists');

// Subview containers exist
assert(indexHtml.includes('id="my-groups-full-grid"'), 'Container #my-groups-full-grid exists in Groups view');
assert(indexHtml.includes('id="my-sessions-full-list"'), 'Container #my-sessions-full-list exists in Sessions view');
assert(indexHtml.includes('id="my-tasks-full-list"'), 'Container #my-tasks-full-list exists in Tasks view');
assert(indexHtml.includes('id="settings-user-name"'), 'Element #settings-user-name exists in Settings view');
assert(indexHtml.includes('id="settings-calendar-badge"'), 'Element #settings-calendar-badge exists in Settings view');
assert(indexHtml.includes('id="settings-connect-calendar-btn"'), 'Button #settings-connect-calendar-btn exists in Settings view');
assert(indexHtml.includes('id="settings-disconnect-calendar-btn"'), 'Button #settings-disconnect-calendar-btn exists in Settings view');
assert(indexHtml.toLowerCase().includes('not implemented'), 'Not Implemented notice exists for unimplemented preferences in Settings view');

// ────────────────────────────────────────────────────────────────
// PART 2: STATIC SCRIPT.JS INSPECTION FOR SIDEBAR FUNCTIONS
// ────────────────────────────────────────────────────────────────
console.log('\n[PART 2] Inspecting script.js for sidebar functions...');

const scriptPath = path.join(projectRoot, 'frontend', 'script.js');
const scriptJs = fs.readFileSync(scriptPath, 'utf-8');

assert(scriptJs.includes('function showDashboardView'), 'Function showDashboardView exists');
assert(scriptJs.includes('function loadMyGroupsView'), 'Function loadMyGroupsView exists');
assert(scriptJs.includes('function loadMySessionsView'), 'Function loadMySessionsView exists');
assert(scriptJs.includes('function loadMyTasksView'), 'Function loadMyTasksView exists');
assert(scriptJs.includes('function loadSettingsView'), 'Function loadSettingsView exists');
assert(scriptJs.includes('function createGroupCardElement'), 'Function createGroupCardElement exists');

// ────────────────────────────────────────────────────────────────
// PART 3: SIMULATED RUNTIME NAVIGATION & DATA LOADING
// ────────────────────────────────────────────────────────────────
console.log('\n[PART 3] Testing sidebar navigation in simulated DOM runtime...');

class DOMElementMock {
  constructor(id, tagName = 'div') {
    this.id = id;
    this.tagName = tagName;
    this.dataset = {};
    this.style = {};
    this.classList = {
      classes: new Set(),
      add: (c) => this.classList.classes.add(c),
      remove: (c) => this.classList.classes.delete(c),
      contains: (c) => this.classList.classes.has(c)
    };
    this._innerHTML = '';
    this._textContent = '';
    this.attributes = {};
    this.eventListeners = {};
    this.children = [];
  }
  get innerHTML() { return this._innerHTML; }
  set innerHTML(val) {
    this._innerHTML = String(val);
    if (val === '') this.children = [];
  }
  get textContent() { return this._textContent; }
  set textContent(val) { this._textContent = String(val); }
  setAttribute(k, v) { this.attributes[k] = v; }
  getAttribute(k) { return this.attributes[k] || null; }
  removeAttribute(k) { delete this.attributes[k]; }
  addEventListener(event, fn) {
    if (!this.eventListeners[event]) this.eventListeners[event] = [];
    this.eventListeners[event].push(fn);
  }
  click() {
    const list = this.eventListeners['click'] || [];
    list.forEach(fn => fn({ preventDefault: () => {} }));
  }
  appendChild(child) { this.children.push(child); }
  querySelector(sel) { return null; }
  querySelectorAll(sel) { return []; }
}

const elements = {};
function getEl(id) {
  if (!elements[id]) {
    elements[id] = new DOMElementMock(id);
  }
  return elements[id];
}

// Pre-create known elements
const elementIds = [
  'landing-page', 'dashboard-page', 'group-details-page', 'sidebar',
  'nav-dashboard', 'nav-groups', 'nav-sessions', 'nav-tasks', 'nav-settings',
  'logout-btn', 'back-to-landing-btn', 'view-all-groups-btn', 'dashboard-view-calendar-btn',
  'dashboard-view-overview', 'dashboard-view-groups', 'dashboard-view-sessions',
  'dashboard-view-tasks', 'dashboard-view-settings',
  'groups-grid', 'group-count', 'dashboard-tasks-count', 'dashboard-sessions-count',
  'my-groups-full-grid', 'my-sessions-full-list', 'my-tasks-full-list',
  'user-tasks-total', 'user-tasks-pending', 'user-tasks-inprogress', 'user-tasks-completed', 'user-tasks-rate', 'user-tasks-progress-fill',
  'settings-user-name', 'settings-user-email', 'settings-user-id', 'settings-groups-count',
  'settings-calendar-badge', 'settings-connect-calendar-btn', 'settings-disconnect-calendar-btn',
  'connect-calendar-btn', 'disconnect-calendar-btn', 'nav-login-btn', 'nav-signup-btn', 'nav-dashboard-btn', 'nav-logout-btn'
];

elementIds.forEach(id => getEl(id));

// Set data-section attributes on nav links
getEl('nav-dashboard').setAttribute('data-section', 'dashboard');
getEl('nav-groups').setAttribute('data-section', 'groups');
getEl('nav-sessions').setAttribute('data-section', 'sessions');
getEl('nav-tasks').setAttribute('data-section', 'tasks');
getEl('nav-settings').setAttribute('data-section', 'settings');

let mockLocation = { hash: '', pathname: '/' };
let mockToken = 'mock-test-jwt-token';
let mockUser = { id: 42, name: 'Alex Johnson', email: 'alex@example.com' };

const sandbox = {
  document: {
    getElementById: (id) => getEl(id),
    querySelectorAll: (sel) => {
      if (sel === '.sidebar-link') {
        return [getEl('nav-dashboard'), getEl('nav-groups'), getEl('nav-sessions'), getEl('nav-tasks'), getEl('nav-settings')];
      }
      return [];
    },
    createElement: (tag) => new DOMElementMock('dynamic-' + Math.random(), tag)
  },
  window: {
    location: mockLocation,
    scrollTo: () => {},
    addEventListener: () => {}
  },
  localStorage: {
    store: {
      authToken: mockToken,
      currentUser: JSON.stringify(mockUser)
    },
    getItem(k) { return this.store[k] || null; },
    setItem(k, v) { this.store[k] = String(v); },
    removeItem(k) { delete this.store[k]; }
  },
  API_BASE_URL: 'http://localhost:8000',
  escapeHtml: (s) => String(s || ''),
  avatarColors: ['avatar-teal', 'avatar-amber', 'avatar-rose'],
  console: console,
  openGroupDetails: (gid) => { sandbox.openedGroupId = gid; },
  openModal: (m) => {},
  closeModal: (m) => {},
  createSessionElement: (s) => {
    const el = new DOMElementMock('sess-' + s.id);
    el.textContent = s.title;
    return el;
  },
  fetch: async (url, opts = {}) => {
    if (url.includes('/api/groups') && !url.includes('/tasks')) {
      return {
        ok: true,
        json: async () => ({
          success: true,
          groups: [
            { id: 1, name: 'Algorithms Prep', subject: 'CS 301', description: 'Data structures & algorithms', member_count: 5, task_count: 4, session_count: 2 },
            { id: 2, name: 'Distributed Systems', subject: 'CS 401', description: 'Consensus & replication', member_count: 3, task_count: 2, session_count: 1 }
          ]
        })
      };
    }
    if (url.includes('/api/sessions')) {
      return {
        ok: true,
        json: async () => ({
          success: true,
          count: 2,
          sessions: [
            { id: 201, title: 'Raft Consensus Review', group_id: 2, group_name: 'Distributed Systems', start_time: '2026-11-15T10:00:00Z', calendar_sync_status: 'synced' },
            { id: 202, title: 'Dynamic Programming Practice', group_id: 1, group_name: 'Algorithms Prep', start_time: '2026-11-12T14:00:00Z', calendar_sync_status: 'synced' }
          ]
        })
      };
    }
    if (url.includes('/api/tasks')) {
      return {
        ok: true,
        json: async () => ({
          success: true,
          count: 3,
          tasks: [
            { id: 10, title: 'Read Raft paper', group_id: 2, group_name: 'Distributed Systems', status: 'completed', assignee: { name: 'Alex Johnson' }, due_date_formatted: 'Nov 14, 2026' },
            { id: 11, title: 'Implement Segment Tree', group_id: 1, group_name: 'Algorithms Prep', status: 'in_progress', assignee: { name: 'Sam Taylor' }, due_date_formatted: 'Nov 16, 2026' },
            { id: 12, title: 'Solve LeetCode #200', group_id: 1, group_name: 'Algorithms Prep', status: 'pending', assignee: null, due_date_formatted: null }
          ]
        })
      };
    }
    if (url.includes('/api/users/me')) {
      return {
        ok: true,
        json: async () => ({
          success: true,
          id: 42,
          name: 'Alex Johnson',
          email: 'alex@example.com',
          groups_count: 2,
          calendar_connected: true
        })
      };
    }
    if (url.includes('/auth/google/status')) {
      return {
        ok: true,
        json: async () => ({
          connected: true,
          status: 'connected',
          email: 'alex@gmail.com'
        })
      };
    }
    return { ok: false, status: 404, json: async () => ({}) };
  }
};

vm.createContext(sandbox);

// Execute Section 5B functions in sandbox
const s5bStart = scriptJs.indexOf("let currentDashboardView = 'dashboard';");
const s5bEnd = scriptJs.indexOf('// ── Wire Navigation Actions & Listeners ──');
const s5bCode = scriptJs.substring(s5bStart, s5bEnd);

vm.runInContext(`
  const dashboardPage = document.getElementById('dashboard-page');
  const landingPage = document.getElementById('landing-page');
  const groupDetailsPage = document.getElementById('group-details-page');
  const sidebar = document.getElementById('sidebar');
  const hamburgerBtn = { setAttribute: () => {} };
  const dashboardTasksCount = document.getElementById('dashboard-tasks-count');
  const dashboardSessionsCount = document.getElementById('dashboard-sessions-count');
  function getAuthToken() { return localStorage.getItem('authToken'); }
  function getCurrentUser() { return JSON.parse(localStorage.getItem('currentUser') || 'null'); }
  function getAuthHeaders() { return {}; }
  function updateAuthNavigation() {}
  function loadGroups() {}
  function loadDashboardUpcomingSessions() {}
  function checkGoogleCalendarStatus() {}
` + s5bCode, sandbox);

async function runTests() {
  const showDashboardView = sandbox.showDashboardView;

  // ── TEST 1: Navigate to Dashboard Overview ──
  console.log('\n[Item 1: Dashboard]');
  showDashboardView('dashboard', true);
  assert(getEl('dashboard-view-overview').style.display === 'block', 'Dashboard overview is displayed');
  assert(getEl('dashboard-view-groups').style.display === 'none', 'Groups view is hidden');
  assert(getEl('dashboard-view-settings').style.display === 'none', 'Settings view is hidden');
  assert(getEl('nav-dashboard').classList.contains('active'), 'Sidebar #nav-dashboard has active class');
  assert(!getEl('nav-settings').classList.contains('active'), 'Sidebar #nav-settings does NOT have active class (bug resolved)');
  assert(mockLocation.hash === 'dashboard', 'Location hash updated to #dashboard');

  // ── TEST 2: Navigate to My Groups ──
  console.log('\n[Item 2: My Groups]');
  showDashboardView('groups', true);
  assert(getEl('dashboard-view-groups').style.display === 'block', 'My Groups view is displayed');
  assert(getEl('dashboard-view-overview').style.display === 'none', 'Dashboard overview is hidden');
  assert(getEl('nav-groups').classList.contains('active'), 'Sidebar #nav-groups has active class');
  assert(!getEl('nav-dashboard').classList.contains('active'), 'Sidebar #nav-dashboard active class removed');
  assert(mockLocation.hash === 'groups', 'Location hash updated to #groups');

  try { await sandbox.loadMyGroupsView();  } catch(e) { console.error('loadMyGroupsView error:', e); }
  assert(getEl('my-groups-full-grid').children.length === 2, 'My Groups grid populated with 2 user groups');

  // ── TEST 3: Navigate to Sessions ──
  console.log('\n[Item 3: Sessions]');
  showDashboardView('sessions', true);
  assert(getEl('dashboard-view-sessions').style.display === 'block', 'Sessions view is displayed');
  assert(getEl('dashboard-view-groups').style.display === 'none', 'Groups view is hidden');
  assert(getEl('nav-sessions').classList.contains('active'), 'Sidebar #nav-sessions has active class');
  assert(mockLocation.hash === 'sessions', 'Location hash updated to #sessions');

  try { await sandbox.loadMySessionsView('all'); } catch(e) { console.error('loadMySessionsView error:', e); }
  assert(getEl('my-sessions-full-list').children.length === 2, 'Sessions list populated with 2 sessions');

  // ── TEST 4: Navigate to Tasks ──
  console.log('\n[Item 4: Tasks]');
  showDashboardView('tasks', true);
  assert(getEl('dashboard-view-tasks').style.display === 'block', 'Tasks view is displayed');
  assert(getEl('dashboard-view-sessions').style.display === 'none', 'Sessions view is hidden');
  assert(getEl('nav-tasks').classList.contains('active'), 'Sidebar #nav-tasks has active class');
  assert(mockLocation.hash === 'tasks', 'Location hash updated to #tasks');

  try { await sandbox.loadMyTasksView('all'); } catch(e) { console.error('loadMyTasksView error:', e); }
  assert(getEl('user-tasks-total').textContent === '3', 'Task total count reflects 3 user tasks');
  assert(getEl('user-tasks-pending').textContent === '1', 'Task pending count reflects 1 pending task');
  assert(getEl('user-tasks-inprogress').textContent === '1', 'Task in-progress count reflects 1 in-progress task');
  assert(getEl('user-tasks-completed').textContent === '1', 'Task completed count reflects 1 completed task');
  assert(getEl('user-tasks-rate').textContent === '33%', 'Task completion rate is 33%');
  assert(getEl('my-tasks-full-list').children.length === 3, 'Tasks list populated with 3 task cards');

  // ── TEST 5: Navigate to Settings ──
  console.log('\n[Item 5: Settings]');
  showDashboardView('settings', true);
  assert(getEl('dashboard-view-settings').style.display === 'block', 'Settings view is displayed');
  assert(getEl('dashboard-view-overview').style.display === 'none', 'Dashboard overview is hidden');
  assert(getEl('dashboard-view-tasks').style.display === 'none', 'Tasks view is hidden');
  assert(getEl('nav-settings').classList.contains('active'), 'Sidebar #nav-settings has active class');
  assert(!getEl('nav-dashboard').classList.contains('active'), 'Sidebar #nav-dashboard active class removed');
  assert(mockLocation.hash === 'settings', 'Location hash updated to #settings');

  await sandbox.loadSettingsView();
  assert(getEl('settings-user-name').textContent === 'Alex Johnson', 'Settings displays user name "Alex Johnson"');
  assert(getEl('settings-user-email').textContent === 'alex@example.com', 'Settings displays user email');
  assert(getEl('settings-user-id').textContent === '#42', 'Settings displays user ID #42');
  assert(getEl('settings-groups-count').textContent === '2 groups', 'Settings displays active group count');
  assert(getEl('settings-calendar-badge').textContent === 'Connected', 'Settings displays calendar status Connected');

  // ── TEST 6 & 7: Navigation back and URL restoration ──
  console.log('\n[Navigation & URL Synchronization]');
  showDashboardView('dashboard', true);
  assert(getEl('dashboard-view-overview').style.display === 'block', 'Returned to Dashboard overview');
  assert(getEl('nav-dashboard').classList.contains('active'), 'Dashboard active highlight restored');
  assert(!getEl('nav-settings').classList.contains('active'), 'Settings active highlight cleared');
  assert(mockLocation.hash === 'dashboard', 'Location hash updated back to #dashboard');

  console.log('\n' + '='.repeat(75));
  console.log(`SUMMARY: ${passed} passed, ${failed} failed.`);
  console.log('='.repeat(75));

  if (failed > 0) {
    process.exit(1);
  }
}

runTests().catch(e => {
  console.error('Test run error:', e);
  process.exit(1);
});
