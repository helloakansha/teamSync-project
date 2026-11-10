/**
 * TeamSync - Dynamic Landing Page & Dashboard Data Automated Test Suite
 * 
 * Verifies:
 * 1. Removal of all hardcoded demonstration data from index.html:
 *    - Platform stats (no "2,400+", "850+", "12,000+")
 *    - Floating cards (no "Binary Trees — by Priya", "DSA Study Session", etc.)
 *    - About cards (no "DSA Prep", "Web Development" with fabricated counts)
 *    - Dashboard welcome (no "Good morning, Akansha!")
 * 2. Complete removal of unused sampleSessions array from script.js.
 * 3. Frontend dynamic functionality:
 *    - formatStatCount helper
 *    - formatSessionBriefTime helper
 *    - loadPlatformStats DOM update
 *    - resetLandingDefaultData for logged-out / guest state
 *    - loadLandingPersonalizedData for authenticated users with data
 *    - loadLandingPersonalizedData for authenticated users with 0 data (empty states)
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
console.log('TEAMSYNC — DYNAMIC LANDING & DASHBOARD DATA VERIFICATION TEST SUITE');
console.log('='.repeat(75));

let testsPassed = 0;
let testsFailed = 0;

function assert(condition, message) {
  if (condition) {
    testsPassed++;
    console.log(`  ✓ ${message}`);
  } else {
    testsFailed++;
    console.error(`  ✗ FAIL: ${message}`);
  }
}

// ────────────────────────────────────────────────────────────────
// PART 1: HTML STATIC INSPECTION
// ────────────────────────────────────────────────────────────────
console.log('\n[PART 1] Inspecting frontend/index.html for hardcoded demonstration values...');

const indexPath = path.join(projectRoot, 'frontend', 'index.html');
const indexHtml = fs.readFileSync(indexPath, 'utf-8');

// Check 1: No fabricated hero statistics
assert(!indexHtml.includes('2,400+'), 'index.html does not contain hardcoded "2,400+"');
assert(!indexHtml.includes('850+'), 'index.html does not contain hardcoded "850+"');
assert(!indexHtml.includes('12,000+'), 'index.html does not contain hardcoded "12,000+"');

// Check 2: Dynamic stats element IDs exist
assert(indexHtml.includes('id="platform-students-count"'), 'Element #platform-students-count exists');
assert(indexHtml.includes('id="platform-groups-count"'), 'Element #platform-groups-count exists');
assert(indexHtml.includes('id="platform-sessions-count"'), 'Element #platform-sessions-count exists');

// Check 3: No fabricated demonstration cards in hero-visual
assert(!indexHtml.includes('Binary Trees — by Priya'), 'index.html does not contain hardcoded "Binary Trees — by Priya"');
assert(!indexHtml.includes('Today · 4:00 PM'), 'index.html does not contain hardcoded "Today · 4:00 PM"');
assert(!indexHtml.includes('3 members joined'), 'index.html does not contain hardcoded "3 members joined"');

// Check 4: Dynamic floating card IDs exist
assert(indexHtml.includes('id="hero-card-session-title"'), 'Element #hero-card-session-title exists');
assert(indexHtml.includes('id="hero-card-session-sub"'), 'Element #hero-card-session-sub exists');
assert(indexHtml.includes('id="hero-card-task-title"'), 'Element #hero-card-task-title exists');
assert(indexHtml.includes('id="hero-card-task-sub"'), 'Element #hero-card-task-sub exists');
assert(indexHtml.includes('id="hero-card-group-title"'), 'Element #hero-card-group-title exists');
assert(indexHtml.includes('id="hero-card-group-sub"'), 'Element #hero-card-group-sub exists');

// Check 5: No fabricated demo groups in about-visual
assert(!indexHtml.includes('DSA Prep'), 'index.html does not contain hardcoded "DSA Prep"');
assert(!indexHtml.includes('4 members · 3 tasks left'), 'index.html does not contain hardcoded "4 members · 3 tasks left"');
assert(!indexHtml.includes('6 members · 1 task left'), 'index.html does not contain hardcoded "6 members · 1 task left"');

// Check 6: Dynamic about card IDs exist
assert(indexHtml.includes('id="about-card-1-title"'), 'Element #about-card-1-title exists');
assert(indexHtml.includes('id="about-card-1-sub"'), 'Element #about-card-1-sub exists');
assert(indexHtml.includes('id="about-card-1-progress"'), 'Element #about-card-1-progress exists');
assert(indexHtml.includes('id="about-card-2-title"'), 'Element #about-card-2-title exists');
assert(indexHtml.includes('id="about-card-2-sub"'), 'Element #about-card-2-sub exists');
assert(indexHtml.includes('id="about-card-2-progress"'), 'Element #about-card-2-progress exists');

// Check 7: Dashboard welcome header is neutral
assert(!indexHtml.includes('Good morning, Akansha!'), 'index.html does not contain hardcoded "Good morning, Akansha!"');
assert(indexHtml.includes('id="dashboard-welcome">Welcome! 👋</h1>'), 'Dashboard welcome header defaults cleanly to "Welcome! 👋"');

// ────────────────────────────────────────────────────────────────
// PART 2: SCRIPT.JS STATIC INSPECTION
// ────────────────────────────────────────────────────────────────
console.log('\n[PART 2] Inspecting frontend/script.js for dead code and demo data...');

const scriptPath = path.join(projectRoot, 'frontend', 'script.js');
const scriptJs = fs.readFileSync(scriptPath, 'utf-8');

assert(!scriptJs.includes('sampleSessions ='), 'sampleSessions array has been removed from script.js');
assert(!scriptJs.includes('Java DSA — Binary Trees Deep Dive'), 'No demo session titles exist in script.js');
assert(scriptJs.includes('function formatStatCount'), 'Helper formatStatCount exists');
assert(scriptJs.includes('function formatSessionBriefTime'), 'Helper formatSessionBriefTime exists');
assert(scriptJs.includes('function loadPlatformStats'), 'Function loadPlatformStats exists');
assert(scriptJs.includes('function resetLandingDefaultData'), 'Function resetLandingDefaultData exists');
assert(scriptJs.includes('function loadLandingPersonalizedData'), 'Function loadLandingPersonalizedData exists');

// ────────────────────────────────────────────────────────────────
// PART 3: FRONTEND RUNTIME DYNAMIC BEHAVIOUR
// ────────────────────────────────────────────────────────────────
console.log('\n[PART 3] Testing dynamic helpers and DOM updates in simulated runtime...');

class DOMElementMock {
  constructor(id, tagName = 'div') {
    this.id = id;
    this.tagName = tagName;
    this.style = {};
    this.textContent = '';
    this.innerHTML = '';
  }
}

const mockElements = {
  'platform-students-count': new DOMElementMock('platform-students-count'),
  'platform-groups-count': new DOMElementMock('platform-groups-count'),
  'platform-sessions-count': new DOMElementMock('platform-sessions-count'),
  'hero-card-session-title': new DOMElementMock('hero-card-session-title'),
  'hero-card-session-sub': new DOMElementMock('hero-card-session-sub'),
  'hero-card-task-title': new DOMElementMock('hero-card-task-title'),
  'hero-card-task-sub': new DOMElementMock('hero-card-task-sub'),
  'hero-card-group-title': new DOMElementMock('hero-card-group-title'),
  'hero-card-group-sub': new DOMElementMock('hero-card-group-sub'),
  'about-card-1-title': new DOMElementMock('about-card-1-title'),
  'about-card-1-sub': new DOMElementMock('about-card-1-sub'),
  'about-card-1-progress': new DOMElementMock('about-card-1-progress'),
  'about-card-2-title': new DOMElementMock('about-card-2-title'),
  'about-card-2-sub': new DOMElementMock('about-card-2-sub'),
  'about-card-2-progress': new DOMElementMock('about-card-2-progress'),
  'dashboard-welcome': new DOMElementMock('dashboard-welcome')
};

// Create sandbox with mock environment
let mockAuthToken = null;
let mockFetchRoutes = {};

const sandbox = {
  document: {
    getElementById: (id) => mockElements[id] || null
  },
  API_BASE_URL: 'http://localhost:8000',
  getAuthToken: () => mockAuthToken,
  console: console,
  fetch: async (url, opts = {}) => {
    for (const [routePattern, handler] of Object.entries(mockFetchRoutes)) {
      if (url.includes(routePattern)) {
        return handler(url, opts);
      }
    }
    return { ok: false, status: 404, json: async () => ({}) };
  }
};

vm.createContext(sandbox);

// Extract the functions from script.js into sandbox
const functionsToExtract = [
  'formatStatCount',
  'formatSessionBriefTime',
  'loadPlatformStats',
  'resetLandingDefaultData',
  'loadLandingPersonalizedData'
];

// Run the script in VM to populate functions
// We can extract Section 2 code cleanly:
const normalizedScript = scriptJs.replace(/\r\n/g, '\n');
const s2Start = normalizedScript.indexOf('function formatStatCount');
const s2End = normalizedScript.indexOf('let currentGroupCount = 0;');
const section2Code = normalizedScript.substring(s2Start, s2End);
vm.runInContext(section2Code, sandbox);

// 3.1: formatStatCount helper test
const fsc = sandbox.formatStatCount;
assert(fsc(38) === '38', 'formatStatCount(38) returns "38"');
assert(fsc(1200) === '1,200', 'formatStatCount(1200) returns "1,200"');
assert(fsc(0) === '0', 'formatStatCount(0) returns "0"');
assert(fsc(null) === '0', 'formatStatCount(null) returns "0"');

// 3.2: formatSessionBriefTime helper test
const fsbt = sandbox.formatSessionBriefTime;
const today = new Date();
today.setHours(16, 0, 0, 0);
const todayFormatted = fsbt(today.toISOString());
assert(todayFormatted.startsWith('Today · '), `formatSessionBriefTime for today starts with "Today · " (got "${todayFormatted}")`);

const tomorrow = new Date();
tomorrow.setDate(tomorrow.getDate() + 1);
tomorrow.setHours(10, 30, 0, 0);
const tomorrowFormatted = fsbt(tomorrow.toISOString());
assert(tomorrowFormatted.startsWith('Tomorrow · '), `formatSessionBriefTime for tomorrow starts with "Tomorrow · " (got "${tomorrowFormatted}")`);

// 3.3: loadPlatformStats updates DOM elements
mockFetchRoutes['/api/platform/stats'] = async () => ({
  ok: true,
  json: async () => ({
    success: true,
    students_count: 38,
    groups_count: 19,
    sessions_count: 3
  })
});

async function testRuntime() {
  await sandbox.loadPlatformStats();
  assert(mockElements['platform-students-count'].textContent === '38', 'platform-students-count updated to "38"');
  assert(mockElements['platform-groups-count'].textContent === '19', 'platform-groups-count updated to "19"');
  assert(mockElements['platform-sessions-count'].textContent === '3', 'platform-sessions-count updated to "3"');

  // 3.4: resetLandingDefaultData (Logged-out state)
  sandbox.resetLandingDefaultData();
  assert(mockElements['hero-card-session-title'].textContent === 'Study Sessions', 'Logged-out session card title is "Study Sessions"');
  assert(mockElements['hero-card-session-sub'].textContent === 'Coordinate group schedules', 'Logged-out session card subtitle is neutral');
  assert(mockElements['hero-card-task-title'].textContent === 'Task Tracking', 'Logged-out task card title is "Task Tracking"');
  assert(mockElements['hero-card-task-sub'].textContent === 'Assign and complete topics', 'Logged-out task card subtitle is neutral');
  assert(mockElements['hero-card-group-title'].textContent === 'Group Collaboration', 'Logged-out group card title is "Group Collaboration"');
  assert(mockElements['about-card-1-title'].textContent === 'Structured Goals', 'Logged-out about card 1 is "Structured Goals"');
  assert(mockElements['about-card-2-title'].textContent === 'Shared Milestones', 'Logged-out about card 2 is "Shared Milestones"');

  // 3.5: loadLandingPersonalizedData (Logged-in with real data)
  mockAuthToken = 'valid.test.token';
  mockFetchRoutes['/api/sessions'] = async () => ({
    ok: true,
    json: async () => ({
      success: true,
      sessions: [
        {
          id: 101,
          title: 'Algorithms & Complexity',
          start_time: today.toISOString(),
          formatted_time: 'Today · 4:00 PM'
        }
      ]
    })
  });
  mockFetchRoutes['/api/groups/1/tasks'] = async () => ({
    ok: true,
    json: async () => ({
      success: true,
      tasks: [
        {
          id: 5,
          title: 'Graph Traversal Homework',
          status: 'completed',
          assignee: { name: 'Rohan Verma' }
        }
      ]
    })
  });
  mockFetchRoutes['/api/groups'] = async () => ({
    ok: true,
    json: async () => ({
      success: true,
      groups: [
        {
          id: 1,
          name: 'Computer Science Study Hub',
          member_count: 5,
          task_count: 8,
          pending_task_count: 2
        },
        {
          id: 2,
          name: 'Machine Learning Cohort',
          member_count: 8,
          task_count: 4,
          pending_task_count: 1
        }
      ]
    })
  });

  await sandbox.loadLandingPersonalizedData();

  assert(mockElements['hero-card-session-title'].textContent === 'Algorithms & Complexity', 'Personalized session title populated from database');
  assert(mockElements['hero-card-session-sub'].textContent.startsWith('Today · '), 'Personalized session time formatted dynamically');
  assert(mockElements['hero-card-group-title'].textContent === 'Computer Science Study Hub', 'Personalized group title populated from database');
  assert(mockElements['hero-card-group-sub'].textContent === '5 members', 'Personalized member count formatted dynamically');
  assert(mockElements['hero-card-task-title'].textContent === 'Task Completed', 'Personalized completed task title populated');
  assert(mockElements['hero-card-task-sub'].textContent === 'Graph Traversal Homework — by Rohan Verma', 'Personalized task title and real assignee populated');
  assert(mockElements['about-card-1-title'].textContent === 'Computer Science Study Hub', 'Personalized about card 1 shows real primary group');
  assert(mockElements['about-card-1-sub'].textContent === '5 members · 2 tasks left', 'Personalized about card 1 shows real member & pending task count');
  assert(mockElements['about-card-2-title'].textContent === 'Machine Learning Cohort', 'Personalized about card 2 shows real secondary group');
  assert(mockElements['about-card-2-sub'].textContent === '8 members · 1 task left', 'Personalized about card 2 shows real secondary member & task count');

  // 3.6: loadLandingPersonalizedData for user with 0 groups and 0 sessions
  mockFetchRoutes['/api/sessions'] = async () => ({
    ok: true,
    json: async () => ({ success: true, sessions: [] })
  });
  mockFetchRoutes['/api/groups'] = async () => ({
    ok: true,
    json: async () => ({ success: true, groups: [] })
  });

  await sandbox.loadLandingPersonalizedData();

  assert(mockElements['hero-card-session-title'].textContent === 'No upcoming sessions', 'Zero-session user sees "No upcoming sessions"');
  assert(mockElements['hero-card-session-sub'].textContent === 'Schedule one in your group', 'Zero-session user sees non-misleading prompt');
  assert(mockElements['hero-card-group-title'].textContent === 'Create your first group', 'Zero-group user sees "Create your first group"');
  assert(mockElements['hero-card-task-title'].textContent === 'No tasks yet', 'Zero-task user sees "No tasks yet"');
  assert(mockElements['about-card-1-title'].textContent === 'Create a Study Group', 'Zero-group about card 1 prompts creation');
  assert(mockElements['about-card-2-title'].textContent === 'Track Shared Tasks', 'Zero-group about card 2 prompts task tracking');

  console.log('\n' + '='.repeat(75));
  console.log(`SUMMARY: ${testsPassed} passed, ${testsFailed} failed.`);
  console.log('='.repeat(75));

  if (testsFailed > 0) {
    process.exit(1);
  }
}

testRuntime().catch((e) => {
  console.error('Test execution error:', e);
  process.exit(1);
});
