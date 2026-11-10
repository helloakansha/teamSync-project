/**

 * TeamSync — script.js

 * =====================

 * This file controls all the interactivity on the page:

 *   - Switching between the Landing Page and the Dashboard

 *   - Opening and closing modals

 *   - Form validation

 *   - Dynamically adding new study group cards to the dashboard

 *   - Rendering the upcoming sessions list from sample data

 *

 * We keep things simple and readable:

 *   - No frameworks, no build tools

 *   - Each feature is in its own clearly-labelled section

 *   - Comments explain the "why", not just the "what"

 */





/* ================================================================

   SECTION 1: GRAB ALL THE HTML ELEMENTS WE NEED

   We use getElementById / querySelector to find elements and save

   them in variables. This way we don't re-query the DOM every time.

================================================================ */





// FastAPI backend URL

const API_BASE_URL = "http://127.0.0.1:8000";



// ── Page containers ──

const landingPage = document.getElementById('landing-page');

const dashboardPage = document.getElementById('dashboard-page');

const groupDetailsPage = document.getElementById('group-details-page');



// ── Group Details Elements ──

const detailsBackBtn = document.getElementById('details-back-btn');

const detailsErrorBackBtn = document.getElementById('details-error-back-btn');

const groupDetailsLoading = document.getElementById('group-details-loading');

const groupDetailsError = document.getElementById('group-details-error');

const groupDetailsErrorTitle = document.getElementById('group-details-error-title');

const groupDetailsErrorMsg = document.getElementById('group-details-error-msg');

const groupDetailsContent = document.getElementById('group-details-content');

const detailAvatar = document.getElementById('detail-avatar');

const detailGroupName = document.getElementById('detail-group-name');

const detailGroupSubject = document.getElementById('detail-group-subject');

const detailGroupDesc = document.getElementById('detail-group-desc');

const detailMembersCount = document.getElementById('detail-members-count');

const detailMembersBadge = document.getElementById('detail-members-badge');

const detailMembersList = document.getElementById('detail-members-list');

const detailTasksCount = document.getElementById('detail-tasks-count');

const detailSessionsCount = document.getElementById('detail-sessions-count');

const detailSessionsList = document.getElementById('detail-sessions-list');

const inviteMembersBtn = document.getElementById('invite-members-btn');



// ── Study Group Tasks Elements ──

const addTaskBtn = document.getElementById('add-task-btn');

const createTaskModal = document.getElementById('create-task-modal');

const closeTaskModal = document.getElementById('close-task-modal');

const cancelTaskBtn = document.getElementById('cancel-task-btn');

const createTaskForm = document.getElementById('create-task-form');

const taskTitleInput = document.getElementById('task-title-input');

const taskTitleError = document.getElementById('task-title-error');

const taskDescInput = document.getElementById('task-desc-input');

const taskAssigneeSelect = document.getElementById('task-assignee-select');

const taskDueDateInput = document.getElementById('task-due-date-input');

const taskStatusSelect = document.getElementById('task-status-select');

const taskGeneralError = document.getElementById('task-general-error');

const submitTaskBtn = document.getElementById('submit-task-btn');



// ── Edit Task Elements ──

const editTaskModal = document.getElementById('edit-task-modal');

const closeEditTaskModal = document.getElementById('close-edit-task-modal');

const cancelEditTaskBtn = document.getElementById('cancel-edit-task-btn');

const editTaskForm = document.getElementById('edit-task-form');

const editTaskIdInput = document.getElementById('edit-task-id');

const editTaskTitleInput = document.getElementById('edit-task-title-input');

const editTaskTitleError = document.getElementById('edit-task-title-error');

const editTaskDescInput = document.getElementById('edit-task-desc-input');

const editTaskAssigneeSelect = document.getElementById('edit-task-assignee-select');

const editTaskDueDateInput = document.getElementById('edit-task-due-date-input');

const editTaskStatusSelect = document.getElementById('edit-task-status-select');

const editTaskGeneralError = document.getElementById('edit-task-general-error');

const submitEditTaskBtn = document.getElementById('submit-edit-task-btn');



// ── Schedule Study Session Elements ──

const addSessionBtn = document.getElementById('add-session-btn');

const detailSessionsBadge = document.getElementById('detail-sessions-badge');

const scheduleSessionModal = document.getElementById('schedule-session-modal');

const closeScheduleSessionModal = document.getElementById('close-schedule-session-modal');

const cancelScheduleSessionBtn = document.getElementById('cancel-schedule-session-btn');

const scheduleSessionForm = document.getElementById('schedule-session-form');

const sessionTitleInput = document.getElementById('session-title-input');

const sessionTitleError = document.getElementById('session-title-error');

const sessionDescInput = document.getElementById('session-desc-input');

const sessionDateInput = document.getElementById('session-date-input');

const sessionDateError = document.getElementById('session-date-error');

const sessionStartTimeInput = document.getElementById('session-start-time-input');

const sessionStartTimeError = document.getElementById('session-start-time-error');

const sessionEndTimeInput = document.getElementById('session-end-time-input');

const sessionEndTimeError = document.getElementById('session-end-time-error');

const sessionGeneralError = document.getElementById('session-general-error');

const submitScheduleSessionBtn = document.getElementById('submit-schedule-session-btn');



// ── Edit Study Session Elements ──

const editSessionModal = document.getElementById('edit-session-modal');

const closeEditSessionModal = document.getElementById('close-edit-session-modal');

const cancelEditSessionBtn = document.getElementById('cancel-edit-session-btn');

const editSessionForm = document.getElementById('edit-session-form');

const editSessionIdInput = document.getElementById('edit-session-id');

const editSessionTitleInput = document.getElementById('edit-session-title-input');

const editSessionTitleError = document.getElementById('edit-session-title-error');

const editSessionDescInput = document.getElementById('edit-session-desc-input');

const editSessionDateInput = document.getElementById('edit-session-date-input');

const editSessionDateError = document.getElementById('edit-session-date-error');

const editSessionStartTimeInput = document.getElementById('edit-session-start-time-input');

const editSessionStartTimeError = document.getElementById('edit-session-start-time-error');

const editSessionEndTimeInput = document.getElementById('edit-session-end-time-input');

const editSessionEndTimeError = document.getElementById('edit-session-end-time-error');

const editSessionGeneralError = document.getElementById('edit-session-general-error');

const submitEditSessionBtn = document.getElementById('submit-edit-session-btn');



// ── Cancel Study Session Elements ──

const cancelSessionModal = document.getElementById('cancel-session-modal');

const closeCancelSessionModal = document.getElementById('close-cancel-session-modal');

const keepSessionBtn = document.getElementById('keep-session-btn');

const confirmCancelSessionBtn = document.getElementById('confirm-cancel-session-btn');

const cancelSessionName = document.getElementById('cancel-session-name');

const cancelSessionTime = document.getElementById('cancel-session-time');

const cancelSessionGeneralError = document.getElementById('cancel-session-general-error');

let sessionToCancelId = null;



const tasksTotalBadge = document.getElementById('tasks-total-badge');

const statPendingCount = document.getElementById('stat-pending-count');

const statInprogressCount = document.getElementById('stat-inprogress-count');

const statCompletedCount = document.getElementById('stat-completed-count');

const statCompletionRate = document.getElementById('stat-completion-rate');

const taskProgressFill = document.getElementById('task-progress-fill');



const tabCountAll = document.getElementById('tab-count-all');

const tabCountPending = document.getElementById('tab-count-pending');

const tabCountInprogress = document.getElementById('tab-count-inprogress');

const tabCountCompleted = document.getElementById('tab-count-completed');

const detailTasksList = document.getElementById('detail-tasks-list');

const dashboardTasksCount = document.getElementById('dashboard-tasks-count');



let currentDetailsGroupId = null;

let currentTasks = [];

let currentTaskFilter = 'all';

let currentGroupMembers = [];

let currentGroupSessions = [];



// ── Buttons that switch between landing and dashboard ──

const getStartedBtn = document.getElementById('get-started-btn');

const navLoginBtn = document.getElementById('nav-login-btn');

const navSignupBtn = document.getElementById('nav-signup-btn');

const navDashboardBtn = document.getElementById('nav-dashboard-btn');

const navLogoutBtn = document.getElementById('nav-logout-btn');

const aboutCtaBtn = document.getElementById('about-cta-btn');

const backToLandingBtn = document.getElementById('back-to-landing-btn');



// ── Dashboard: Google Calendar Integration ──

const connectCalendarBtn = document.getElementById('connect-calendar-btn');

const disconnectCalendarBtn = document.getElementById('disconnect-calendar-btn');

const disconnectCalendarModal = document.getElementById('disconnect-calendar-modal');

const closeDisconnectCalendarModal = document.getElementById('close-disconnect-calendar-modal');

const cancelDisconnectCalendarBtn = document.getElementById('cancel-disconnect-calendar-btn');

const confirmDisconnectCalendarBtn = document.getElementById('confirm-disconnect-calendar-btn');

const disconnectCalendarError = document.getElementById('disconnect-calendar-error');



// ── Dashboard: Create Group ──

const createGroupBtn = document.getElementById('create-group-btn');

const createGroupModal = document.getElementById('create-group-modal');

const closeCreateModal = document.getElementById('close-create-modal');

const cancelCreateBtn = document.getElementById('cancel-create-btn');

const createGroupForm = document.getElementById('create-group-form');



// Create Group form fields and their error messages

const groupNameInput = document.getElementById('group-name-input');

const groupNameError = document.getElementById('group-name-error');

const groupSubjectInput = document.getElementById('group-subject-input');

const groupDescInput = document.getElementById('group-desc-input');

const groupDescError = document.getElementById('group-desc-error');



// ── Dashboard: Join Group ──

const joinGroupBtn = document.getElementById('join-group-btn');

const joinGroupModal = document.getElementById('join-group-modal');

const closeJoinModal = document.getElementById('close-join-modal');

const cancelJoinBtn = document.getElementById('cancel-join-btn');

const joinGroupForm = document.getElementById('join-group-form');



// Join Group form fields

const inviteCodeInput = document.getElementById('invite-code-input');

const inviteCodeError = document.getElementById('invite-code-error');

const joinGeneralError = document.getElementById('join-general-error');

const joinInfoNotice = document.getElementById('join-info-notice');

const joinSuccessNotice = document.getElementById('join-success-notice');

const joinSuccessText = document.getElementById('join-success-text');

const joinModalActions = document.getElementById('join-modal-actions');



// ── Invite Modal Elements ──

const inviteModal = document.getElementById('invite-modal');

const closeInviteModal = document.getElementById('close-invite-modal');

const closeInviteBtn = document.getElementById('close-invite-btn');

const inviteCodeVal = document.getElementById('invite-code-val');

const copyInviteCodeBtn = document.getElementById('copy-invite-code-btn');

const inviteLinkInput = document.getElementById('invite-link-input');

const copyInviteLinkBtn = document.getElementById('copy-invite-link-btn');

const inviteExpiryNote = document.getElementById('invite-expiry-note');

const inviteGeneralError = document.getElementById('invite-general-error');



// ── Dashboard: where new group cards are added ──

const groupsGrid = document.getElementById('groups-grid');

const groupCount = document.getElementById('group-count');



// ── Dashboard: sessions list container ──

const sessionsList = document.getElementById('sessions-list');

const dashboardSessionsCount = document.getElementById('dashboard-sessions-count');



// ── Mobile sidebar toggle ──

const hamburgerBtn = document.getElementById('hamburger-btn');

const sidebar = document.getElementById('sidebar');



// ── Sidebar nav links (to highlight the active one) ──

const sidebarLinks = document.querySelectorAll('.sidebar-link');



// ── Auth: Log In Elements ──

const loginModal = document.getElementById('login-modal');

const closeLoginModal = document.getElementById('close-login-modal');

const cancelLoginBtn = document.getElementById('cancel-login-btn');

const loginForm = document.getElementById('login-form');

const loginEmailInput = document.getElementById('login-email-input');

const loginEmailError = document.getElementById('login-email-error');

const loginPasswordInput = document.getElementById('login-password-input');

const loginPasswordError = document.getElementById('login-password-error');

const loginGeneralError = document.getElementById('login-general-error');

const switchToSignup = document.getElementById('switch-to-signup');



// ── Auth: Sign Up Elements ──

const signupModal = document.getElementById('signup-modal');

const closeSignupModal = document.getElementById('close-signup-modal');

const cancelSignupBtn = document.getElementById('cancel-signup-btn');

const signupForm = document.getElementById('signup-form');

const signupNameInput = document.getElementById('signup-name-input');

const signupNameError = document.getElementById('signup-name-error');

const signupEmailInput = document.getElementById('signup-email-input');

const signupEmailError = document.getElementById('signup-email-error');

const signupPasswordInput = document.getElementById('signup-password-input');

const signupPasswordError = document.getElementById('signup-password-error');

const signupGeneralError = document.getElementById('signup-general-error');

const switchToLogin = document.getElementById('switch-to-login');



// ── Dashboard User & Logout ──

const dashboardWelcome = document.getElementById('dashboard-welcome');

const logoutBtn = document.getElementById('logout-btn');





/* ================================================================

   SECTION 2: LANDING PAGE & PLATFORM DATA

   Dynamically fetches aggregate platform statistics and personalized

   data for authenticated users on the landing page.

================================================================ */



/**

 * Format a number cleanly for stats display.

 * @param {number|string} count

 * @returns {string}

 */

function formatStatCount(count) {

  if (count === null || count === undefined || isNaN(count)) return '0';

  return Number(count).toLocaleString();

}



/**

 * Format session start time for floating card display.

 * @param {string} isoString

 * @returns {string}

 */

function formatSessionBriefTime(isoString) {

  if (!isoString) return '';

  const d = new Date(isoString);

  if (isNaN(d.getTime())) return '';



  const now = new Date();

  const isToday = d.toDateString() === now.toDateString();

  const tomorrow = new Date(now);

  tomorrow.setDate(now.getDate() + 1);

  const isTomorrow = d.toDateString() === tomorrow.toDateString();



  const timeStr = d.toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' });

  if (isToday) {

    return `Today · ${timeStr}`;

  } else if (isTomorrow) {

    return `Tomorrow · ${timeStr}`;

  } else {

    const dateStr = d.toLocaleDateString([], { month: 'short', day: 'numeric' });

    return `${dateStr} · ${timeStr}`;

  }

}



/**

 * Loads platform-wide aggregate counts from GET /api/platform/stats

 * and updates the hero statistics in the landing page.

 */

async function loadPlatformStats() {

  const studentsEl = document.getElementById('platform-students-count');

  const groupsEl = document.getElementById('platform-groups-count');

  const sessionsEl = document.getElementById('platform-sessions-count');



  if (!studentsEl && !groupsEl && !sessionsEl) return;



  try {

    const response = await fetch(`${API_BASE_URL}/api/platform/stats`);

    if (!response.ok) return;

    const data = await response.json();

    if (data.success) {

      if (studentsEl) studentsEl.textContent = formatStatCount(data.students_count);

      if (groupsEl) groupsEl.textContent = formatStatCount(data.groups_count);

      if (sessionsEl) sessionsEl.textContent = formatStatCount(data.sessions_count);

    }

  } catch (err) {

    console.error('Failed to load platform stats:', err);

  }

}



/**

 * Resets landing page visual cards to neutral, non-fabricated platform descriptions.

 * Used when logged out or upon logout.

 */

function resetLandingDefaultData() {

  // Hero floating cards

  const sessionTitle = document.getElementById('hero-card-session-title');

  const sessionSub = document.getElementById('hero-card-session-sub');

  const taskTitle = document.getElementById('hero-card-task-title');

  const taskSub = document.getElementById('hero-card-task-sub');

  const groupTitle = document.getElementById('hero-card-group-title');

  const groupSub = document.getElementById('hero-card-group-sub');



  if (sessionTitle) sessionTitle.textContent = 'Study Sessions';

  if (sessionSub) sessionSub.textContent = 'Coordinate group schedules';

  if (taskTitle) taskTitle.textContent = 'Task Tracking';

  if (taskSub) taskSub.textContent = 'Assign and complete topics';

  if (groupTitle) groupTitle.textContent = 'Group Collaboration';

  if (groupSub) groupSub.textContent = 'Study together with peers';



  // About section cards

  const about1Title = document.getElementById('about-card-1-title');

  const about1Sub = document.getElementById('about-card-1-sub');

  const about1Prog = document.getElementById('about-card-1-progress');

  const about2Title = document.getElementById('about-card-2-title');

  const about2Sub = document.getElementById('about-card-2-sub');

  const about2Prog = document.getElementById('about-card-2-progress');



  if (about1Title) about1Title.textContent = 'Structured Goals';

  if (about1Sub) about1Sub.textContent = 'Track group progress collaboratively';

  if (about1Prog) about1Prog.style.width = '75%';



  if (about2Title) about2Title.textContent = 'Shared Milestones';

  if (about2Sub) about2Sub.textContent = 'Coordinate tasks and deadlines';

  if (about2Prog) about2Prog.style.width = '50%';

}



/**

 * Loads personalized cards for authenticated users on the landing page.

 * Uses real upcoming session, real group, and real task from PostgreSQL.

 */

async function loadLandingPersonalizedData() {

  const token = getAuthToken();

  if (!token) {

    resetLandingDefaultData();

    return;

  }



  const sessionTitle = document.getElementById('hero-card-session-title');

  const sessionSub = document.getElementById('hero-card-session-sub');

  const taskTitle = document.getElementById('hero-card-task-title');

  const taskSub = document.getElementById('hero-card-task-sub');

  const groupTitle = document.getElementById('hero-card-group-title');

  const groupSub = document.getElementById('hero-card-group-sub');



  const about1Title = document.getElementById('about-card-1-title');

  const about1Sub = document.getElementById('about-card-1-sub');

  const about1Prog = document.getElementById('about-card-1-progress');

  const about2Title = document.getElementById('about-card-2-title');

  const about2Sub = document.getElementById('about-card-2-sub');

  const about2Prog = document.getElementById('about-card-2-progress');



  try {

    // 1. Fetch user's upcoming sessions

    const sessionsRes = await fetch(`${API_BASE_URL}/api/sessions`, {

      headers: { 'Authorization': `Bearer ${token}` }

    });

    if (sessionsRes.ok) {

      const data = await sessionsRes.json();

      const sessions = data.sessions || [];

      if (sessions.length > 0) {

        const s = sessions[0];

        if (sessionTitle) sessionTitle.textContent = s.title || 'Study Session';

        if (sessionSub) sessionSub.textContent = formatSessionBriefTime(s.start_time) || (s.formatted_time || 'Upcoming');

      } else {

        if (sessionTitle) sessionTitle.textContent = 'No upcoming sessions';

        if (sessionSub) sessionSub.textContent = 'Schedule one in your group';

      }

    }



    // 2. Fetch user's groups

    const groupsRes = await fetch(`${API_BASE_URL}/api/groups`, {

      headers: { 'Authorization': `Bearer ${token}` }

    });

    if (groupsRes.ok) {

      const data = await groupsRes.json();

      const groups = data.groups || [];



      if (groups.length > 0) {

        // Group floating card

        const g0 = groups[0];

        const mCount = g0.member_count || g0.members_count || 1;

        if (groupTitle) groupTitle.textContent = g0.name;

        if (groupSub) groupSub.textContent = `${mCount} member${mCount === 1 ? '' : 's'}`;



        // About Card 1

        if (about1Title) about1Title.textContent = g0.name;

        const pTasks0 = g0.pending_task_count ?? 0;

        if (about1Sub) about1Sub.textContent = `${mCount} member${mCount === 1 ? '' : 's'} · ${pTasks0} task${pTasks0 === 1 ? '' : 's'} left`;

        if (about1Prog) {

          const tCount0 = g0.task_count ?? 0;

          const completed0 = Math.max(0, tCount0 - pTasks0);

          const pct0 = tCount0 > 0 ? Math.round((completed0 / tCount0) * 100) : 0;

          about1Prog.style.width = `${pct0}%`;

        }



        // About Card 2

        if (groups.length > 1) {

          const g1 = groups[1];

          const mCount1 = g1.member_count || g1.members_count || 1;

          const pTasks1 = g1.pending_task_count ?? 0;

          if (about2Title) about2Title.textContent = g1.name;

          if (about2Sub) about2Sub.textContent = `${mCount1} member${mCount1 === 1 ? '' : 's'} · ${pTasks1} task${pTasks1 === 1 ? '' : 's'} left`;

          if (about2Prog) {

            const tCount1 = g1.task_count ?? 0;

            const completed1 = Math.max(0, tCount1 - pTasks1);

            const pct1 = tCount1 > 0 ? Math.round((completed1 / tCount1) * 100) : 0;

            about2Prog.style.width = `${pct1}%`;

          }

        } else {

          if (about2Title) about2Title.textContent = 'Create Another Group';

          if (about2Sub) about2Sub.textContent = 'Add more subjects & members';

          if (about2Prog) about2Prog.style.width = '0%';

        }



        // 3. Fetch tasks for user's primary group to display a real task card

        try {

          const tasksRes = await fetch(`${API_BASE_URL}/api/groups/${g0.id}/tasks`, {

            headers: { 'Authorization': `Bearer ${token}` }

          });

          if (tasksRes.ok) {

            const taskData = await tasksRes.json();

            const tasks = taskData.tasks || [];

            const completedTask = tasks.find(t => (t.status || '').toLowerCase() === 'completed');

            const anyTask = completedTask || tasks[0];



            if (completedTask) {

              if (taskTitle) taskTitle.textContent = 'Task Completed';

              const assigneeName = completedTask.assignee?.name || completedTask.creator_name || '';

              if (taskSub) taskSub.textContent = `${completedTask.title}${assigneeName ? ` — by ${assigneeName}` : ''}`;

            } else if (anyTask) {

              const statusLabel = (anyTask.status || 'pending').replace('_', ' ');

              if (taskTitle) taskTitle.textContent = anyTask.title;

              if (taskSub) taskSub.textContent = `Status: ${statusLabel}`;

            } else {

              if (taskTitle) taskTitle.textContent = 'No tasks yet';

              if (taskSub) taskSub.textContent = 'Add tasks to keep track';

            }

          }

        } catch (taskErr) {

          console.error('Failed to load group tasks for hero card:', taskErr);

        }

      } else {

        // User has 0 groups

        if (groupTitle) groupTitle.textContent = 'Create your first group';

        if (groupSub) groupSub.textContent = 'Collaborate with peers';

        if (taskTitle) taskTitle.textContent = 'No tasks yet';

        if (taskSub) taskSub.textContent = 'Join or create a study group';



        if (about1Title) about1Title.textContent = 'Create a Study Group';

        if (about1Sub) about1Sub.textContent = 'Invite peers and share notes';

        if (about1Prog) about1Prog.style.width = '0%';



        if (about2Title) about2Title.textContent = 'Track Shared Tasks';

        if (about2Sub) about2Sub.textContent = 'Stay on top of deadlines';

        if (about2Prog) about2Prog.style.width = '0%';

      }

    }

  } catch (err) {

    console.error('Failed to load personalized landing data:', err);

  }

}





/**

 * Tracks how many groups currently exist on the dashboard.

 * Starts at 0 and is populated dynamically from PostgreSQL.

 */

let currentGroupCount = 0;



/**

 * A list of avatar color classes to cycle through when

 * creating new group cards. This keeps things visually varied.

 */

const avatarColors = [

  'avatar-teal',

  'avatar-amber',

  'avatar-rose',

  'avatar-green',

  'avatar-purple',

  'avatar-indigo'

];



// Tracks which color to use next (cycles back to 0 at end)

let nextAvatarColorIndex = 2; // Start at index 2 so new groups differ from the sample ones





/* ================================================================

   SECTION 3: PAGE NAVIGATION (Landing ↔ Dashboard)

   We show/hide entire pages by toggling a CSS class called 'active'.

   The CSS rule `.page { display: none }` hides pages by default,

   and `.page.active { display: block }` makes them visible.

================================================================ */



/**

 * Show the dashboard and hide the landing page.

 * Called when the user clicks "Get Started", "Log In", etc.

 */

function showDashboard(view = 'dashboard') {
  landingPage.classList.remove('active');
  if (groupDetailsPage) groupDetailsPage.classList.remove('active');
  dashboardPage.classList.add('active');
  updateAuthNavigation();
  showDashboardView(view, true);
  if (typeof window !== 'undefined' && typeof window.scrollTo === 'function') {
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }
}



/**

 * Show the landing page and hide the dashboard.

 * Called when the user clicks "← Back to Home".

 */

function showLanding() {

  dashboardPage.classList.remove('active');

  if (groupDetailsPage) groupDetailsPage.classList.remove('active');

  landingPage.classList.add('active');

  updateAuthNavigation();

  window.scrollTo({ top: 0, behavior: 'smooth' });



  const user = getCurrentUser();

  const token = getAuthToken();

  if (user && token) {

    loadLandingPersonalizedData();

  } else {

    resetLandingDefaultData();

  }

}



/**

 * Opens the dedicated Group Details page and fetches the group from FastAPI.

 * @param {number|string} groupId - The database ID of the group

 */

async function openGroupDetails(groupId) {

  currentDetailsGroupId = groupId;

  landingPage.classList.remove('active');

  dashboardPage.classList.remove('active');

  if (groupDetailsPage) groupDetailsPage.classList.add('active');

  window.scrollTo({ top: 0, behavior: 'smooth' });



  // Show loading spinner, hide previous content or error

  groupDetailsLoading.removeAttribute('hidden');

  groupDetailsContent.setAttribute('hidden', '');

  groupDetailsError.setAttribute('hidden', '');



  try {

    const response = await fetch(`${API_BASE_URL}/api/groups/${groupId}`, {

      headers: getAuthHeaders(false)

    });



    if (!response.ok) {

      groupDetailsLoading.setAttribute('hidden', '');

      groupDetailsContent.setAttribute('hidden', '');

      groupDetailsError.removeAttribute('hidden');



      if (response.status === 401) {

        localStorage.removeItem('currentUser');

        localStorage.removeItem('authToken');

        updateAuthNavigation();

        groupDetailsErrorTitle.textContent = "Authentication Required";

        groupDetailsErrorMsg.textContent = "Your session has expired or you are not logged in. Please sign in to view this study group.";

      } else if (response.status === 403) {

        const errData = await response.json().catch(() => ({}));

        groupDetailsErrorTitle.textContent = "Access Denied";

        groupDetailsErrorMsg.textContent = errData.detail || "You are not a member of this study group. Please join using an invitation code.";

      } else {

        groupDetailsErrorTitle.textContent = "Study Group Not Found";

        groupDetailsErrorMsg.textContent = `Could not find a study group with ID #${groupId}. It may have been deleted or does not exist.`;

      }

      return;

    }



    const data = await response.json();

    const group = data.group;



    if (!group) {

      throw new Error("Invalid response format");

    }



    // Populate Group Info

    detailGroupName.textContent = group.name;

    detailGroupSubject.textContent = group.subject ? `📚 ${group.subject}` : `📚 ${group.name}`;

    detailGroupDesc.textContent = group.description || "No description provided.";



    // Avatar initials

    const words = group.name.trim().split(' ');

    const initials = words.length >= 2

      ? words[0][0].toUpperCase() + words[1][0].toUpperCase()

      : words[0].slice(0, 2).toUpperCase();

    detailAvatar.textContent = initials;



    // Numerical stats

    const members = group.members || [];

    currentGroupMembers = members;

    const membersCount = group.members_count !== undefined ? group.members_count : members.length;

    detailMembersCount.textContent = membersCount;

    if (detailMembersBadge) {

      detailMembersBadge.textContent = `${membersCount} ${membersCount === 1 ? 'member' : 'members'}`;

    }

    detailTasksCount.textContent = group.tasks_count || 0;

    const sessions = group.sessions || [];

    currentGroupSessions = sessions;

    if (detailSessionsCount) detailSessionsCount.textContent = sessions.length;

    if (detailSessionsBadge) {

      detailSessionsBadge.textContent = `${sessions.length} ${sessions.length === 1 ? 'session' : 'sessions'}`;

    }



    // Determine current logged-in user and group owner permissions

    const currentUser = getCurrentUser();

    const currentUserId = currentUser ? Number(currentUser.id) : null;

    const ownerMember = members.find(m => (m.role || "").toLowerCase() === "owner");

    const ownerUserId = ownerMember ? Number(ownerMember.id) : null;

    const isGroupOwner = (currentUserId !== null && ownerUserId !== null && currentUserId === ownerUserId);



    // Render Upcoming Sessions

    if (detailSessionsList) {

      detailSessionsList.innerHTML = '';

      if (sessions.length === 0) {

        detailSessionsList.innerHTML = `

          <div class="details-empty-sessions">

            <p>🗓️ No upcoming sessions scheduled for this group yet.</p>

          </div>

        `;

      } else {

        sessions.forEach(session => {

          const item = document.createElement('div');

          item.classList.add('session-item');

          const formattedTime = session.formatted_time || session.time || "Scheduled session";

          const descHtml = session.description ? `<p class="session-desc" style="font-size: 12px; color: var(--color-text-muted); margin-top: 4px; line-height: 1.4;">${escapeHtml(session.description)}</p>` : '';

          const tagHtml = getSessionSyncTagHtml(session);



          // Show Edit and Cancel buttons only if user is session creator or group owner

          const isCreator = (currentUserId !== null && session.created_by !== null && currentUserId === Number(session.created_by));

          const canEdit = isCreator || isGroupOwner;



          const retryBtnHtml = (canEdit && isEligibleForSyncRetry(session))

            ? `<button class="session-retry-btn" data-session-id="${session.id}" title="Retry Google Calendar sync">🔄 Retry Sync</button>`

            : '';



          const actionsHtml = canEdit ? `

            <div class="session-actions" style="display: flex; align-items: center; gap: 8px; flex-shrink: 0; margin-left: 8px;">

              ${retryBtnHtml}

              <button class="session-edit-btn" data-session-id="${session.id}" title="Edit study session">✏️ Edit</button>

              <button class="session-cancel-btn" data-session-id="${session.id}" title="Cancel study session">🗑️ Cancel</button>

            </div>

          ` : '';



          item.innerHTML = `

            <div class="session-time-block">

              <p class="session-day">${escapeHtml(session.day || "UPC")}</p>

              <p class="session-date">${escapeHtml(session.date || "--")}</p>

            </div>

            <div class="session-divider"></div>

            <div class="session-info">

              <p class="session-title">${escapeHtml(session.title)}</p>

              <p class="session-meta">🕐 ${escapeHtml(formattedTime)}${session.creator_name ? ` &nbsp;•&nbsp; 👤 ${escapeHtml(session.creator_name)}` : ''}</p>

              ${descHtml}

            </div>

            ${tagHtml}

            ${actionsHtml}

          `;

          detailSessionsList.appendChild(item);

        });

      }

    }



    // Render Group Members

    if (detailMembersList) {

      detailMembersList.innerHTML = '';

      if (members.length === 0) {

        detailMembersList.innerHTML = `

          <div class="details-empty-members">

            <p>👥 No members have joined this group yet.</p>

          </div>

        `;

      } else {

        members.forEach((m, idx) => {

          const mCard = document.createElement('div');

          mCard.classList.add('member-card');

          const mName = m.name || "Unknown Member";

          const mWords = mName.trim().split(' ');

          const mInitials = mWords.length >= 2

            ? mWords[0][0].toUpperCase() + mWords[1][0].toUpperCase()

            : mWords[0].slice(0, 2).toUpperCase();

          const mAvatarColor = avatarColors[idx % avatarColors.length];

          const isOwner = (m.role || "").toLowerCase() === "owner";

          const roleLabel = isOwner ? "Owner" : "Member";

          const roleClass = isOwner ? "role-owner" : "role-member";

          const joinedDate = m.joined_at ? `Joined ${escapeHtml(m.joined_at)}` : "Member";



          mCard.innerHTML = `

            <div class="member-avatar ${mAvatarColor}">${escapeHtml(mInitials)}</div>

            <div class="member-info">

              <p class="member-name" title="${escapeHtml(mName)}">${escapeHtml(mName)}</p>

              <p class="member-joined">${escapeHtml(joinedDate)}</p>

            </div>

            <span class="member-role-badge ${roleClass}">${roleLabel}</span>

          `;

          detailMembersList.appendChild(mCard);

        });

      }

    }



    // Store and render Tasks & Task Statistics

    currentTasks = group.tasks || [];

    currentGroupMembers = members;

    populateTaskAssigneeDropdown(currentGroupMembers);

    renderTaskStats(group.task_stats || {});

    resetTaskFilterTabs();

    renderTasks(currentTasks, currentTaskFilter);



    // Display content

    groupDetailsLoading.setAttribute('hidden', '');

    groupDetailsError.setAttribute('hidden', '');

    groupDetailsContent.removeAttribute('hidden');



  } catch (error) {

    console.error("Error loading group details:", error);

    groupDetailsLoading.setAttribute('hidden', '');

    groupDetailsContent.setAttribute('hidden', '');

    groupDetailsError.removeAttribute('hidden');

    groupDetailsErrorTitle.textContent = "Unable to Load Group";

    groupDetailsErrorMsg.textContent = "Could not connect to the backend server. Please make sure FastAPI is running.";

  }

}



function decodeJwtPayload(token) {

  try {

    const parts = token.split('.');

    if (parts.length !== 3) return null;

    const b64 = parts[1].replace(/-/g, '+').replace(/_/g, '/');

    const json = atob(b64);

    return JSON.parse(json);

  } catch (err) {

    return null;

  }

}



function isTokenExpired(token) {

  if (!token) return true;

  const payload = decodeJwtPayload(token);

  if (!payload) return true;

  if (payload.exp && (Date.now() / 1000) >= payload.exp) {

    return true;

  }

  return false;

}



function getCurrentUser() {

  const token = getAuthToken();

  if (!token) {

    return null;

  }

  try {

    const userStr = localStorage.getItem('currentUser');

    return userStr ? JSON.parse(userStr) : null;

  } catch (e) {

    return null;

  }

}



function getAuthToken() {

  const token = localStorage.getItem('authToken') || '';

  if (token && isTokenExpired(token)) {

    localStorage.removeItem('currentUser');

    localStorage.removeItem('authToken');

    updateAuthNavigation();

    return '';

  }

  return token;

}



function getAuthHeaders(includeJson = true) {

  const headers = {};

  if (includeJson) {

    headers['Content-Type'] = 'application/json';

  }

  const token = getAuthToken();

  if (token) {

    headers['Authorization'] = `Bearer ${token}`;

  }

  return headers;

}



function updateDashboardUser(user) {

  if (dashboardWelcome) {

    const name = user && user.name ? user.name : 'Student';

    dashboardWelcome.textContent = `Welcome, ${name}! 👋`;

  }

}



/**

 * Updates navigation bar elements according to current authentication state.

 * When authenticated: hides Log In / Sign Up, shows Dashboard / Log Out.

 * When logged out: shows Log In / Sign Up, hides Dashboard / Log Out.

 */

function updateAuthNavigation() {

  const token = localStorage.getItem('authToken') || '';

  const userStr = localStorage.getItem('currentUser');

  let authenticated = false;



  if (token && userStr && !isTokenExpired(token)) {

    authenticated = true;

  }



  const loginBtn = document.getElementById('nav-login-btn');

  const signupBtn = document.getElementById('nav-signup-btn');

  const dashboardBtn = document.getElementById('nav-dashboard-btn');

  const logoutNavBtn = document.getElementById('nav-logout-btn');



  if (loginBtn) loginBtn.style.display = authenticated ? 'none' : '';

  if (signupBtn) signupBtn.style.display = authenticated ? 'none' : '';

  if (dashboardBtn) dashboardBtn.style.display = authenticated ? '' : 'none';

  if (logoutNavBtn) logoutNavBtn.style.display = authenticated ? '' : 'none';

}



function handleLogout() {

  localStorage.removeItem('currentUser');

  localStorage.removeItem('authToken');

  if (connectCalendarBtn) {

    connectCalendarBtn.innerHTML = '📅 Connect Google Calendar';

    connectCalendarBtn.disabled = false;

    connectCalendarBtn.classList.remove('btn-connected', 'btn-reconnect');

  }

  if (disconnectCalendarBtn) {

    disconnectCalendarBtn.style.display = 'none';

  }

  // Clear user-specific groups from the dashboard DOM

  groupsGrid.innerHTML = '';

  currentGroupCount = 0;

  if (groupCount) {

    groupCount.textContent = '0';

  }

  if (sessionsList) {

    sessionsList.innerHTML = '';

  }

  if (dashboardSessionsCount) {

    dashboardSessionsCount.textContent = '0';

  }

  if (dashboardWelcome) {

    dashboardWelcome.textContent = "Welcome! 👋";
  }
  currentDashboardView = 'dashboard';
  const subviewList = [
    document.getElementById('dashboard-view-overview'),
    document.getElementById('dashboard-view-groups'),
    document.getElementById('dashboard-view-sessions'),
    document.getElementById('dashboard-view-tasks'),
    document.getElementById('dashboard-view-settings')
  ];
  subviewList.forEach(el => {
    if (el) {
      el.style.display = 'none';
      el.classList.remove('active');
    }
  });
  if (subviewList[0]) {
    subviewList[0].style.display = 'block';
    subviewList[0].classList.add('active');
  }
  const allNavLinks = document.querySelectorAll('.sidebar-link');
  allNavLinks.forEach(l => l.classList.remove('active'));
  const dLink = document.getElementById('nav-dashboard');
  if (dLink) dLink.classList.add('active');
  window.location.hash = '';

  resetLandingDefaultData();
  updateAuthNavigation();
  showLanding();

}



// Wire up auth buttons

navLoginBtn.addEventListener('click', function () {

  const user = getCurrentUser();

  if (user) {

    updateDashboardUser(user);

    showDashboard();

  } else {

    openModal(loginModal);

  }

});



function handleSignupCta() {

  const user = getCurrentUser();

  if (user) {

    updateDashboardUser(user);

    showDashboard();

  } else {

    openModal(signupModal);

  }

}



getStartedBtn.addEventListener('click', handleSignupCta);

navSignupBtn.addEventListener('click', handleSignupCta);

aboutCtaBtn.addEventListener('click', handleSignupCta);



if (navDashboardBtn) {

  navDashboardBtn.addEventListener('click', function () {

    showDashboard();

  });

}



if (navLogoutBtn) {

  navLogoutBtn.addEventListener('click', handleLogout);

}



// Wire up the "back to landing" button in the sidebar

backToLandingBtn.addEventListener('click', showLanding);



// Wire up Back to Dashboard buttons on the details page

if (detailsBackBtn) {
  detailsBackBtn.addEventListener('click', function () {
    if (groupDetailsPage) groupDetailsPage.classList.remove('active');
    showDashboardView(currentDashboardView || 'dashboard', true);
  });
}
if (detailsErrorBackBtn) {
  detailsErrorBackBtn.addEventListener('click', function () {
    if (groupDetailsPage) groupDetailsPage.classList.remove('active');
    showDashboardView(currentDashboardView || 'dashboard', true);
  });
}



/**

 * Checks whether the logged-in user has connected their Google Calendar.

 * Updates the dashboard calendar button state dynamically.

 */

async function checkGoogleCalendarStatus() {

  if (!connectCalendarBtn) return;

  const token = localStorage.getItem('authToken');

  if (!token) {

    connectCalendarBtn.innerHTML = '📅 Connect Google Calendar';

    connectCalendarBtn.disabled = false;

    connectCalendarBtn.title = 'Connect your Google Calendar to sync study sessions';

    connectCalendarBtn.classList.remove('btn-connected', 'btn-reconnect');

    if (disconnectCalendarBtn) disconnectCalendarBtn.style.display = 'none';

    return;

  }



  try {

    const response = await fetch(`${API_BASE_URL}/auth/google/status`, {

      method: 'GET',

      headers: {

        'Authorization': `Bearer ${token}`

      }

    });



    if (response.ok) {

      const data = await response.json();

      if (data && data.requires_reconnect) {

        // Credentials expired without refresh or were revoked

        connectCalendarBtn.innerHTML = '⚠️ Reconnect Google Calendar';

        connectCalendarBtn.disabled = false;

        connectCalendarBtn.title = data.message || 'Google authorization expired. Click to reconnect.';

        connectCalendarBtn.classList.add('btn-reconnect');

        connectCalendarBtn.classList.remove('btn-connected');

        if (disconnectCalendarBtn) disconnectCalendarBtn.style.display = 'inline-flex';

      } else if (data && data.connected) {

        // Connected and healthy

        connectCalendarBtn.innerHTML = '✅ Google Calendar Connected';

        connectCalendarBtn.disabled = true;

        connectCalendarBtn.title = 'Your Google Calendar is connected';

        connectCalendarBtn.classList.add('btn-connected');

        connectCalendarBtn.classList.remove('btn-reconnect');

        if (disconnectCalendarBtn) disconnectCalendarBtn.style.display = 'inline-flex';

      } else {

        // Disconnected

        connectCalendarBtn.innerHTML = '📅 Connect Google Calendar';

        connectCalendarBtn.disabled = false;

        connectCalendarBtn.title = 'Connect your Google Calendar to sync study sessions';

        connectCalendarBtn.classList.remove('btn-connected', 'btn-reconnect');

        if (disconnectCalendarBtn) disconnectCalendarBtn.style.display = 'none';

      }

    }

  } catch (err) {

    console.error('Failed to check Google Calendar connection status:', err);

  }

}



// Wire up Disconnect Google Calendar modal actions

if (disconnectCalendarBtn) {

  disconnectCalendarBtn.addEventListener('click', function () {

    if (disconnectCalendarError) disconnectCalendarError.textContent = '';

    openModal(disconnectCalendarModal);

  });

}



if (closeDisconnectCalendarModal) {

  closeDisconnectCalendarModal.addEventListener('click', function () {

    closeModal(disconnectCalendarModal);

  });

}



if (cancelDisconnectCalendarBtn) {

  cancelDisconnectCalendarBtn.addEventListener('click', function () {

    closeModal(disconnectCalendarModal);

  });

}



if (confirmDisconnectCalendarBtn) {

  confirmDisconnectCalendarBtn.addEventListener('click', async function () {

    const token = localStorage.getItem('authToken');

    if (!token) {

      closeModal(disconnectCalendarModal);

      openModal(loginModal);

      return;

    }



    const originalText = confirmDisconnectCalendarBtn.textContent;

    confirmDisconnectCalendarBtn.disabled = true;

    confirmDisconnectCalendarBtn.textContent = 'Disconnecting...';

    if (disconnectCalendarError) disconnectCalendarError.textContent = '';



    try {

      const response = await fetch(`${API_BASE_URL}/auth/google/disconnect`, {

        method: 'POST',

        headers: {

          'Authorization': `Bearer ${token}`

        }

      });



      confirmDisconnectCalendarBtn.disabled = false;

      confirmDisconnectCalendarBtn.textContent = originalText;



      const data = await response.json().catch(() => ({}));



      if (!response.ok) {

        if (disconnectCalendarError) {

          disconnectCalendarError.textContent = data.detail || 'Could not disconnect Google Calendar. Please try again.';

        }

        return;

      }



      // Close modal and refresh connection state

      closeModal(disconnectCalendarModal);

      await checkGoogleCalendarStatus();

      alert('Google Calendar has been disconnected. Existing study sessions remain in TeamSync.');



    } catch (err) {

      console.error('Error disconnecting Google Calendar:', err);

      confirmDisconnectCalendarBtn.disabled = false;

      confirmDisconnectCalendarBtn.textContent = originalText;

      if (disconnectCalendarError) {

        disconnectCalendarError.textContent = 'Connection error. Please check if the server is running.';

      }

    }

  });

}



// Wire up Connect Google Calendar button

if (connectCalendarBtn) {

  connectCalendarBtn.addEventListener('click', async function () {

    const token = localStorage.getItem('authToken');



    // Check for existing login token

    if (!token) {

      alert('Please log in or create an account first to connect your Google Calendar.');

      openModal(loginModal);

      return;

    }



    // Show loading state while request is in progress

    const originalHtml = connectCalendarBtn.innerHTML;

    connectCalendarBtn.disabled = true;

    connectCalendarBtn.innerHTML = '⏳ Connecting...';



    try {

      // Pass the current page URL so the backend redirects directly back here after Google auth

      const currentUrl = window.location.href.split('?')[0].split('#')[0];

      const connectUrl = `${API_BASE_URL}/auth/google/connect?return_url=${encodeURIComponent(currentUrl)}`;



      const response = await fetch(connectUrl, {

        method: 'GET',

        headers: {

          'Authorization': `Bearer ${token}`

        }

      });



      const data = await response.json().catch(() => ({}));



      if (!response.ok) {

        connectCalendarBtn.disabled = false;

        connectCalendarBtn.innerHTML = originalHtml;



        if (response.status === 401) {

          alert('Your session has expired. Please log in again to connect Google Calendar.');

          openModal(loginModal);

        } else {

          alert(data.detail || 'Failed to connect Google Calendar. Please verify Google OAuth credentials are configured.');

        }

        return;

      }



      if (data && data.authorization_url) {

        connectCalendarBtn.innerHTML = '🔄 Redirecting...';

        window.location.href = data.authorization_url;

      } else {

        connectCalendarBtn.disabled = false;

        connectCalendarBtn.innerHTML = originalHtml;

        alert('Could not retrieve Google Calendar authorization URL. Please try again.');

      }



    } catch (err) {

      console.error('Error connecting Google Calendar:', err);

      connectCalendarBtn.disabled = false;

      connectCalendarBtn.innerHTML = originalHtml;

      alert('Unable to connect to the backend server. Please verify FastAPI is running on port 8000.');

    }

  });

}



// Wire up logout button in sidebar

if (logoutBtn) {

  logoutBtn.addEventListener('click', handleLogout);

}





/* ================================================================

   SECTION 4: MOBILE SIDEBAR TOGGLE

   On small screens the sidebar is hidden off-screen.

   The hamburger button slides it in/out using a CSS class.

================================================================ */



hamburgerBtn.addEventListener('click', function () {

  // Toggle the 'open' class — CSS handles the slide animation

  sidebar.classList.toggle('open');



  // Update aria-expanded for accessibility (screen readers)

  const isOpen = sidebar.classList.contains('open');

  hamburgerBtn.setAttribute('aria-expanded', isOpen);

});



/**

 * Close the sidebar when the user clicks anywhere outside of it.

 * This is a common UX pattern for mobile drawers.

 */

document.addEventListener('click', function (event) {

  const clickedOutsideSidebar = !sidebar.contains(event.target);

  const clickedOutsideHamburger = !hamburgerBtn.contains(event.target);



  if (sidebar.classList.contains('open') && clickedOutsideSidebar && clickedOutsideHamburger) {

    sidebar.classList.remove('open');

    hamburgerBtn.setAttribute('aria-expanded', false);

  }

});



/**

 * Sidebar nav link highlighting.

 * When the user clicks a nav link, highlight it and remove the

 * highlight from all other links.

 */

sidebarLinks.forEach(function (link) {
  link.addEventListener('click', function (event) {
    event.preventDefault();
    const section = this.getAttribute('data-section') || 'dashboard';
    showDashboardView(section, true);
  });
});





/* ================================================================

   SECTION 5: MODAL HELPER FUNCTIONS

   Modals use the HTML `hidden` attribute.

   When hidden is present, the element is invisible.

   We remove it to show, and add it to hide.

================================================================ */



/**

 * Opens a modal.

 * @param {HTMLElement} modal - The modal overlay element to show.

 */

function openModal(modal) {

  modal.removeAttribute('hidden');



  // Prevent the page behind the modal from scrolling

  document.body.style.overflow = 'hidden';



  // Move focus into the modal for keyboard/screen reader accessibility

  const firstInput = modal.querySelector('input, textarea, button');

  if (firstInput) firstInput.focus();

}



/**

 * Closes a modal and resets its form.

 * @param {HTMLElement} modal - The modal overlay element to hide.

 * @param {HTMLFormElement} form  - The form inside the modal to reset.

 */

function closeModal(modal, form) {

  modal.setAttribute('hidden', '');



  // Allow the page to scroll again

  document.body.style.overflow = '';



  // Reset the form fields

  if (form) form.reset();



  // Clear any validation error messages and red borders

  clearFormErrors(form);

}



/**

 * Close a modal when the user clicks on the dark backdrop

 * (outside the white modal box).

 */

function setupBackdropClose(modal, form) {

  modal.addEventListener('click', function (event) {

    // event.target is what was clicked.

    // If it's the overlay itself (not the box inside it), close.

    if (event.target === modal) {

      closeModal(modal, form);

    }

  });

}



/**

 * Close modals on pressing the Escape key — standard UX pattern.

 */

document.addEventListener('keydown', function (event) {

  if (event.key === 'Escape') {

    if (!createGroupModal.hasAttribute('hidden')) {

      closeModal(createGroupModal, createGroupForm);

    }

    if (!joinGroupModal.hasAttribute('hidden')) {

      resetJoinModal();

      closeModal(joinGroupModal, joinGroupForm);

    }

    if (loginModal && !loginModal.hasAttribute('hidden')) {

      closeModal(loginModal, loginForm);

    }

    if (signupModal && !signupModal.hasAttribute('hidden')) {

      closeModal(signupModal, signupForm);

    }

    if (inviteModal && !inviteModal.hasAttribute('hidden')) {

      closeModal(inviteModal);

    }

    if (createTaskModal && !createTaskModal.hasAttribute('hidden')) {

      closeModal(createTaskModal, createTaskForm);

    }

    if (editTaskModal && !editTaskModal.hasAttribute('hidden')) {

      closeModal(editTaskModal, editTaskForm);

    }

    if (scheduleSessionModal && !scheduleSessionModal.hasAttribute('hidden')) {

      closeModal(scheduleSessionModal, scheduleSessionForm);

    }

    if (editSessionModal && !editSessionModal.hasAttribute('hidden')) {

      closeModal(editSessionModal, editSessionForm);

    }

    if (cancelSessionModal && !cancelSessionModal.hasAttribute('hidden')) {

      sessionToCancelId = null;

      closeModal(cancelSessionModal);

    }

  }

});





/* ================================================================

   SECTION 6: FORM VALIDATION HELPERS

   We validate forms before submitting them to avoid empty data.

================================================================ */



/**

 * Shows an error message under a form field and adds a red border.

 * @param {HTMLInputElement} input - The input element that has an error.

 * @param {HTMLElement} errorEl    - The <p> element that shows the message.

 * @param {string} message         - The error text to show.

 */

function showFieldError(input, errorEl, message) {

  input.classList.add('error');       // Adds red border (defined in CSS)

  errorEl.textContent = message;      // Sets the error text

}



/**

 * Clears the error state from a single field.

 */

function clearFieldError(input, errorEl) {

  input.classList.remove('error');

  errorEl.textContent = '';

}



/**

 * Clears all errors in a form.

 * Called when we reset the form.

 * @param {HTMLFormElement} form

 */

function clearFormErrors(form) {

  if (!form) return;



  // Remove the red border from all inputs

  form.querySelectorAll('.error').forEach(el => el.classList.remove('error'));



  // Clear all error message text

  form.querySelectorAll('.form-error').forEach(el => el.textContent = '');

}



// Clear errors as the user types — gives instant feedback

groupNameInput.addEventListener('input', () => clearFieldError(groupNameInput, groupNameError));

if (taskTitleInput) {

  taskTitleInput.addEventListener('input', () => clearFieldError(taskTitleInput, taskTitleError));

}

if (editTaskTitleInput) {

  editTaskTitleInput.addEventListener('input', () => clearFieldError(editTaskTitleInput, editTaskTitleError));

}

if (sessionTitleInput) {

  sessionTitleInput.addEventListener('input', () => clearFieldError(sessionTitleInput, sessionTitleError));

}

if (sessionDateInput) {

  sessionDateInput.addEventListener('input', () => clearFieldError(sessionDateInput, sessionDateError));

}

if (sessionStartTimeInput) {

  sessionStartTimeInput.addEventListener('input', () => clearFieldError(sessionStartTimeInput, sessionStartTimeError));

}

if (sessionEndTimeInput) {

  sessionEndTimeInput.addEventListener('input', () => clearFieldError(sessionEndTimeInput, sessionEndTimeError));

}

if (editSessionTitleInput) {

  editSessionTitleInput.addEventListener('input', () => clearFieldError(editSessionTitleInput, editSessionTitleError));

}

if (editSessionDateInput) {

  editSessionDateInput.addEventListener('input', () => clearFieldError(editSessionDateInput, editSessionDateError));

}

if (editSessionStartTimeInput) {

  editSessionStartTimeInput.addEventListener('input', () => clearFieldError(editSessionStartTimeInput, editSessionStartTimeError));

}

if (editSessionEndTimeInput) {

  editSessionEndTimeInput.addEventListener('input', () => clearFieldError(editSessionEndTimeInput, editSessionEndTimeError));

}

groupDescInput.addEventListener('input', () => clearFieldError(groupDescInput, groupDescError));

inviteCodeInput.addEventListener('input', () => clearFieldError(inviteCodeInput, inviteCodeError));



// Clear auth input errors on typing

loginEmailInput.addEventListener('input', () => { clearFieldError(loginEmailInput, loginEmailError); loginGeneralError.textContent = ''; });

loginPasswordInput.addEventListener('input', () => { clearFieldError(loginPasswordInput, loginPasswordError); loginGeneralError.textContent = ''; });

signupNameInput.addEventListener('input', () => { clearFieldError(signupNameInput, signupNameError); signupGeneralError.textContent = ''; });

signupEmailInput.addEventListener('input', () => { clearFieldError(signupEmailInput, signupEmailError); signupGeneralError.textContent = ''; });

signupPasswordInput.addEventListener('input', () => { clearFieldError(signupPasswordInput, signupPasswordError); signupGeneralError.textContent = ''; });





/* ================================================================

   SECTION 7: CREATE GROUP MODAL

================================================================ */



// Open the modal when the "+ Create Group" button is clicked

createGroupBtn.addEventListener('click', function () {

  openModal(createGroupModal);

});



// Close via the ✕ button

closeCreateModal.addEventListener('click', function () {

  closeModal(createGroupModal, createGroupForm);

});



// Close via the "Cancel" button

cancelCreateBtn.addEventListener('click', function () {

  closeModal(createGroupModal, createGroupForm);

});



// Close when clicking the dark backdrop

setupBackdropClose(createGroupModal, createGroupForm);



/**

 * Handle the Create Group form submission.

 * 1. Prevent the browser's default form submit (which would reload the page).

 * 2. Validate the fields.

 * 3. If valid, create a new group card on the dashboard.

 */

createGroupForm.addEventListener('submit', async function (event) {

  event.preventDefault();



  const name = groupNameInput.value.trim();

  const subject = groupSubjectInput.value.trim();

  const desc = groupDescInput.value.trim();



  let hasError = false;



  if (!name) {

    showFieldError(groupNameInput, groupNameError, 'Group name is required.');

    hasError = true;

  }



  if (!desc) {

    showFieldError(groupDescInput, groupDescError, 'Please add a short description.');

    hasError = true;

  }



  if (hasError) return;



  try {

    const response = await fetch(`${API_BASE_URL}/api/groups`, {

      method: "POST",

      headers: getAuthHeaders(),

      body: JSON.stringify({

        name: name,

        subject: subject,

        description: desc

      })

    });



    if (!response.ok) {

      throw new Error("Failed to create group.");

    }



    const data = await response.json();

    const grp = data.group;

    const mCount = grp.member_count !== undefined ? grp.member_count : (grp.members_count || 0);

    const tCount = grp.task_count !== undefined ? grp.task_count : (grp.tasks_count || 0);

    const sCount = grp.session_count !== undefined ? grp.session_count : (grp.sessions_count || 0);

    const user = getCurrentUser();

    const initialMembers = (mCount > 0 && user) ? [{ id: user.id, name: user.name }] : [];



    // Display the group returned by the backend with actual database counts

    addGroupCard(

      grp.id,

      grp.name,

      grp.subject,

      grp.description,

      mCount,

      tCount,

      sCount,

      initialMembers

    );



    closeModal(createGroupModal, createGroupForm);



  } catch (error) {

    console.error("Error creating group:", error);

    alert("Could not create the group. Please check whether the backend is running.");

  }

});





/**

 * Creates a group card element and prepends it to the groups grid.

 * This is the core "dynamic DOM" feature — no page reload needed.

 *

 * @param {number|string} id      - Database group ID

 * @param {string} name           - The group name entered by the user

 * @param {string} subject        - The subject/topic (optional)

 * @param {string} desc           - The description entered by the user

 * @param {number} [memberCount]  - Actual number of group members from PostgreSQL

 * @param {number} [taskCount]    - Actual number of tasks from PostgreSQL

 * @param {number} [sessionCount] - Actual number of sessions from PostgreSQL

 * @param {Array}  [members]      - Array of member objects for avatar previews

 */

function addGroupCard(id, name, subject, desc, memberCount = 0, taskCount = 0, sessionCount = 0, members = []) {

  // Pick a color for the avatar and cycle to the next one

  const avatarClass = avatarColors[nextAvatarColorIndex % avatarColors.length];

  nextAvatarColorIndex++;



  // Create the 2-letter abbreviation for the avatar (e.g. "Python Study" → "PS")

  const words = (name || '').trim().split(/\s+/).filter(Boolean);

  const initials = words.length >= 2

    ? (words[0][0] || '') + (words[1][0] || '')

    : (words[0] ? words[0].slice(0, 2) : 'SG');

  const safeInitials = (initials || 'SG').toUpperCase();



  // Use the subject if provided, or fall back to the group name

  const displaySubject = subject || name;



  // Increment the group count and update the stat card

  currentGroupCount++;

  if (groupCount) {

    groupCount.textContent = currentGroupCount;

  }



  const mCount = Number(memberCount) || 0;

  const tCount = Number(taskCount) || 0;

  const sCount = Number(sessionCount) || 0;



  // Build member avatar icons dynamically from the database

  let membersHtml = '';

  if (Array.isArray(members) && members.length > 0) {

    const previewList = members.slice(0, 4);

    previewList.forEach(m => {

      const mName = m.name || 'Member';

      const initial = mName.trim() ? mName.trim()[0].toUpperCase() : 'M';

      membersHtml += `<div class="member-avatar" title="${escapeHtml(mName)}">${escapeHtml(initial)}</div>`;

    });

    if (members.length > 4) {

      membersHtml += `<div class="member-avatar member-more">+${members.length - 4}</div>`;

    }

  } else if (mCount > 0) {

    membersHtml = `<div class="member-avatar" title="Member">👤</div>`;

  } else {

    membersHtml = `<span style="font-size: 12px; color: var(--color-text-muted);">No members yet</span>`;

  }



  // Format stats labels dynamically based on database counts

  const memberLabel = mCount === 1 ? '1 member' : `${mCount} members`;

  const taskLabel = tCount === 1 ? '1 task' : `${tCount} tasks`;

  const sessionLabel = sCount === 0 ? 'No sessions yet' : (sCount === 1 ? '1 session' : `${sCount} sessions`);



  // ── Build the HTML for the card ──

  const card = document.createElement('div');

  card.dataset.groupId = id;

  card.classList.add('group-card', 'new-card'); // 'new-card' triggers slide-in animation

  card.innerHTML = `

    <div class="group-card-header">

      <div class="group-avatar ${avatarClass}">${safeInitials}</div>

      <div class="group-meta">

        <h3 class="group-name">${escapeHtml(name)}</h3>

        <p class="group-subject">📚 ${escapeHtml(displaySubject)}</p>

      </div>

      <span class="group-badge badge-active">Active</span>

    </div>

    <p class="group-desc">${escapeHtml(desc)}</p>

    <div class="group-stats">

      <span>👥 ${escapeHtml(memberLabel)}</span>

      <span>✅ ${escapeHtml(taskLabel)}</span>

      <span>🗓️ ${escapeHtml(sessionLabel)}</span>

    </div>

    <div class="group-card-footer">

      <div class="group-members">

        ${membersHtml}

      </div>

      <button class="btn btn-outline-small open-group-btn">Open →</button>

      <button class="delete-group-btn">Delete</button>

    </div>

  `;



  // ── Attach Open button functionality ──

  const openButton = card.querySelector('.open-group-btn');

  if (openButton) {

    openButton.addEventListener('click', function () {

      openGroupDetails(id);

    });

  }



  // ── Attach Delete button functionality ──

  const deleteButton = card.querySelector('.delete-group-btn');

  deleteButton.addEventListener('click', async function () {

    const confirmDelete = confirm("Are you sure you want to delete this group? Only the group owner can delete it.");

    if (confirmDelete === false) {

      return;

    }



    try {

      const response = await fetch(`${API_BASE_URL}/api/groups/${id}`, {

        method: "DELETE",

        headers: getAuthHeaders(false)

      });



      if (!response.ok) {

        const err = await response.json().catch(() => ({}));

        alert(err.detail || "Could not delete group. Only the group owner is authorized to delete this group.");

        return;

      }



      card.remove();



      if (currentGroupCount > 0) {

        currentGroupCount--;

      }

      if (groupCount) {

        groupCount.textContent = currentGroupCount;

      }



      // If no groups left, show the friendly empty state

      if (currentGroupCount === 0) {

        renderEmptyGroupsState();

      }



    } catch (error) {

      console.error("Delete error:", error);

      alert("Something went wrong while deleting the group.");

    }

  });



  // Remove any empty state card if present before adding

  const existingEmpty = groupsGrid.querySelector('.groups-empty-state, .groups-error-state');

  if (existingEmpty) {

    existingEmpty.remove();

  }



  // Add the card at the top of the grid (prepend = add before other cards)

  groupsGrid.prepend(card);



  // Remove the animation class after it finishes so it doesn't replay on interaction

  card.addEventListener('animationend', function () {

    card.classList.remove('new-card');

  });

}









function renderEmptyGroupsState() {

  groupsGrid.innerHTML = `

    <div class="groups-empty-state" style="grid-column: 1 / -1; text-align: center; padding: 48px 20px; background: var(--color-surface); border: 1px dashed var(--color-border); border-radius: var(--radius-lg);">

      <p style="font-size: 2.6rem; margin-bottom: 10px;">👥</p>

      <h3 style="font-size: 1.25rem; color: var(--color-text); margin-bottom: 8px;">No Study Groups Yet</h3>

      <p style="font-size: 14px; color: var(--color-text-muted); max-width: 440px; margin: 0 auto 24px; line-height: 1.5;">You haven't joined or created any study groups yet. Create your first group or join one using an invitation code!</p>

      <div style="display: flex; gap: 12px; justify-content: center; flex-wrap: wrap;">

        <button class="btn btn-primary" id="empty-create-group-btn">+ Create Group</button>

        <button class="btn btn-outline" id="empty-join-group-btn">🔗 Join Group</button>

      </div>

    </div>

  `;

  const emptyCreate = document.getElementById('empty-create-group-btn');

  if (emptyCreate) {

    emptyCreate.addEventListener('click', () => openModal(createGroupModal));

  }

  const emptyJoin = document.getElementById('empty-join-group-btn');

  if (emptyJoin) {

    emptyJoin.addEventListener('click', () => openModal(joinGroupModal));

  }

}



async function loadGroups() {

  const token = getAuthToken();



  // If user is not authenticated, show friendly sign-in prompt instead of querying

  if (!token) {

    groupsGrid.innerHTML = `

      <div class="groups-empty-state" style="grid-column: 1 / -1; text-align: center; padding: 48px 20px; background: var(--color-surface); border: 1px dashed var(--color-border); border-radius: var(--radius-lg);">

        <p style="font-size: 2.6rem; margin-bottom: 10px;">🔒</p>

        <h3 style="font-size: 1.25rem; color: var(--color-text); margin-bottom: 8px;">Sign In to View Your Groups</h3>

        <p style="font-size: 14px; color: var(--color-text-muted); max-width: 420px; margin: 0 auto 20px;">Please log in or create an account to access your personal study groups.</p>

        <button class="btn btn-primary" onclick="openModal(loginModal)">Log In</button>

      </div>

    `;

    currentGroupCount = 0;

    if (groupCount) groupCount.textContent = '0';

    return;

  }



  try {

    const response = await fetch(`${API_BASE_URL}/api/groups`, {

      headers: getAuthHeaders(false)

    });



    if (response.status === 401) {

      // Session expired or invalid token

      localStorage.removeItem('currentUser');

      localStorage.removeItem('authToken');

      updateAuthNavigation();

      groupsGrid.innerHTML = `

        <div class="groups-empty-state" style="grid-column: 1 / -1; text-align: center; padding: 48px 20px; background: var(--color-surface); border: 1px dashed var(--color-border); border-radius: var(--radius-lg);">

          <p style="font-size: 2.6rem; margin-bottom: 10px;">⌛</p>

          <h3 style="font-size: 1.25rem; color: var(--color-text); margin-bottom: 8px;">Session Expired</h3>

          <p style="font-size: 14px; color: var(--color-text-muted); max-width: 420px; margin: 0 auto 20px;">Your session has expired. Please log in again to access your study groups.</p>

          <button class="btn btn-primary" onclick="openModal(loginModal)">Log In</button>

        </div>

      `;

      currentGroupCount = 0;

      if (groupCount) groupCount.textContent = '0';

      return;

    }



    if (!response.ok) {

      throw new Error("Failed to fetch groups.");

    }



    const data = await response.json();



    // Clear the groups grid (removes previous user's groups or placeholders)

    groupsGrid.innerHTML = "";



    // Reset the group counter

    currentGroupCount = 0;



    const groups = data.groups || [];



    if (groups.length === 0) {

      renderEmptyGroupsState();

    } else {

      // Display only the groups returned for the authenticated user

      groups.forEach(function (group) {

        const mCount = group.member_count !== undefined ? group.member_count : (group.members_count || 0);

        const tCount = group.task_count !== undefined ? group.task_count : (group.tasks_count || 0);

        const sCount = group.session_count !== undefined ? group.session_count : (group.sessions_count || 0);



        addGroupCard(

          group.id,

          group.name,

          group.subject,

          group.description,

          mCount,

          tCount,

          sCount,

          group.members || []

        );

      });

    }



    if (groupCount) {

      groupCount.textContent = currentGroupCount;

    }



    // Update Dashboard Pending Tasks count from PostgreSQL

    if (dashboardTasksCount) {

      const totalPending = groups.reduce((acc, g) => acc + (Number(g.pending_task_count) || 0), 0);

      dashboardTasksCount.textContent = totalPending;

    }



  } catch (error) {

    console.error("Error loading groups:", error);

    if (groupsGrid && groupsGrid.children.length === 0) {

      groupsGrid.innerHTML = `

        <div class="groups-error-state" style="grid-column: 1 / -1; text-align: center; padding: 40px 16px; background: var(--color-surface); border: 1px solid var(--color-border); border-radius: var(--radius-lg);">

          <p style="font-size: 2.2rem; margin-bottom: 8px;">⚠️</p>

          <h3 style="font-size: 1.15rem; color: var(--color-text); margin-bottom: 6px;">Unable to Load Study Groups</h3>

          <p style="font-size: 14px; color: var(--color-text-muted); margin-bottom: 16px;">Please ensure your FastAPI backend is running on port 8000.</p>

          <button class="btn btn-outline-small" onclick="loadGroups()">🔄 Retry</button>

        </div>

      `;

    }

  }

}



// Event delegation for opening groups from groups grid (supports sample and dynamic cards)

groupsGrid.addEventListener('click', function (event) {

  const openBtn = event.target.closest('.open-group-btn') || 

    (event.target.classList.contains('btn-outline-small') && event.target.textContent.includes('Open') ? event.target : null);

  

  if (openBtn) {

    const card = openBtn.closest('.group-card');

    if (card && card.dataset.groupId) {

      openGroupDetails(card.dataset.groupId);

    }

  }

});



/**

 * Escapes special HTML characters to prevent XSS (security best practice).

 * If a user types "<script>alert('hi')</script>" as a group name,

 * this function prevents it from actually running as code.

 *

 * @param {string} str - The raw string from user input

 * @returns {string}   - The safe, escaped string

 */

function escapeHtml(str) {

  if (str === null || str === undefined) return '';

  const div = document.createElement('div');

  div.textContent = str;

  return div.innerHTML;

}





/* ================================================================

   SECTION 8: JOIN GROUP MODAL

================================================================ */



// Open the modal when "Join Group" is clicked

joinGroupBtn.addEventListener('click', function () {

  openModal(joinGroupModal);

});



// Close via the ✕ button

closeJoinModal.addEventListener('click', function () {

  resetJoinModal();

  closeModal(joinGroupModal, joinGroupForm);

});



// Close via the "Cancel" button

cancelJoinBtn.addEventListener('click', function () {

  resetJoinModal();

  closeModal(joinGroupModal, joinGroupForm);

});



// Close when clicking the dark backdrop

setupBackdropClose(joinGroupModal, joinGroupForm);



/**

 * Reset the Join Group modal to its initial state.

 * We need this because the modal shows dynamic content

 * (info notice, success message) that must be cleared on close.

 */

function resetJoinModal() {

  if (joinInfoNotice) joinInfoNotice.setAttribute('hidden', '');

  if (joinSuccessNotice) joinSuccessNotice.setAttribute('hidden', '');

  if (joinSuccessText) joinSuccessText.textContent = '';

  if (joinGeneralError) joinGeneralError.textContent = '';

  if (inviteCodeInput) {

    inviteCodeInput.value = '';

    clearFieldError(inviteCodeInput, inviteCodeError);

  }

  if (joinModalActions) joinModalActions.removeAttribute('hidden');

}



/**

 * Handle the Join Group form submission.

 * Validates the invite code against the backend and joins the group.

 */

joinGroupForm.addEventListener('submit', async function (event) {

  event.preventDefault();



  const code = inviteCodeInput.value.trim().toUpperCase();



  // ── Validation: invite code must not be empty ──

  if (!code) {

    showFieldError(inviteCodeInput, inviteCodeError, 'Please enter an invitation code.');

    return;

  }



  // ── Check authentication ──

  const token = getAuthToken();

  if (!token) {

    if (joinGeneralError) {

      joinGeneralError.textContent = 'Please log in or create an account before joining a study group.';

    }

    return;

  }



  const submitBtn = document.getElementById('submit-join-btn');

  try {

    submitBtn.disabled = true;

    submitBtn.textContent = 'Joining...';

    if (joinGeneralError) joinGeneralError.textContent = '';



    const response = await fetch(`${API_BASE_URL}/api/groups/join`, {

      method: 'POST',

      headers: getAuthHeaders(),

      body: JSON.stringify({ invite_code: code })

    });



    const data = await response.json();

    submitBtn.disabled = false;

    submitBtn.textContent = 'Join Group';



    if (!response.ok) {

      if (joinGeneralError) {

        joinGeneralError.textContent = data.detail || 'Invalid or expired invitation code. Please verify and try again.';

      }

      return;

    }



    if (data.already_member) {

      if (joinGeneralError) {

        joinGeneralError.textContent = data.message || 'You are already a member of this study group.';

      }

      return;

    }



    // ── Show a success message ──

    joinSuccessText.textContent = data.message || 'You have successfully joined the group!';

    joinSuccessNotice.removeAttribute('hidden');



    // ── Hide the submit/cancel buttons after success ──

    joinModalActions.setAttribute('hidden', '');



    // Refresh groups on dashboard

    loadGroups();



  } catch (err) {

    console.error('Join group error:', err);

    submitBtn.disabled = false;

    submitBtn.textContent = 'Join Group';

    if (joinGeneralError) {

      joinGeneralError.textContent = 'Could not connect to backend server. Please make sure FastAPI is running.';

    }

  }

});





/* ================================================================

   SECTION 8C: INVITE MEMBERS MODAL & ACTIONS

================================================================ */



if (inviteMembersBtn) {

  inviteMembersBtn.addEventListener('click', async function () {

    if (!currentDetailsGroupId) return;



    try {

      inviteMembersBtn.disabled = true;

      const originalText = inviteMembersBtn.textContent;

      inviteMembersBtn.textContent = 'Generating...';



      const response = await fetch(`${API_BASE_URL}/api/groups/${currentDetailsGroupId}/invitations`, {

        method: 'POST',

        headers: getAuthHeaders()

      });



      inviteMembersBtn.disabled = false;

      inviteMembersBtn.textContent = originalText;



      if (!response.ok) {

        const err = await response.json().catch(() => ({}));

        alert(err.detail || 'Could not generate invitation code. Please try again.');

        return;

      }



      const data = await response.json();

      const code = data.invite_code;



      if (inviteCodeVal) {

        inviteCodeVal.textContent = code;

      }



      if (inviteLinkInput) {

        const baseUrl = window.location.href.split('#')[0];

        inviteLinkInput.value = `${baseUrl}#invite=${code}`;

      }



      if (inviteGeneralError) {

        inviteGeneralError.textContent = '';

      }



      openModal(inviteModal);



    } catch (err) {

      console.error('Error generating invitation:', err);

      inviteMembersBtn.disabled = false;

      inviteMembersBtn.textContent = '✉️ Invite Members';

      alert('Could not connect to backend server.');

    }

  });

}



// Copy Code Button

if (copyInviteCodeBtn) {

  copyInviteCodeBtn.addEventListener('click', function () {

    const code = inviteCodeVal ? inviteCodeVal.textContent.trim() : '';

    if (!code || code === 'TS-XXXXXX') return;



    navigator.clipboard.writeText(code).then(() => {

      const originalText = copyInviteCodeBtn.textContent;

      copyInviteCodeBtn.textContent = 'Copied! ✅';

      setTimeout(() => {

        copyInviteCodeBtn.textContent = originalText;

      }, 2000);

    }).catch(err => {

      console.error('Copy code failed:', err);

    });

  });

}



// Copy Shareable Link Button

if (copyInviteLinkBtn) {

  copyInviteLinkBtn.addEventListener('click', function () {

    const link = inviteLinkInput ? inviteLinkInput.value.trim() : '';

    if (!link) return;



    navigator.clipboard.writeText(link).then(() => {

      const originalText = copyInviteLinkBtn.textContent;

      copyInviteLinkBtn.textContent = 'Copied! ✅';

      setTimeout(() => {

        copyInviteLinkBtn.textContent = originalText;

      }, 2000);

    }).catch(err => {

      console.error('Copy link failed:', err);

    });

  });

}



// Close Invite Modal

if (closeInviteModal) {

  closeInviteModal.addEventListener('click', () => closeModal(inviteModal));

}

if (closeInviteBtn) {

  closeInviteBtn.addEventListener('click', () => closeModal(inviteModal));

}

if (inviteModal) {

  setupBackdropClose(inviteModal);

}







/* ================================================================

   SECTION 8D: STUDY GROUP TASKS MANAGEMENT

   - Creating tasks inside study groups

   - Assigning tasks to group members

   - Setting deadlines and detecting overdue tasks

   - Tracking Pending, In Progress, and Completed statuses

   - Real-time task statistics & progress bar calculation

   ================================================================ */



function renderTaskStats(stats = {}) {

  const total = stats.total || 0;

  const pending = stats.pending || 0;

  const inProgress = stats.in_progress || 0;

  const completed = stats.completed || 0;

  const rate = stats.completion_rate !== undefined ? stats.completion_rate : (total > 0 ? Math.round((completed / total) * 100) : 0);

  const active = stats.active !== undefined ? stats.active : (pending + inProgress);



  if (tasksTotalBadge) tasksTotalBadge.textContent = `${total} ${total === 1 ? 'task' : 'tasks'}`;

  if (statPendingCount) statPendingCount.textContent = pending;

  if (statInprogressCount) statInprogressCount.textContent = inProgress;

  if (statCompletedCount) statCompletedCount.textContent = completed;

  if (statCompletionRate) statCompletionRate.textContent = `${rate}%`;

  if (taskProgressFill) taskProgressFill.style.width = `${rate}%`;



  if (tabCountAll) tabCountAll.textContent = total;

  if (tabCountPending) tabCountPending.textContent = pending;

  if (tabCountInprogress) tabCountInprogress.textContent = inProgress;

  if (tabCountCompleted) tabCountCompleted.textContent = completed;



  if (detailTasksCount) {

    detailTasksCount.textContent = active;

  }

}



function resetTaskFilterTabs() {

  currentTaskFilter = 'all';

  document.querySelectorAll('.task-filter-tab').forEach(tab => {

    if (tab.dataset.filter === 'all') {

      tab.classList.add('active');

    } else {

      tab.classList.remove('active');

    }

  });

}



function populateTaskAssigneeDropdown(members = []) {

  if (!taskAssigneeSelect) return;

  taskAssigneeSelect.innerHTML = '<option value="">👤 Unassigned</option>';



  members.forEach(m => {

    const opt = document.createElement('option');

    opt.value = m.id;

    const isOwner = (m.role || '').toLowerCase() === 'owner';

    const roleTag = isOwner ? ' (Owner)' : '';

    opt.textContent = `👤 ${m.name}${roleTag}`;

    taskAssigneeSelect.appendChild(opt);

  });

}



function populateEditTaskAssigneeDropdown(members = []) {

  if (!editTaskAssigneeSelect) return;

  editTaskAssigneeSelect.innerHTML = '<option value="">👤 Unassigned</option>';



  members.forEach(m => {

    const opt = document.createElement('option');

    opt.value = m.id;

    const isOwner = (m.role || '').toLowerCase() === 'owner';

    const roleTag = isOwner ? ' (Owner)' : '';

    opt.textContent = `👤 ${m.name}${roleTag}`;

    editTaskAssigneeSelect.appendChild(opt);

  });

}



function renderTasks(tasks = [], filter = 'all') {

  if (!detailTasksList) return;

  detailTasksList.innerHTML = '';



  const filtered = tasks.filter(t => {

    if (filter === 'all') return true;

    return (t.status || 'pending').toLowerCase() === filter.toLowerCase();

  });



  if (filtered.length === 0) {

    const emptyMsg = filter === 'all'

      ? "📝 No tasks have been created for this study group yet. Click '+ Add Task' above to assign your first task!"

      : `No ${filter.replace('_', ' ')} tasks found in this group.`;

    detailTasksList.innerHTML = `

      <div class="tasks-empty">

        <p>${escapeHtml(emptyMsg)}</p>

      </div>

    `;

    return;

  }



  filtered.forEach(task => {

    const card = document.createElement('div');

    const status = (task.status || 'pending').toLowerCase();

    card.classList.add('task-card', `is-${status.replace('_', '')}`);

    card.dataset.taskId = task.id;



    // Status badge text & icon

    let statusBadgeHtml = '';

    if (status === 'completed') {

      statusBadgeHtml = `<span class="task-status-badge badge-completed">✅ Completed</span>`;

    } else if (status === 'in_progress') {

      statusBadgeHtml = `<span class="task-status-badge badge-inprogress">🔄 In Progress</span>`;

    } else {

      statusBadgeHtml = `<span class="task-status-badge badge-pending">⏳ Pending</span>`;

    }



    // Assignee pill

    let assigneeHtml = '';

    if (task.assignee && task.assignee.name) {

      const aName = task.assignee.name;

      assigneeHtml = `<span class="task-pill" title="Assigned to ${escapeHtml(aName)}">👤 <strong>${escapeHtml(aName)}</strong></span>`;

    } else {

      assigneeHtml = `<span class="task-pill" style="opacity: 0.7;">👤 Unassigned</span>`;

    }



    // Deadline pill

    let dueHtml = '';

    if (task.due_date_formatted) {

      if (task.is_overdue) {

        dueHtml = `<span class="task-pill task-pill-overdue" title="Overdue deadline: ${escapeHtml(task.due_date_formatted)}">⚠️ Overdue: ${escapeHtml(task.due_date_formatted)}</span>`;

      } else {

        dueHtml = `<span class="task-pill" title="Due on ${escapeHtml(task.due_date_formatted)}">📅 Due: ${escapeHtml(task.due_date_formatted)}</span>`;

      }

    } else {

      dueHtml = `<span class="task-pill" style="opacity: 0.7;">📅 No deadline</span>`;

    }



    card.innerHTML = `

      <div class="task-header-row">

        <h4 class="task-title">${escapeHtml(task.title)}</h4>

        ${statusBadgeHtml}

      </div>

      ${task.description ? `<p class="task-desc">${escapeHtml(task.description)}</p>` : ''}

      <div class="task-footer-row">

        <div class="task-meta-left">

          ${assigneeHtml}

          ${dueHtml}

        </div>

        <div class="task-meta-right">

          <label style="font-size: 11px; color: var(--color-text-muted); font-weight: 600;">Status:</label>

          <select class="task-status-select" data-task-id="${task.id}" aria-label="Change task status">

            <option value="pending" ${status === 'pending' ? 'selected' : ''}>⏳ Pending</option>

            <option value="in_progress" ${status === 'in_progress' ? 'selected' : ''}>🔄 In Progress</option>

            <option value="completed" ${status === 'completed' ? 'selected' : ''}>✅ Completed</option>

          </select>

          <button class="task-edit-btn" data-task-id="${task.id}" title="Edit task details">✏️ Edit</button>

          <button class="task-del-btn" data-task-id="${task.id}" title="Delete task">🗑️ Delete</button>

        </div>

      </div>

    `;



    detailTasksList.appendChild(card);

  });

}



// ── Filter tabs click handling ──

document.querySelectorAll('.task-filter-tab').forEach(tab => {

  tab.addEventListener('click', function () {

    document.querySelectorAll('.task-filter-tab').forEach(t => t.classList.remove('active'));

    this.classList.add('active');

    currentTaskFilter = this.dataset.filter || 'all';

    renderTasks(currentTasks, currentTaskFilter);

  });

});



// ── Open & Close Add Task Modal ──

if (addTaskBtn) {

  addTaskBtn.addEventListener('click', function () {

    if (taskTitleInput) taskTitleInput.value = '';

    if (taskDescInput) taskDescInput.value = '';

    if (taskDueDateInput) taskDueDateInput.value = '';

    if (taskStatusSelect) taskStatusSelect.value = 'pending';

    if (taskGeneralError) taskGeneralError.textContent = '';

    clearFormErrors(createTaskForm);



    populateTaskAssigneeDropdown(currentGroupMembers);

    openModal(createTaskModal);

  });

}



if (closeTaskModal) {

  closeTaskModal.addEventListener('click', () => closeModal(createTaskModal, createTaskForm));

}

if (cancelTaskBtn) {

  cancelTaskBtn.addEventListener('click', () => closeModal(createTaskModal, createTaskForm));

}

if (createTaskModal) {

  setupBackdropClose(createTaskModal, createTaskForm);

}



// ── Handle Task Creation Form Submission ──

if (createTaskForm) {

  createTaskForm.addEventListener('submit', async function (event) {

    event.preventDefault();

    if (!currentDetailsGroupId) return;



    const title = taskTitleInput ? taskTitleInput.value.trim() : '';

    const desc = taskDescInput ? taskDescInput.value.trim() : '';

    const assigneeVal = taskAssigneeSelect && taskAssigneeSelect.value ? parseInt(taskAssigneeSelect.value, 10) : null;

    const dueDateVal = taskDueDateInput ? taskDueDateInput.value : '';

    const statusVal = taskStatusSelect ? taskStatusSelect.value : 'pending';



    if (!title) {

      showFieldError(taskTitleInput, taskTitleError, 'Task title is required.');

      return;

    }



    try {

      submitTaskBtn.disabled = true;

      submitTaskBtn.textContent = 'Creating...';

      if (taskGeneralError) taskGeneralError.textContent = '';



      const response = await fetch(`${API_BASE_URL}/api/groups/${currentDetailsGroupId}/tasks`, {

        method: 'POST',

        headers: getAuthHeaders(),

        body: JSON.stringify({

          title: title,

          description: desc,

          assigned_to: assigneeVal,

          due_date: dueDateVal || null,

          status: statusVal

        })

      });



      submitTaskBtn.disabled = false;

      submitTaskBtn.textContent = 'Create Task';



      if (!response.ok) {

        const errData = await response.json().catch(() => ({}));

        if (taskGeneralError) {

          taskGeneralError.textContent = errData.detail || 'Could not create task. Please try again.';

        }

        return;

      }



      const data = await response.json();

      const newTask = data.task;

      const stats = data.stats;



      // Add to list and update state

      currentTasks.unshift(newTask);

      renderTaskStats(stats);

      renderTasks(currentTasks, currentTaskFilter);



      closeModal(createTaskModal, createTaskForm);



    } catch (err) {

      console.error('Error creating task:', err);

      submitTaskBtn.disabled = false;

      submitTaskBtn.textContent = 'Create Task';

      if (taskGeneralError) {

        taskGeneralError.textContent = 'Failed to connect to backend server.';

      }

    }

  });

}



// ── Event delegation for Status Change and Delete Task inside detailTasksList ──

if (detailTasksList) {

  // Status Change

  detailTasksList.addEventListener('change', async function (event) {

    if (event.target && event.target.classList.contains('task-status-select')) {

      const select = event.target;

      const taskId = select.dataset.taskId;

      const newStatus = select.value;

      if (!currentDetailsGroupId || !taskId) return;



      try {

        const response = await fetch(`${API_BASE_URL}/api/groups/${currentDetailsGroupId}/tasks/${taskId}/status`, {

          method: 'PATCH',

          headers: getAuthHeaders(),

          body: JSON.stringify({ status: newStatus })

        });



        if (!response.ok) {

          const err = await response.json().catch(() => ({}));

          alert(err.detail || 'Could not update task status.');

          return;

        }



        const data = await response.json();

        const updatedTask = data.task;

        const stats = data.stats;



        // Update task in memory

        const idx = currentTasks.findIndex(t => t.id === Number(taskId));

        if (idx !== -1) {

          currentTasks[idx] = updatedTask;

        }



        renderTaskStats(stats);

        renderTasks(currentTasks, currentTaskFilter);



      } catch (err) {

        console.error('Error updating task status:', err);

        alert('Could not update task status.');

      }

    }

  });



  // Task Actions (Edit & Delete)

  detailTasksList.addEventListener('click', async function (event) {

    // ── Handle Edit Task Click ──

    const editBtn = event.target.closest('.task-edit-btn');

    if (editBtn) {

      const taskId = Number(editBtn.dataset.taskId);

      if (!currentDetailsGroupId || !taskId) return;



      const task = currentTasks.find(t => t.id === taskId);

      if (!task) return;



      // Populate member options

      populateEditTaskAssigneeDropdown(currentGroupMembers);



      // Pre-fill inputs with current task data

      if (editTaskIdInput) editTaskIdInput.value = task.id;

      if (editTaskTitleInput) editTaskTitleInput.value = task.title || '';

      if (editTaskDescInput) editTaskDescInput.value = task.description || '';

      if (editTaskAssigneeSelect) {

        editTaskAssigneeSelect.value = (task.assigned_to !== null && task.assigned_to !== undefined) ? task.assigned_to : '';

      }

      if (editTaskDueDateInput) {

        // Pre-fill ISO date string YYYY-MM-DD

        editTaskDueDateInput.value = task.due_date_iso || (task.due_date ? task.due_date.slice(0, 10) : '');

      }

      if (editTaskStatusSelect) {

        editTaskStatusSelect.value = (task.status || 'pending').toLowerCase();

      }



      clearFieldError(editTaskTitleInput, editTaskTitleError);

      if (editTaskGeneralError) editTaskGeneralError.textContent = '';



      openModal(editTaskModal);

      return;

    }



    // ── Handle Delete Task Click ──

    const delBtn = event.target.closest('.task-del-btn');

    if (delBtn) {

      const taskId = delBtn.dataset.taskId;

      if (!currentDetailsGroupId || !taskId) return;



      const confirmDel = confirm('Are you sure you want to delete this study task? This action cannot be undone.');

      if (!confirmDel) return;



      try {

        const response = await fetch(`${API_BASE_URL}/api/groups/${currentDetailsGroupId}/tasks/${taskId}`, {

          method: 'DELETE',

          headers: getAuthHeaders(false)

        });



        if (!response.ok) {

          const err = await response.json().catch(() => ({}));

          alert(err.detail || 'Could not delete task.');

          return;

        }



        const data = await response.json();

        // Remove from currentTasks immediately

        currentTasks = currentTasks.filter(t => t.id !== Number(taskId));



        renderTaskStats(data.stats);

        renderTasks(currentTasks, currentTaskFilter);



      } catch (err) {

        console.error('Error deleting task:', err);

        alert('Could not delete task.');

      }

    }

  });



// ── Close Edit Task Modal ──

if (closeEditTaskModal) {

  closeEditTaskModal.addEventListener('click', () => closeModal(editTaskModal, editTaskForm));

}

if (cancelEditTaskBtn) {

  cancelEditTaskBtn.addEventListener('click', () => closeModal(editTaskModal, editTaskForm));

}

if (editTaskModal) {

  setupBackdropClose(editTaskModal, editTaskForm);

}



// ── Handle Edit Task Form Submission ──

if (editTaskForm) {

  editTaskForm.addEventListener('submit', async function (event) {

    event.preventDefault();

    if (!currentDetailsGroupId) return;



    const taskId = editTaskIdInput ? editTaskIdInput.value : null;

    const title = editTaskTitleInput ? editTaskTitleInput.value.trim() : '';

    const desc = editTaskDescInput ? editTaskDescInput.value.trim() : '';

    const assigneeVal = editTaskAssigneeSelect && editTaskAssigneeSelect.value ? parseInt(editTaskAssigneeSelect.value, 10) : null;

    const dueDateVal = editTaskDueDateInput ? editTaskDueDateInput.value : '';

    const statusVal = editTaskStatusSelect ? editTaskStatusSelect.value : 'pending';



    if (!title) {

      showFieldError(editTaskTitleInput, editTaskTitleError, 'Task title is required.');

      return;

    }



    try {

      submitEditTaskBtn.disabled = true;

      submitEditTaskBtn.textContent = 'Saving...';

      if (editTaskGeneralError) editTaskGeneralError.textContent = '';



      const response = await fetch(`${API_BASE_URL}/api/groups/${currentDetailsGroupId}/tasks/${taskId}`, {

        method: 'PUT',

        headers: getAuthHeaders(),

        body: JSON.stringify({

          title: title,

          description: desc,

          assigned_to: assigneeVal,

          due_date: dueDateVal || null,

          status: statusVal

        })

      });



      submitEditTaskBtn.disabled = false;

      submitEditTaskBtn.textContent = 'Save Changes';



      if (!response.ok) {

        const errData = await response.json().catch(() => ({}));

        if (editTaskGeneralError) {

          editTaskGeneralError.textContent = errData.detail || 'Could not update task. Please try again.';

        }

        return;

      }



      const data = await response.json();

      const updatedTask = data.task;

      const stats = data.stats;



      // Update task in memory immediately

      const idx = currentTasks.findIndex(t => t.id === Number(taskId));

      if (idx !== -1) {

        currentTasks[idx] = updatedTask;

      }



      renderTaskStats(stats);

      renderTasks(currentTasks, currentTaskFilter);



      closeModal(editTaskModal, editTaskForm);



    } catch (err) {

      console.error('Error saving task:', err);

      submitEditTaskBtn.disabled = false;

      submitEditTaskBtn.textContent = 'Save Changes';

      if (editTaskGeneralError) {

        editTaskGeneralError.textContent = 'Failed to connect to backend server.';

      }

    }

  });

}

}





/* ================================================================

   SECTION 8B: LOGIN & SIGN UP MODALS

================================================================ */



// Close Login Modal via ✕, Cancel, and Backdrop

closeLoginModal.addEventListener('click', () => closeModal(loginModal, loginForm));

cancelLoginBtn.addEventListener('click', () => closeModal(loginModal, loginForm));

setupBackdropClose(loginModal, loginForm);



// Close Sign Up Modal via ✕, Cancel, and Backdrop

closeSignupModal.addEventListener('click', () => closeModal(signupModal, signupForm));

cancelSignupBtn.addEventListener('click', () => closeModal(signupModal, signupForm));

setupBackdropClose(signupModal, signupForm);



// Switch between Login and Sign Up inside the modals

switchToSignup.addEventListener('click', function (event) {

  event.preventDefault();

  closeModal(loginModal, loginForm);

  openModal(signupModal);

});



switchToLogin.addEventListener('click', function (event) {

  event.preventDefault();

  closeModal(signupModal, signupForm);

  openModal(loginModal);

});



// ── Handle Sign Up Form Submission ──

signupForm.addEventListener('submit', async function (event) {

  event.preventDefault();



  const name = signupNameInput.value.trim();

  const email = signupEmailInput.value.trim();

  const password = signupPasswordInput.value.trim();



  let hasError = false;



  if (!name) {

    showFieldError(signupNameInput, signupNameError, 'Full name is required.');

    hasError = true;

  }



  if (!email) {

    showFieldError(signupEmailInput, signupEmailError, 'Email address is required.');

    hasError = true;

  } else if (!email.includes('@') || !email.includes('.')) {

    showFieldError(signupEmailInput, signupEmailError, 'Please enter a valid email address.');

    hasError = true;

  }



  if (!password) {

    showFieldError(signupPasswordInput, signupPasswordError, 'Password is required.');

    hasError = true;

  } else if (password.length < 6) {

    showFieldError(signupPasswordInput, signupPasswordError, 'Password must be at least 6 characters.');

    hasError = true;

  }



  if (hasError) return;



  const submitBtn = document.getElementById('submit-signup-btn');

  try {

    submitBtn.disabled = true;

    submitBtn.textContent = 'Creating account...';



    const response = await fetch(`${API_BASE_URL}/api/signup`, {

      method: 'POST',

      headers: {

        'Content-Type': 'application/json'

      },

      body: JSON.stringify({ name, email, password })

    });



    const data = await response.json();

    submitBtn.disabled = false;

    submitBtn.textContent = 'Create Account';



    if (!response.ok || !data.success) {

      signupGeneralError.textContent = data.message || 'Sign up failed. Please try again.';

      return;

    }



    if (data.access_token && data.user) {

      localStorage.setItem('currentUser', JSON.stringify(data.user));

      localStorage.setItem('authToken', data.access_token);

      updateDashboardUser(data.user);

      updateAuthNavigation();

      closeModal(signupModal, signupForm);

      showDashboard();

    } else {

      closeModal(signupModal, signupForm);

      updateAuthNavigation();

      openModal(loginModal);

      if (loginGeneralError) {

        loginGeneralError.textContent = data.message || 'Account created successfully! Please log in.';

      }

    }



  } catch (err) {

    console.error('Sign up error:', err);

    submitBtn.disabled = false;

    submitBtn.textContent = 'Create Account';

    signupGeneralError.textContent = 'Cannot connect to backend. Please ensure FastAPI is running.';

  }

});



// ── Handle Log In Form Submission ──

loginForm.addEventListener('submit', async function (event) {

  event.preventDefault();



  const email = loginEmailInput.value.trim();

  const password = loginPasswordInput.value.trim();



  let hasError = false;



  if (!email) {

    showFieldError(loginEmailInput, loginEmailError, 'Email address is required.');

    hasError = true;

  }



  if (!password) {

    showFieldError(loginPasswordInput, loginPasswordError, 'Password is required.');

    hasError = true;

  }



  if (hasError) return;



  const submitBtn = document.getElementById('submit-login-btn');

  try {

    submitBtn.disabled = true;

    submitBtn.textContent = 'Logging in...';



    const response = await fetch(`${API_BASE_URL}/api/login`, {

      method: 'POST',

      headers: {

        'Content-Type': 'application/json'

      },

      body: JSON.stringify({ email, password })

    });



    const data = await response.json();

    submitBtn.disabled = false;

    submitBtn.textContent = 'Log In';



    if (!response.ok || !data.success) {

      loginGeneralError.textContent = data.message || 'Invalid email or password.';

      return;

    }



    // Save logged-in user in localStorage

    localStorage.setItem('currentUser', JSON.stringify(data.user));

    if (data.access_token) {

      localStorage.setItem('authToken', data.access_token);

    }

    updateDashboardUser(data.user);

    updateAuthNavigation();



    closeModal(loginModal, loginForm);

    showDashboard();



  } catch (err) {

    console.error('Login error:', err);

    submitBtn.disabled = false;

    submitBtn.textContent = 'Log In';

    loginGeneralError.textContent = 'Cannot connect to backend. Please ensure FastAPI is running.';

  }

});





/* ================================================================

   SECTION 9: RENDER UPCOMING SESSIONS

   Fetches and renders real upcoming sessions from GET /api/sessions.

================================================================ */



/**

 * Builds a session card element from a session data object.

 * @param {Object} session - Session object from backend

 * @returns {HTMLElement} - The built session card element

 */

/**

 * Generates badge HTML for a study session based on its calendar sync status.

 * @param {object} session

 * @returns {string} HTML string

 */

function isEligibleForSyncRetry(session) {

  if (session.calendar_sync_status === 'failed') return true;

  if (session.calendar_sync_status === 'pending' || session.calendar_sync_status === 'syncing') {

    const started = session.calendar_sync_started_at || session.updated_at;

    if (started) {

      const diffMinutes = (Date.now() - new Date(started).getTime()) / (1000 * 60);

      if (diffMinutes > 5) return true;

    }

  }

  return false;

}



function getSessionSyncTagHtml(session) {

  const status = session.calendar_sync_status || (session.calendar_synced ? 'synced' : 'not_connected');

  if (status === 'pending' || status === 'syncing') {

    if (isEligibleForSyncRetry(session)) {

      return `<span class="session-tag session-tag-failed" title="Synchronization timed out. Click retry to synchronize.">⚠️ Sync Timed Out</span>`;

    }

    return `<span class="session-tag session-tag-pending" title="Synchronization with Google Calendar in progress">⏳ Syncing...</span>`;

  } else if (status === 'synced') {

    return `<span class="session-tag session-tag-synced" title="Synced to Google Calendar">📅 Google Synced</span>`;

  } else if (status === 'failed') {

    const errorMsg = session.calendar_sync_error ? ` title="${escapeHtml(session.calendar_sync_error)}"` : ' title="Google Calendar sync failed"';

    return `<span class="session-tag session-tag-failed"${errorMsg}>⚠️ Sync Failed</span>`;

  } else if (status === 'delete_pending') {

    return `<span class="session-tag session-tag-pending" title="Google Calendar deletion is pending in background">🗑️ Deletion Pending</span>`;

  } else {

    return `<span class="session-tag">${escapeHtml(session.tag || "Upcoming")}</span>`;

  }

}



function createSessionElement(session) {

  const item = document.createElement('div');

  item.classList.add('session-item');



  const groupName = session.group_name || session.group || "Study Group";

  const formattedTime = session.formatted_time || session.time || "Scheduled";

  const descHtml = session.description ? `<p class="session-desc" style="font-size: 12px; color: var(--color-text-muted); margin-top: 4px; line-height: 1.4;">${escapeHtml(session.description)}</p>` : '';

  

  const tagHtml = getSessionSyncTagHtml(session);



  item.innerHTML = `

    <div class="session-time-block">

      <p class="session-day">${escapeHtml(session.day || "UPC")}</p>

      <p class="session-date">${escapeHtml(session.date || "--")}</p>

    </div>

    <div class="session-divider"></div>

    <div class="session-info">

      <p class="session-title">${escapeHtml(session.title)}</p>

      <p class="session-meta">📚 ${escapeHtml(groupName)} &nbsp;·&nbsp; 🕐 ${escapeHtml(formattedTime)}</p>

      ${descHtml}

    </div>

    ${tagHtml}

  `;

  return item;

}



/**

 * Loads upcoming sessions for the logged-in user from GET /api/sessions

 * and dynamically renders them on the dashboard.

 */

async function loadDashboardUpcomingSessions() {

  if (!sessionsList) return;

  const token = getAuthToken();



  if (!token) {

    sessionsList.innerHTML = `

      <div class="sessions-empty" style="text-align: center; padding: 24px 16px; background: var(--color-surface); border: 1px dashed var(--color-border); border-radius: var(--radius-md);">

        <p style="font-size: 1.3rem; margin-bottom: 6px;">🗓️</p>

        <p style="font-weight: 600; color: var(--color-text); font-size: 14px;">Log in to view upcoming study sessions</p>

      </div>

    `;

    if (dashboardSessionsCount) dashboardSessionsCount.textContent = '0';

    return;

  }



  try {

    const response = await fetch(`${API_BASE_URL}/api/sessions`, {

      headers: getAuthHeaders(false)

    });



    if (!response.ok) {

      sessionsList.innerHTML = `

        <div class="sessions-empty" style="text-align: center; padding: 20px; color: var(--color-error);">

          <p>⚠️ Unable to load upcoming sessions.</p>

        </div>

      `;

      if (dashboardSessionsCount) dashboardSessionsCount.textContent = '0';

      return;

    }



    const data = await response.json();

    const sessions = data.sessions || [];



    // Update dynamic dashboard session count in quick stats row

    if (dashboardSessionsCount) {

      dashboardSessionsCount.textContent = sessions.length;

    }



    sessionsList.innerHTML = '';



    if (sessions.length === 0) {

      sessionsList.innerHTML = `

        <div class="sessions-empty" style="text-align: center; padding: 32px 16px; background: var(--color-surface); border: 1px dashed var(--color-border); border-radius: var(--radius-md);">

          <p style="font-size: 1.5rem; margin-bottom: 8px;">🗓️</p>

          <p style="font-weight: 600; color: var(--color-text);">No upcoming study sessions</p>

          <p style="font-size: 12px; color: var(--color-text-muted); margin-top: 4px;">Schedule a session inside any of your study groups to see it here.</p>

        </div>

      `;

      return;

    }



    sessions.forEach(session => {

      const el = createSessionElement(session);

      sessionsList.appendChild(el);

    });



  } catch (err) {

    console.error('Error loading dashboard upcoming sessions:', err);

    sessionsList.innerHTML = `

      <div class="sessions-empty" style="text-align: center; padding: 20px; color: var(--color-text-muted);">

        <p>Could not connect to backend server to load sessions.</p>

      </div>

    `;

    if (dashboardSessionsCount) dashboardSessionsCount.textContent = '0';

  }

}





/* ================================================================

   SECTION 9B: SCHEDULE STUDY SESSION MODAL & ACTIONS

   Handles opening, validating, and submitting the Schedule Session modal.

================================================================ */



// Open Schedule Session modal

if (addSessionBtn) {

  addSessionBtn.addEventListener('click', function () {

    if (!currentDetailsGroupId) return;



    if (sessionTitleInput) sessionTitleInput.value = '';

    if (sessionDescInput) sessionDescInput.value = '';

    if (sessionGeneralError) sessionGeneralError.textContent = '';

    clearFormErrors(scheduleSessionForm);



    // Set default date to today's date in local time

    const now = new Date();

    const yyyy = now.getFullYear();

    const mm = String(now.getMonth() + 1).padStart(2, '0');

    const dd = String(now.getDate()).padStart(2, '0');

    const todayStr = `${yyyy}-${mm}-${dd}`;

    if (sessionDateInput) {

      sessionDateInput.value = todayStr;

      sessionDateInput.min = todayStr;

    }



    // Default start time to next round hour, end time to 1 hour later

    const nextHour = new Date(now.getTime() + 60 * 60 * 1000);

    const startHourStr = String(nextHour.getHours()).padStart(2, '0') + ':00';

    const endHour = new Date(now.getTime() + 2 * 60 * 60 * 1000);

    const endHourStr = String(endHour.getHours()).padStart(2, '0') + ':00';

    if (sessionStartTimeInput) sessionStartTimeInput.value = startHourStr;

    if (sessionEndTimeInput) sessionEndTimeInput.value = endHourStr;



    openModal(scheduleSessionModal);

  });

}



// Close Schedule Session modal

if (closeScheduleSessionModal) {

  closeScheduleSessionModal.addEventListener('click', () => closeModal(scheduleSessionModal, scheduleSessionForm));

}

if (cancelScheduleSessionBtn) {

  cancelScheduleSessionBtn.addEventListener('click', () => closeModal(scheduleSessionModal, scheduleSessionForm));

}

if (scheduleSessionModal) {

  setupBackdropClose(scheduleSessionModal, scheduleSessionForm);

}



// Submission guard to prevent duplicate concurrent submissions

let isSubmittingScheduleSession = false;



// Handle Schedule Session Form Submission

if (scheduleSessionForm) {

  scheduleSessionForm.addEventListener('submit', async function (event) {

    event.preventDefault();

    if (!currentDetailsGroupId) return;



    if (isSubmittingScheduleSession) return;

    isSubmittingScheduleSession = true;



    clearFormErrors(scheduleSessionForm);

    if (sessionGeneralError) sessionGeneralError.textContent = '';



    const title = sessionTitleInput ? sessionTitleInput.value.trim() : '';

    const desc = sessionDescInput ? sessionDescInput.value.trim() : '';

    const dateVal = sessionDateInput ? sessionDateInput.value : '';

    const startTimeVal = sessionStartTimeInput ? sessionStartTimeInput.value : '';

    const endTimeVal = sessionEndTimeInput ? sessionEndTimeInput.value : '';



    let hasError = false;



    if (!title) {

      showFieldError(sessionTitleInput, sessionTitleError, 'Session title is required.');

      hasError = true;

    } else if (title.length > 150) {

      showFieldError(sessionTitleInput, sessionTitleError, 'Session title must not exceed 150 characters.');

      hasError = true;

    }



    if (!dateVal) {

      showFieldError(sessionDateInput, sessionDateError, 'Please select a date.');

      hasError = true;

    }



    if (!startTimeVal) {

      showFieldError(sessionStartTimeInput, sessionStartTimeError, 'Please select a start time.');

      hasError = true;

    }



    if (!endTimeVal) {

      showFieldError(sessionEndTimeInput, sessionEndTimeError, 'Please select an end time.');

      hasError = true;

    }



    if (hasError) return;



    // Convert local date and times to ISO timestamp without misinterpreting local time as UTC

    const startDateTime = new Date(`${dateVal}T${startTimeVal}:00`);

    const endDateTime = new Date(`${dateVal}T${endTimeVal}:00`);



    if (isNaN(startDateTime.getTime()) || isNaN(endDateTime.getTime())) {

      if (sessionGeneralError) sessionGeneralError.textContent = 'Invalid date or time format.';

      return;

    }



    if (endDateTime <= startDateTime) {

      showFieldError(sessionEndTimeInput, sessionEndTimeError, 'End time must be later than start time.');

      return;

    }



    try {

      if (submitScheduleSessionBtn) {

        submitScheduleSessionBtn.disabled = true;

        submitScheduleSessionBtn.textContent = 'Scheduling...';

      }



      const response = await fetch(`${API_BASE_URL}/api/groups/${currentDetailsGroupId}/sessions`, {

        method: 'POST',

        headers: getAuthHeaders(),

        body: JSON.stringify({

          title: title,

          description: desc || null,

          start_time: startDateTime.toISOString(),

          end_time: endDateTime.toISOString()

        })

      });



      if (submitScheduleSessionBtn) {

        submitScheduleSessionBtn.disabled = false;

        submitScheduleSessionBtn.textContent = 'Schedule Session';

      }



      if (!response.ok) {

        const errData = await response.json().catch(() => ({}));

        if (sessionGeneralError) {

          sessionGeneralError.textContent = errData.detail || 'Could not schedule study session. Please try again.';

        }

        return;

      }



      const data = await response.json();



      // Close modal

      closeModal(scheduleSessionModal, scheduleSessionForm);



      // Refresh group details (re-fetches group with updated sessions list & stats)

      await openGroupDetails(currentDetailsGroupId);



      // Refresh live dashboard upcoming sessions

      await loadDashboardUpcomingSessions();



      // Show friendly confirmation message

      const successMsg = data.message || 'Study session scheduled successfully!';

      alert(successMsg);



    } catch (err) {

      console.error('Error scheduling study session:', err);

      if (sessionGeneralError) {

        sessionGeneralError.textContent = 'Failed to connect to backend server. Please verify FastAPI is running.';

      }

    } finally {

      isSubmittingScheduleSession = false;

      if (submitScheduleSessionBtn) {

        submitScheduleSessionBtn.disabled = false;

        submitScheduleSessionBtn.textContent = 'Schedule Session';

      }

    }

  });

}





/* ================================================================

   SECTION 9C: EDIT STUDY SESSION MODAL & ACTIONS

   Handles opening, pre-filling, validating, and submitting the Edit Session modal.

================================================================ */



// Event delegation for Session Actions (Edit & Cancel) inside detailSessionsList

if (detailSessionsList) {

  detailSessionsList.addEventListener('click', function (event) {

    // ── 1. Handle Edit Session Click ──

    const editBtn = event.target.closest('.session-edit-btn');

    if (editBtn) {

      const sessionId = Number(editBtn.dataset.sessionId);

      if (!currentDetailsGroupId || !sessionId) return;



      const session = currentGroupSessions.find(s => s.id === sessionId);

      if (!session) return;



      // Verify client-side permission before opening modal

      const currentUser = getCurrentUser();

      const currentUserId = currentUser ? Number(currentUser.id) : null;

      const ownerMember = (currentGroupMembers || []).find(m => (m.role || "").toLowerCase() === "owner");

      const isGroupOwner = (currentUserId !== null && ownerMember && currentUserId === Number(ownerMember.id));

      const isCreator = (currentUserId !== null && session.created_by !== null && currentUserId === Number(session.created_by));



      if (!isCreator && !isGroupOwner) {

        alert("Permission denied. Only the session creator or group owner can edit this session.");

        return;

      }



      // Pre-fill inputs with current session data

      if (editSessionIdInput) editSessionIdInput.value = session.id;

      if (editSessionTitleInput) editSessionTitleInput.value = session.title || '';

      if (editSessionDescInput) editSessionDescInput.value = session.description || '';



      if (session.start_time && session.end_time) {

        const sDate = new Date(session.start_time);

        const eDate = new Date(session.end_time);



        // Local date YYYY-MM-DD

        const yyyy = sDate.getFullYear();

        const mm = String(sDate.getMonth() + 1).padStart(2, '0');

        const dd = String(sDate.getDate()).padStart(2, '0');

        if (editSessionDateInput) editSessionDateInput.value = `${yyyy}-${mm}-${dd}`;



        // Local start time HH:MM

        const sHours = String(sDate.getHours()).padStart(2, '0');

        const sMins = String(sDate.getMinutes()).padStart(2, '0');

        if (editSessionStartTimeInput) editSessionStartTimeInput.value = `${sHours}:${sMins}`;



        // Local end time HH:MM

        const eHours = String(eDate.getHours()).padStart(2, '0');

        const eMins = String(eDate.getMinutes()).padStart(2, '0');

        if (editSessionEndTimeInput) editSessionEndTimeInput.value = `${eHours}:${eMins}`;

      }



      clearFormErrors(editSessionForm);

      if (editSessionGeneralError) editSessionGeneralError.textContent = '';



      openModal(editSessionModal);

      return;

    }



    // ── 2. Handle Cancel Session Click ──

    const cancelBtn = event.target.closest('.session-cancel-btn');

    if (cancelBtn) {

      const sessionId = Number(cancelBtn.dataset.sessionId);

      if (!currentDetailsGroupId || !sessionId) return;



      const session = currentGroupSessions.find(s => s.id === sessionId);

      if (!session) return;



      // Verify client-side permission before opening confirmation dialog

      const currentUser = getCurrentUser();

      const currentUserId = currentUser ? Number(currentUser.id) : null;

      const ownerMember = (currentGroupMembers || []).find(m => (m.role || "").toLowerCase() === "owner");

      const isGroupOwner = (currentUserId !== null && ownerMember && currentUserId === Number(ownerMember.id));

      const isCreator = (currentUserId !== null && session.created_by !== null && currentUserId === Number(session.created_by));



      if (!isCreator && !isGroupOwner) {

        alert("Permission denied. Only the session creator or group owner can cancel this session.");

        return;

      }



      sessionToCancelId = sessionId;

      if (cancelSessionName) cancelSessionName.textContent = session.title || 'Untitled Session';

      if (cancelSessionTime) cancelSessionTime.textContent = session.formatted_time || session.time || 'Scheduled session';

      if (cancelSessionGeneralError) cancelSessionGeneralError.textContent = '';

      if (confirmCancelSessionBtn) {

        confirmCancelSessionBtn.disabled = false;

        confirmCancelSessionBtn.textContent = 'Yes, Cancel Session';

      }



      openModal(cancelSessionModal);

    }



    // ── 3. Handle Retry Sync Click ──

    const retryBtn = event.target.closest('.session-retry-btn');

    if (retryBtn) {

      const sessionId = Number(retryBtn.dataset.sessionId);

      if (!currentDetailsGroupId || !sessionId) return;



      const token = getAuthToken();

      if (!token) return;



      retryBtn.disabled = true;

      const originalText = retryBtn.textContent;

      retryBtn.textContent = '⏳ Retrying...';



      fetch(`${API_BASE_URL}/api/groups/${currentDetailsGroupId}/sessions/${sessionId}/sync`, {

        method: 'POST',

        headers: {

          'Authorization': `Bearer ${token}`,

          'Content-Type': 'application/json'

        }

      })

      .then(async res => {

        const data = await res.json();

        if (!res.ok) {

          throw new Error(data.detail || data.message || 'Failed to retry synchronization.');

        }

        alert(data.message || 'Google Calendar sync queued! ⏳');

        // Refresh session data

        if (currentDetailsGroupId) {

          openGroupDetails(currentDetailsGroupId);

        }

        loadDashboardUpcomingSessions();

      })

      .catch(err => {

        alert(err.message || 'Failed to retry sync.');

        retryBtn.disabled = false;

        retryBtn.textContent = originalText;

      });

    }

  });

}



// Close Edit Session modal

if (closeEditSessionModal) {

  closeEditSessionModal.addEventListener('click', () => closeModal(editSessionModal, editSessionForm));

}

if (cancelEditSessionBtn) {

  cancelEditSessionBtn.addEventListener('click', () => closeModal(editSessionModal, editSessionForm));

}

if (editSessionModal) {

  setupBackdropClose(editSessionModal, editSessionForm);

}



// Submission guard to prevent duplicate concurrent edits

let isSubmittingEditSession = false;



// Handle Edit Session Form Submission

if (editSessionForm) {

  editSessionForm.addEventListener('submit', async function (event) {

    event.preventDefault();

    if (!currentDetailsGroupId) return;



    if (isSubmittingEditSession) return;

    isSubmittingEditSession = true;



    const sessionId = editSessionIdInput ? editSessionIdInput.value : null;

    if (!sessionId) return;



    clearFormErrors(editSessionForm);

    if (editSessionGeneralError) editSessionGeneralError.textContent = '';



    const title = editSessionTitleInput ? editSessionTitleInput.value.trim() : '';

    const desc = editSessionDescInput ? editSessionDescInput.value.trim() : '';

    const dateVal = editSessionDateInput ? editSessionDateInput.value : '';

    const startTimeVal = editSessionStartTimeInput ? editSessionStartTimeInput.value : '';

    const endTimeVal = editSessionEndTimeInput ? editSessionEndTimeInput.value : '';



    let hasError = false;



    if (!title) {

      showFieldError(editSessionTitleInput, editSessionTitleError, 'Session title is required.');

      hasError = true;

    } else if (title.length > 150) {

      showFieldError(editSessionTitleInput, editSessionTitleError, 'Session title must not exceed 150 characters.');

      hasError = true;

    }



    if (!dateVal) {

      showFieldError(editSessionDateInput, editSessionDateError, 'Please select a date.');

      hasError = true;

    }



    if (!startTimeVal) {

      showFieldError(editSessionStartTimeInput, editSessionStartTimeError, 'Please select a start time.');

      hasError = true;

    }



    if (!endTimeVal) {

      showFieldError(editSessionEndTimeInput, editSessionEndTimeError, 'Please select an end time.');

      hasError = true;

    }



    if (hasError) return;



    // Convert local date and times to ISO timestamp without misinterpreting local time as UTC

    const startDateTime = new Date(`${dateVal}T${startTimeVal}:00`);

    const endDateTime = new Date(`${dateVal}T${endTimeVal}:00`);



    if (isNaN(startDateTime.getTime()) || isNaN(endDateTime.getTime())) {

      if (editSessionGeneralError) editSessionGeneralError.textContent = 'Invalid date or time format.';

      return;

    }



    if (endDateTime <= startDateTime) {

      showFieldError(editSessionEndTimeInput, editSessionEndTimeError, 'End time must be later than start time.');

      return;

    }



    try {

      if (submitEditSessionBtn) {

        submitEditSessionBtn.disabled = true;

        submitEditSessionBtn.textContent = 'Saving...';

      }



      const response = await fetch(`${API_BASE_URL}/api/groups/${currentDetailsGroupId}/sessions/${sessionId}`, {

        method: 'PUT',

        headers: getAuthHeaders(),

        body: JSON.stringify({

          title: title,

          description: desc || null,

          start_time: startDateTime.toISOString(),

          end_time: endDateTime.toISOString()

        })

      });



      if (submitEditSessionBtn) {

        submitEditSessionBtn.disabled = false;

        submitEditSessionBtn.textContent = 'Save Changes';

      }



      if (!response.ok) {

        const errData = await response.json().catch(() => ({}));

        if (response.status === 403) {

          if (editSessionGeneralError) {

            editSessionGeneralError.textContent = errData.detail || 'Permission denied. Only the session creator or group owner can edit this session.';

          }

        } else {

          if (editSessionGeneralError) {

            editSessionGeneralError.textContent = errData.detail || 'Could not update study session. Please try again.';

          }

        }

        return;

      }



      const data = await response.json();



      // Close modal

      closeModal(editSessionModal, editSessionForm);



      // Refresh group details (re-fetches group with updated sessions list & stats)

      await openGroupDetails(currentDetailsGroupId);



      // Refresh live dashboard upcoming sessions and its count

      await loadDashboardUpcomingSessions();



      // Show friendly confirmation message

      if (data.calendar_sync_status === 'failed') {

        alert('Study session updated in TeamSync, but Google Calendar synchronization failed.');

      } else {

        alert(data.message || 'Study session updated successfully!');

      }



    } catch (err) {

      console.error('Error updating study session:', err);

      if (editSessionGeneralError) {

        editSessionGeneralError.textContent = 'Failed to connect to backend server. Please verify FastAPI is running.';

      }

    } finally {

      isSubmittingEditSession = false;

      if (submitEditSessionBtn) {

        submitEditSessionBtn.disabled = false;

        submitEditSessionBtn.textContent = 'Save Changes';

      }

    }

  });

}





/* ================================================================

   SECTION 9D: CANCEL STUDY SESSION CONFIRMATION & ACTIONS

   Handles closing confirmation dialog and executing session cancellation.

================================================================ */



// Close or dismiss Cancel Session modal (Keep Session)

if (closeCancelSessionModal) {

  closeCancelSessionModal.addEventListener('click', () => {

    sessionToCancelId = null;

    closeModal(cancelSessionModal);

  });

}

if (keepSessionBtn) {

  keepSessionBtn.addEventListener('click', () => {

    sessionToCancelId = null;

    closeModal(cancelSessionModal);

  });

}

if (cancelSessionModal) {

  setupBackdropClose(cancelSessionModal);

}



// Handle Confirmed Cancellation

if (confirmCancelSessionBtn) {

  confirmCancelSessionBtn.addEventListener('click', async function () {

    if (!currentDetailsGroupId || !sessionToCancelId) return;



    try {

      confirmCancelSessionBtn.disabled = true;

      confirmCancelSessionBtn.textContent = 'Cancelling...';

      if (cancelSessionGeneralError) cancelSessionGeneralError.textContent = '';



      const response = await fetch(`${API_BASE_URL}/api/groups/${currentDetailsGroupId}/sessions/${sessionToCancelId}`, {

        method: 'DELETE',

        headers: getAuthHeaders(false)

      });



      confirmCancelSessionBtn.disabled = false;

      confirmCancelSessionBtn.textContent = 'Yes, Cancel Session';



      if (!response.ok) {

        const errData = await response.json().catch(() => ({}));

        if (response.status === 401) {

          if (cancelSessionGeneralError) cancelSessionGeneralError.textContent = 'Session expired. Please log in again.';

        } else if (response.status === 403) {

          if (cancelSessionGeneralError) cancelSessionGeneralError.textContent = errData.detail || 'Permission denied. Only the session creator or group owner can cancel this session.';

        } else if (response.status === 404) {

          if (cancelSessionGeneralError) cancelSessionGeneralError.textContent = 'Study session not found or already cancelled.';

        } else {

          if (cancelSessionGeneralError) cancelSessionGeneralError.textContent = errData.detail || 'Could not cancel study session. Please try again.';

        }

        return;

      }



      const data = await response.json();



      // Close modal and clear active ID

      closeModal(cancelSessionModal);

      sessionToCancelId = null;



      // Refresh group details (re-fetches group with updated sessions list & stats)

      await openGroupDetails(currentDetailsGroupId);



      // Refresh live dashboard upcoming sessions and its count

      await loadDashboardUpcomingSessions();



      // Check Google Calendar synchronization status

      if (data.calendar_delete_queued) {

        alert("Study session cancelled in TeamSync! Google Calendar event removal has been scheduled in the background 🗑️");

      } else if (data.calendar_sync_status === 'failed') {

        alert("The study session was cancelled in TeamSync, but removing it from Google Calendar failed. Its Google Calendar event may still exist.");

      } else {

        alert(data.message || 'Study session cancelled successfully!');

      }



    } catch (err) {

      console.error('Error cancelling study session:', err);

      if (confirmCancelSessionBtn) {

        confirmCancelSessionBtn.disabled = false;

        confirmCancelSessionBtn.textContent = 'Yes, Cancel Session';

      }

      if (cancelSessionGeneralError) {

        cancelSessionGeneralError.textContent = 'Failed to connect to backend server. Please verify FastAPI is running.';

      }

    }

  });

}





/* ================================================================

   SECTION 10: INITIALIZE THE APP

   Set up the initial state of the application.

================================================================ */



/* ================================================================
   SECTION 5B: FUNCTIONAL SIDEBAR NAVIGATION & DEDICATED SUBVIEWS
   Manages subviews for: Dashboard, My Groups, Sessions, Tasks, Settings.
   Synchronizes sidebar link highlights, hash navigation, and data loading.
================================================================ */

let currentDashboardView = 'dashboard';
let currentGlobalSessionFilter = 'all';
let currentGlobalTaskFilter = 'all';

/**
 * Reusable helper to switch between dashboard subviews.
 * @param {string} viewName - 'dashboard', 'groups', 'sessions', 'tasks', or 'settings'
 * @param {boolean} updateUrlHash - whether to update window.location.hash
 */
function showDashboardView(viewName = 'dashboard', updateUrlHash = true) {
  const validViews = ['dashboard', 'groups', 'sessions', 'tasks', 'settings'];
  if (!validViews.includes(viewName)) {
    viewName = 'dashboard';
  }
  currentDashboardView = viewName;

  // Ensure dashboard page container is visible
  if (!dashboardPage.classList.contains('active')) {
    landingPage.classList.remove('active');
    if (groupDetailsPage) groupDetailsPage.classList.remove('active');
    dashboardPage.classList.add('active');
    updateAuthNavigation();
  }

  // Subviews mapping
  const subviewElements = {
    dashboard: document.getElementById('dashboard-view-overview'),
    groups: document.getElementById('dashboard-view-groups'),
    sessions: document.getElementById('dashboard-view-sessions'),
    tasks: document.getElementById('dashboard-view-tasks'),
    settings: document.getElementById('dashboard-view-settings')
  };

  // Toggle subview visibility
  Object.keys(subviewElements).forEach(key => {
    const el = subviewElements[key];
    if (el) {
      if (key === viewName) {
        el.style.display = 'block';
        el.classList.add('active');
      } else {
        el.style.display = 'none';
        el.classList.remove('active');
      }
    }
  });

  // Synchronize sidebar links active state (fixes Settings highlight bug)
  const links = document.querySelectorAll('.sidebar-link');
  links.forEach(link => {
    const sec = link.getAttribute('data-section');
    if (sec === viewName) {
      link.classList.add('active');
    } else {
      link.classList.remove('active');
    }
  });

  // Update browser hash
  if (updateUrlHash && typeof window !== 'undefined' && window.location) {
    if (window.location.hash !== `#${viewName}`) {
      window.location.hash = viewName;
    }
  }

  // Close mobile sidebar if open
  if (sidebar && sidebar.classList.contains('open')) {
    sidebar.classList.remove('open');
    if (hamburgerBtn) hamburgerBtn.setAttribute('aria-expanded', false);
  }

  // Fetch and populate data for the activated view
  if (viewName === 'dashboard') {
    loadGroups();
    loadDashboardUpcomingSessions();
    checkGoogleCalendarStatus();
  } else if (viewName === 'groups') {
    loadMyGroupsView();
  } else if (viewName === 'sessions') {
    loadMySessionsView(currentGlobalSessionFilter);
  } else if (viewName === 'tasks') {
    loadMyTasksView(currentGlobalTaskFilter);
  } else if (viewName === 'settings') {
    loadSettingsView();
  }

  window.scrollTo({ top: 0, behavior: 'smooth' });
}

/**
 * Creates a reusable group card DOM element for My Groups view.
 */
function createGroupCardElement(group) {
  const card = document.createElement('div');
  card.classList.add('group-card');
  card.dataset.groupId = group.id;

  const words = (group.name || 'Group').trim().split(' ');
  const initials = words.length >= 2
    ? words[0][0].toUpperCase() + words[1][0].toUpperCase()
    : (group.name || 'SG').slice(0, 2).toUpperCase();

  const colorIndex = (group.color_index !== undefined ? group.color_index : (group.id % avatarColors.length)) || 0;
  const colorClass = avatarColors[colorIndex % avatarColors.length];

  const mCount = group.member_count !== undefined ? group.member_count : (group.members_count || 1);
  const tCount = group.task_count !== undefined ? group.task_count : (group.tasks_count || 0);
  const sCount = group.session_count !== undefined ? group.session_count : (group.sessions_count || 0);

  const subjectHtml = group.subject ? `<p class="group-subject" style="font-size: 13px; color: var(--color-primary); font-weight: 600; margin-bottom: 6px;">📚 ${escapeHtml(group.subject)}</p>` : '';

  card.innerHTML = `
    <div class="group-header">
      <div class="group-avatar ${colorClass}">${escapeHtml(initials)}</div>
      <span class="group-badge badge-active">Active</span>
    </div>
    <div class="group-body">
      <h3 class="group-name">${escapeHtml(group.name)}</h3>
      ${subjectHtml}
      <p class="group-desc">${escapeHtml(group.description || 'No description provided.')}</p>
    </div>
    <div class="group-meta" style="display: flex; gap: 12px; font-size: 12px; color: var(--color-text-muted); margin-bottom: var(--space-4); padding: 8px 0; border-top: 1px solid var(--color-border); border-bottom: 1px solid var(--color-border);">
      <span>👥 <strong>${mCount}</strong> ${mCount === 1 ? 'member' : 'members'}</span>
      <span>✅ <strong>${tCount}</strong> ${tCount === 1 ? 'task' : 'tasks'}</span>
      <span>🗓️ <strong>${sCount}</strong> ${sCount === 1 ? 'session' : 'sessions'}</span>
    </div>
    <div class="group-footer">
      <button class="btn btn-primary-small group-open-btn" style="width: 100%;">Open →</button>
    </div>
  `;

  const openBtn = card.querySelector('.group-open-btn');
  if (openBtn) {
    openBtn.addEventListener('click', () => openGroupDetails(group.id));
  }

  return card;
}

/**
 * Loads and displays groups belonging to the user in the My Groups view.
 */
async function loadMyGroupsView() {
  const grid = document.getElementById('my-groups-full-grid');
  if (!grid) return;
  const token = getAuthToken();
  if (!token) return;

  grid.innerHTML = `
    <div style="grid-column: 1 / -1; text-align: center; padding: 40px 20px;">
      <div class="details-spinner" style="margin: 0 auto 12px;"></div>
      <p style="color: var(--color-text-muted); font-size: 14px;">Loading your study groups...</p>
    </div>
  `;

  try {
    const response = await fetch(`${API_BASE_URL}/api/groups`, {
      headers: getAuthHeaders(false)
    });
    if (!response.ok) throw new Error('Failed to fetch groups');
    const data = await response.json();
    const groups = data.groups || [];

    grid.innerHTML = '';
    if (groups.length === 0) {
      grid.innerHTML = `
        <div style="grid-column: 1 / -1; text-align: center; padding: 48px 20px; background: var(--color-surface); border: 1px dashed var(--color-border); border-radius: var(--radius-lg);">
          <p style="font-size: 2.4rem; margin-bottom: 10px;">👥</p>
          <h3 style="font-size: 1.25rem; color: var(--color-text); margin-bottom: 8px;">No Study Groups Yet</h3>
          <p style="font-size: 14px; color: var(--color-text-muted); max-width: 440px; margin: 0 auto 20px;">
            You aren't a member of any study groups yet. Create a new group to study together with classmates, or join an existing group using an invitation code.
          </p>
          <div style="display: inline-flex; gap: 10px; justify-content: center; flex-wrap: wrap;">
            <button class="btn btn-primary" onclick="openModal(createGroupModal)">+ Create Group</button>
            <button class="btn btn-outline" onclick="openModal(joinGroupModal)">🔗 Join Group</button>
          </div>
        </div>
      `;
      return;
    }

    groups.forEach(group => {
      const card = createGroupCardElement(group);
      grid.appendChild(card);
    });
  } catch (err) {
    console.error('Error loading my groups view:', err);
    grid.innerHTML = `
      <div style="grid-column: 1 / -1; text-align: center; padding: 32px; color: var(--color-error);">
        <p>⚠️ Failed to load study groups. Please check your connection and try again.</p>
      </div>
    `;
  }
}

/**
 * Loads all sessions (upcoming, past, or all) for the dedicated Sessions view.
 */
async function loadMySessionsView(filter = currentGlobalSessionFilter) {
  currentGlobalSessionFilter = filter;
  const list = document.getElementById('my-sessions-full-list');
  if (!list) return;
  const token = getAuthToken();
  if (!token) return;

  const tabs = document.querySelectorAll('#sessions-filter-tabs .task-filter-tab');
  tabs.forEach(tab => {
    if (tab.getAttribute('data-session-filter') === filter) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });

  list.innerHTML = `
    <div style="text-align: center; padding: 40px 20px;">
      <div class="details-spinner" style="margin: 0 auto 12px;"></div>
      <p style="color: var(--color-text-muted); font-size: 14px;">Loading sessions...</p>
    </div>
  `;

  try {
    const response = await fetch(`${API_BASE_URL}/api/sessions?filter=${filter}`, {
      headers: getAuthHeaders(false)
    });
    if (!response.ok) throw new Error('Failed to fetch sessions');
    const data = await response.json();
    const sessions = data.sessions || [];

    list.innerHTML = '';
    if (sessions.length === 0) {
      const filterLabel = filter === 'past' ? 'past' : (filter === 'upcoming' ? 'upcoming' : '');
      list.innerHTML = `
        <div class="sessions-empty" style="text-align: center; padding: 40px 20px; background: var(--color-surface); border: 1px dashed var(--color-border); border-radius: var(--radius-lg);">
          <p style="font-size: 2rem; margin-bottom: 8px;">🗓️</p>
          <h3 style="font-size: 1.15rem; color: var(--color-text); margin-bottom: 6px;">No ${filterLabel} study sessions found</h3>
          <p style="font-size: 13px; color: var(--color-text-muted); max-width: 420px; margin: 0 auto 16px;">
            ${filter === 'upcoming' ? 'Schedule a session inside any of your study groups to see it here.' : 'No sessions match this filter.'}
          </p>
          <button class="btn btn-outline-small" onclick="showDashboardView('groups')">Go to My Groups</button>
        </div>
      `;
      return;
    }

    sessions.forEach(session => {
      const el = createSessionElement(session);
      if (session.group_id) {
        const actionBtn = document.createElement('button');
        actionBtn.className = 'btn btn-ghost-small';
        actionBtn.style.marginLeft = 'auto';
        actionBtn.style.fontSize = '12px';
        actionBtn.textContent = 'Open Group →';
        actionBtn.onclick = (e) => {
          e.stopPropagation();
          openGroupDetails(session.group_id);
        };
        el.appendChild(actionBtn);
      }
      list.appendChild(el);
    });
  } catch (err) {
    console.error('Error loading my sessions view:', err);
    list.innerHTML = `
      <div style="text-align: center; padding: 32px; color: var(--color-error);">
        <p>⚠️ Could not load sessions. Please check your connection and try again.</p>
      </div>
    `;
  }
}

/**
 * Loads tasks across all user groups for the dedicated Tasks view.
 */
async function loadMyTasksView(filter = currentGlobalTaskFilter) {
  currentGlobalTaskFilter = filter;
  const list = document.getElementById('my-tasks-full-list');
  if (!list) return;
  const token = getAuthToken();
  if (!token) return;

  const tabs = document.querySelectorAll('#tasks-filter-tabs .task-filter-tab');
  tabs.forEach(tab => {
    if (tab.getAttribute('data-task-filter') === filter) {
      tab.classList.add('active');
    } else {
      tab.classList.remove('active');
    }
  });

  list.innerHTML = `
    <div style="text-align: center; padding: 40px 20px;">
      <div class="details-spinner" style="margin: 0 auto 12px;"></div>
      <p style="color: var(--color-text-muted); font-size: 14px;">Loading tasks...</p>
    </div>
  `;

  try {
    const response = await fetch(`${API_BASE_URL}/api/tasks`, {
      headers: getAuthHeaders(false)
    });
    if (!response.ok) throw new Error('Failed to fetch tasks');
    const data = await response.json();
    const allTasks = data.tasks || [];

    const total = allTasks.length;
    const pending = allTasks.filter(t => (t.status || '').toLowerCase() === 'pending').length;
    const inProgress = allTasks.filter(t => (t.status || '').toLowerCase() === 'in_progress').length;
    const completed = allTasks.filter(t => (t.status || '').toLowerCase() === 'completed').length;
    const rate = total > 0 ? Math.round((completed / total) * 100) : 0;

    const elTotal = document.getElementById('user-tasks-total');
    const elPending = document.getElementById('user-tasks-pending');
    const elInProg = document.getElementById('user-tasks-inprogress');
    const elCompleted = document.getElementById('user-tasks-completed');
    const elRate = document.getElementById('user-tasks-rate');
    const elFill = document.getElementById('user-tasks-progress-fill');

    if (elTotal) elTotal.textContent = total;
    if (elPending) elPending.textContent = pending;
    if (elInProg) elInProg.textContent = inProgress;
    if (elCompleted) elCompleted.textContent = completed;
    if (elRate) elRate.textContent = `${rate}%`;
    if (elFill) elFill.style.width = `${rate}%`;

    if (dashboardTasksCount) {
      dashboardTasksCount.textContent = pending + inProgress;
    }

    const displayedTasks = allTasks.filter(t => {
      if (filter === 'all') return true;
      return (t.status || 'pending').toLowerCase() === filter.toLowerCase();
    });

    list.innerHTML = '';
    if (displayedTasks.length === 0) {
      const filterMsg = filter === 'all'
        ? "No tasks found across your study groups. Create tasks inside your groups to track assignments."
        : `No ${filter.replace('_', ' ')} tasks found.`;
      list.innerHTML = `
        <div class="tasks-empty" style="text-align: center; padding: 40px 20px; background: var(--color-surface); border: 1px dashed var(--color-border); border-radius: var(--radius-lg);">
          <p style="font-size: 2rem; margin-bottom: 8px;">✅</p>
          <h3 style="font-size: 1.15rem; color: var(--color-text); margin-bottom: 6px;">No Tasks Found</h3>
          <p style="font-size: 13px; color: var(--color-text-muted); max-width: 420px; margin: 0 auto 16px;">
            ${filterMsg}
          </p>
          <button class="btn btn-outline-small" onclick="showDashboardView('groups')">Go to Study Groups</button>
        </div>
      `;
      return;
    }

    displayedTasks.forEach(task => {
      const card = document.createElement('div');
      const status = (task.status || 'pending').toLowerCase();
      card.classList.add('task-card', `is-${status.replace('_', '')}`);
      card.dataset.taskId = task.id;

      let statusBadgeHtml = '';
      if (status === 'completed') {
        statusBadgeHtml = `<span class="task-status-badge badge-completed">✅ Completed</span>`;
      } else if (status === 'in_progress') {
        statusBadgeHtml = `<span class="task-status-badge badge-inprogress">🔄 In Progress</span>`;
      } else {
        statusBadgeHtml = `<span class="task-status-badge badge-pending">⏳ Pending</span>`;
      }

      const groupName = task.group_name || 'Study Group';
      const groupPill = `<span class="task-pill" style="cursor: pointer;" title="Open ${escapeHtml(groupName)}">📚 <strong>${escapeHtml(groupName)}</strong></span>`;

      let assigneeHtml = '';
      if (task.assignee && task.assignee.name) {
        assigneeHtml = `<span class="task-pill" title="Assigned to ${escapeHtml(task.assignee.name)}">👤 <strong>${escapeHtml(task.assignee.name)}</strong></span>`;
      } else {
        assigneeHtml = `<span class="task-pill" style="opacity: 0.7;">👤 Unassigned</span>`;
      }

      let dueHtml = '';
      if (task.due_date_formatted) {
        if (task.is_overdue) {
          dueHtml = `<span class="task-pill task-pill-overdue" title="Overdue: ${escapeHtml(task.due_date_formatted)}">⚠️ Overdue: ${escapeHtml(task.due_date_formatted)}</span>`;
        } else {
          dueHtml = `<span class="task-pill" title="Due: ${escapeHtml(task.due_date_formatted)}">📅 Due: ${escapeHtml(task.due_date_formatted)}</span>`;
        }
      } else {
        dueHtml = `<span class="task-pill" style="opacity: 0.7;">📅 No deadline</span>`;
      }

      card.innerHTML = `
        <div class="task-header-row">
          <h4 class="task-title">${escapeHtml(task.title)}</h4>
          ${statusBadgeHtml}
        </div>
        ${task.description ? `<p class="task-desc">${escapeHtml(task.description)}</p>` : ''}
        <div class="task-footer-row">
          <div class="task-meta-left" style="display: flex; gap: 8px; flex-wrap: wrap;">
            ${groupPill}
            ${assigneeHtml}
            ${dueHtml}
          </div>
          <div class="task-meta-right" style="display: flex; align-items: center; gap: 6px;">
            <label style="font-size: 11px; color: var(--color-text-muted); font-weight: 600;">Status:</label>
            <select class="task-status-select" data-task-id="${task.id}" data-group-id="${task.group_id}" aria-label="Change task status">
              <option value="pending" ${status === 'pending' ? 'selected' : ''}>⏳ Pending</option>
              <option value="in_progress" ${status === 'in_progress' ? 'selected' : ''}>🔄 In Progress</option>
              <option value="completed" ${status === 'completed' ? 'selected' : ''}>✅ Completed</option>
            </select>
          </div>
        </div>
      `;

      const gPillEl = card.querySelector('.task-meta-left span:first-child');
      if (gPillEl && task.group_id) {
        gPillEl.addEventListener('click', () => openGroupDetails(task.group_id));
      }

      const selectEl = card.querySelector('.task-status-select');
      if (selectEl) {
        selectEl.addEventListener('change', async function () {
          const newStatus = this.value;
          const taskId = this.dataset.taskId;
          const groupId = this.dataset.groupId;
          this.disabled = true;
          try {
            const patchRes = await fetch(`${API_BASE_URL}/api/groups/${groupId}/tasks/${taskId}/status`, {
              method: 'PATCH',
              headers: getAuthHeaders(),
              body: JSON.stringify({ status: newStatus })
            });
            if (!patchRes.ok) throw new Error('Status update failed');
            await loadMyTasksView(currentGlobalTaskFilter);
          } catch (patchErr) {
            console.error('Error updating task status:', patchErr);
            alert('Failed to update task status. Please try again.');
            this.disabled = false;
          }
        });
      }

      list.appendChild(card);
    });
  } catch (err) {
    console.error('Error loading my tasks view:', err);
    list.innerHTML = `
      <div style="text-align: center; padding: 32px; color: var(--color-error);">
        <p>⚠️ Could not load tasks. Please check your connection and try again.</p>
      </div>
    `;
  }
}

/**
 * Loads account information and Google Calendar status for the Settings view.
 */
async function loadSettingsView() {
  const token = getAuthToken();
  if (!token) return;

  const uName = document.getElementById('settings-user-name');
  const uEmail = document.getElementById('settings-user-email');
  const uId = document.getElementById('settings-user-id');
  const uGroups = document.getElementById('settings-groups-count');
  const calBadge = document.getElementById('settings-calendar-badge');
  const connBtn = document.getElementById('settings-connect-calendar-btn');
  const disconnBtn = document.getElementById('settings-disconnect-calendar-btn');

  const currentUser = getCurrentUser();
  if (currentUser) {
    if (uName) uName.textContent = currentUser.name || '--';
    if (uEmail) uEmail.textContent = currentUser.email || '--';
    if (uId && currentUser.id) uId.textContent = `#${currentUser.id}`;
  }

  try {
    const res = await fetch(`${API_BASE_URL}/api/users/me`, {
      headers: getAuthHeaders(false)
    });
    if (res.ok) {
      const data = await res.json();
      if (uName && data.name) uName.textContent = data.name;
      if (uEmail && data.email) uEmail.textContent = data.email;
      if (uId && data.id) uId.textContent = `#${data.id}`;
      if (uGroups && data.groups_count !== undefined) {
        uGroups.textContent = `${data.groups_count} ${data.groups_count === 1 ? 'group' : 'groups'}`;
      }
    }
  } catch (err) {
    console.error('Error loading user profile in settings:', err);
  }

  try {
    const calRes = await fetch(`${API_BASE_URL}/auth/google/status`, {
      headers: getAuthHeaders(false)
    });
    if (calRes.ok) {
      const calData = await calRes.json();
      if (calData.connected) {
        if (calBadge) {
          calBadge.textContent = 'Connected';
          calBadge.className = 'session-tag session-tag-synced';
        }
        if (connBtn) connBtn.style.display = 'none';
        if (disconnBtn) disconnBtn.style.display = 'inline-block';
      } else if (calData.requires_reconnect) {
        if (calBadge) {
          calBadge.textContent = 'Reconnect Required';
          calBadge.className = 'session-tag session-tag-pending';
        }
        if (connBtn) {
          connBtn.style.display = 'inline-block';
          connBtn.textContent = '🔄 Reconnect Google Calendar';
        }
        if (disconnBtn) disconnBtn.style.display = 'none';
      } else {
        if (calBadge) {
          calBadge.textContent = 'Not Connected';
          calBadge.className = 'session-tag session-tag-not-connected';
        }
        if (connBtn) {
          connBtn.style.display = 'inline-block';
          connBtn.textContent = '📅 Connect Google Calendar';
        }
        if (disconnBtn) disconnBtn.style.display = 'none';
      }
    }
  } catch (calErr) {
    console.error('Error loading calendar status in settings:', calErr);
  }
}

// ── Wire Navigation Actions & Listeners ──
if (typeof window !== 'undefined' && typeof window.addEventListener === 'function') {
  window.addEventListener('hashchange', function () {
    const hash = (window.location && window.location.hash) ? window.location.hash.replace('#', '').trim() : '';
    const user = getCurrentUser();
    const token = getAuthToken();

    if (!user || !token) {
      if (['dashboard', 'groups', 'sessions', 'tasks', 'settings'].includes(hash)) {
        showLanding();
      }
      return;
    }

    if (['dashboard', 'groups', 'sessions', 'tasks', 'settings'].includes(hash)) {
      showDashboardView(hash, false);
    } else if (hash === 'home' || hash === '') {
      showLanding();
    }
  });
}

// View all groups button on dashboard overview
const viewAllGroupsBtn = document.getElementById('view-all-groups-btn');
if (viewAllGroupsBtn) {
  viewAllGroupsBtn.addEventListener('click', () => showDashboardView('groups', true));
}

// View calendar button on dashboard overview
const dashboardViewCalendarBtn = document.getElementById('dashboard-view-calendar-btn');
if (dashboardViewCalendarBtn) {
  dashboardViewCalendarBtn.addEventListener('click', () => showDashboardView('sessions', true));
}

// Create/Join buttons inside My Groups view
const groupsViewCreateBtn = document.getElementById('groups-view-create-btn');
if (groupsViewCreateBtn) {
  groupsViewCreateBtn.addEventListener('click', () => openModal(createGroupModal));
}
const groupsViewJoinBtn = document.getElementById('groups-view-join-btn');
if (groupsViewJoinBtn) {
  groupsViewJoinBtn.addEventListener('click', () => openModal(joinGroupModal));
}

// Filter tabs in Sessions view
const sessionFilterButtons = document.querySelectorAll('#sessions-filter-tabs .task-filter-tab');
sessionFilterButtons.forEach(btn => {
  btn.addEventListener('click', function () {
    const f = this.getAttribute('data-session-filter') || 'all';
    loadMySessionsView(f);
  });
});

// Filter tabs in Tasks view
const taskFilterButtons = document.querySelectorAll('#tasks-filter-tabs .task-filter-tab');
taskFilterButtons.forEach(btn => {
  btn.addEventListener('click', function () {
    const f = this.getAttribute('data-task-filter') || 'all';
    loadMyTasksView(f);
  });
});

// Google Calendar connect / disconnect buttons in Settings view
const settingsConnectCalendarBtn = document.getElementById('settings-connect-calendar-btn');
if (settingsConnectCalendarBtn) {
  settingsConnectCalendarBtn.addEventListener('click', function () {
    if (connectCalendarBtn) connectCalendarBtn.click();
  });
}
const settingsDisconnectCalendarBtn = document.getElementById('settings-disconnect-calendar-btn');
if (settingsDisconnectCalendarBtn) {
  settingsDisconnectCalendarBtn.addEventListener('click', function () {
    if (disconnectCalendarBtn) disconnectCalendarBtn.click();
  });
}

// User Profile Name editing in Settings view
const settingsEditNameBtn = document.getElementById('settings-edit-name-btn');
const settingsNameDisplayWrap = document.getElementById('settings-name-display-wrap');
const settingsEditNameForm = document.getElementById('settings-edit-name-form');
const settingsNameInput = document.getElementById('settings-name-input');
const settingsSaveNameBtn = document.getElementById('settings-save-name-btn');
const settingsCancelNameBtn = document.getElementById('settings-cancel-name-btn');
const settingsNameFeedback = document.getElementById('settings-name-feedback');
const settingsUserNameEl = document.getElementById('settings-user-name');

if (settingsEditNameBtn) {
  settingsEditNameBtn.addEventListener('click', function () {
    if (!settingsNameDisplayWrap || !settingsEditNameForm || !settingsNameInput) return;
    const currentName = (settingsUserNameEl && settingsUserNameEl.textContent !== '--')
      ? settingsUserNameEl.textContent.trim()
      : ((getCurrentUser() && getCurrentUser().name) || '');
    settingsNameInput.value = currentName;
    settingsNameDisplayWrap.style.display = 'none';
    settingsEditNameBtn.style.display = 'none';
    settingsEditNameForm.style.display = 'flex';
    if (settingsNameFeedback) {
      settingsNameFeedback.style.display = 'none';
      settingsNameFeedback.textContent = '';
    }
    settingsNameInput.focus();
  });
}

if (settingsCancelNameBtn) {
  settingsCancelNameBtn.addEventListener('click', function () {
    if (!settingsNameDisplayWrap || !settingsEditNameForm) return;
    settingsEditNameForm.style.display = 'none';
    settingsNameDisplayWrap.style.display = 'block';
    if (settingsEditNameBtn) settingsEditNameBtn.style.display = 'inline-block';
    if (settingsNameFeedback) {
      settingsNameFeedback.style.display = 'none';
      settingsNameFeedback.textContent = '';
    }
  });
}

if (settingsEditNameForm) {
  settingsEditNameForm.addEventListener('submit', async function (e) {
    e.preventDefault();
    if (!settingsNameInput) return;
    const newName = settingsNameInput.value.trim();
    if (!newName) {
      if (settingsNameFeedback) {
        settingsNameFeedback.textContent = 'Please enter a valid name.';
        settingsNameFeedback.style.color = '#ef4444';
        settingsNameFeedback.style.display = 'block';
      }
      return;
    }

    if (settingsSaveNameBtn) {
      settingsSaveNameBtn.disabled = true;
      settingsSaveNameBtn.textContent = 'Saving...';
    }

    try {
      const res = await fetch(`${API_BASE_URL}/api/users/me`, {
        method: 'PUT',
        headers: getAuthHeaders(true),
        body: JSON.stringify({ name: newName })
      });
      const data = await res.json();
      if (res.ok && data.success) {
        if (settingsUserNameEl) settingsUserNameEl.textContent = newName;
        const u = getCurrentUser();
        if (u) {
          u.name = newName;
          localStorage.setItem('currentUser', JSON.stringify(u));
          updateDashboardUser(u);
        }
        if (settingsNameFeedback) {
          settingsNameFeedback.textContent = 'Name updated successfully!';
          settingsNameFeedback.style.color = '#10b981';
          settingsNameFeedback.style.display = 'block';
        }
        settingsEditNameForm.style.display = 'none';
        settingsNameDisplayWrap.style.display = 'block';
        if (settingsEditNameBtn) settingsEditNameBtn.style.display = 'inline-block';
        setTimeout(() => {
          if (settingsNameFeedback) {
            settingsNameFeedback.style.display = 'none';
          }
        }, 3000);
      } else {
        if (settingsNameFeedback) {
          settingsNameFeedback.textContent = (data && data.detail) || 'Failed to update name.';
          settingsNameFeedback.style.color = '#ef4444';
          settingsNameFeedback.style.display = 'block';
        }
      }
    } catch (err) {
      console.error('Error updating profile name:', err);
      if (settingsNameFeedback) {
        settingsNameFeedback.textContent = 'Network error while updating name.';
        settingsNameFeedback.style.color = '#ef4444';
        settingsNameFeedback.style.display = 'block';
      }
    } finally {
      if (settingsSaveNameBtn) {
        settingsSaveNameBtn.disabled = false;
        settingsSaveNameBtn.textContent = 'Save';
      }
    }
  });
}


/**

 * Initialize the app:

 * - Show the landing page first (it already has class 'active' in HTML)

 * - Nothing else is needed for now — features activate on user interaction

 */

function init() {
  updateAuthNavigation();
  loadPlatformStats();

  const user = getCurrentUser();
  const token = getAuthToken();
  if (user && token) {
    updateDashboardUser(user);
    const hash = window.location.hash.replace('#', '').trim();
    if (['groups', 'sessions', 'tasks', 'settings'].includes(hash)) {
      showDashboard(hash);
    } else {
      showDashboard('dashboard');
    }
    loadLandingPersonalizedData();

  } else {

    resetLandingDefaultData();

    showLanding();

  }



  // Handle Google Calendar redirect parameters

  const urlParams = new URLSearchParams(window.location.search);

  const calendarStatus = urlParams.get('calendar_status');

  const calendarError = urlParams.get('calendar_error');



  if (calendarStatus === 'connected') {

    if (user && token) {

      showDashboard();

      checkGoogleCalendarStatus();

    }

    alert('🎉 Google Calendar connected successfully to TeamSync!');

    // Clean query parameters from URL bar without reloading the page

    const cleanUrl = window.location.pathname + window.location.hash;

    window.history.replaceState({}, document.title, cleanUrl);

  } else if (calendarStatus === 'error') {

    if (user && token) {

      showDashboard();

    }

    alert(calendarError ? `Google Calendar connection: ${calendarError}` : 'Google Calendar connection was cancelled or failed.');

    const cleanUrl = window.location.pathname + window.location.hash;

    window.history.replaceState({}, document.title, cleanUrl);

  }



  // Handle invitation link if page is opened with #invite=CODE

  if (window.location.hash.startsWith('#invite=')) {

    const code = window.location.hash.replace('#invite=', '').trim();

    if (code) {

      if (user) {

        showDashboard();

        openModal(joinGroupModal);

        if (inviteCodeInput) {

          inviteCodeInput.value = code;

        }

      } else {

        openModal(loginModal);

        if (loginGeneralError) {

          loginGeneralError.textContent = `Please log in to join the group with code ${code}.`;

        }

      }

    }

  }



    initThemeToggle();

  console.log('TeamSync initialized successfully ✅');

}



// Run init when the DOM is fully loaded

// Since this script is at the bottom of <body>, the DOM is already ready,

// but this is a good defensive practice.

document.addEventListener('DOMContentLoaded', init);



// ================================================================
// THEME SWITCHER (Dark Mode with #001514 as Primary Surface)
// ================================================================
function updateThemeIcons(theme) {
  const icon = theme === 'dark' ? '☀️' : '🌙';
  const label = theme === 'dark' ? 'Switch to Light Mode' : 'Switch to Dark Mode';
  document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
    btn.setAttribute('title', label);
    btn.setAttribute('aria-label', label);
    const span = btn.querySelector('.theme-icon');
    if (span) span.textContent = icon;
  });
}

function initThemeToggle() {
  const savedTheme = (typeof localStorage !== 'undefined' && localStorage.getItem('teamsync-theme')) || 'light';
  if (typeof document !== 'undefined' && document.documentElement) {
    document.documentElement.setAttribute('data-theme', savedTheme);
  }
  updateThemeIcons(savedTheme);

  document.querySelectorAll('.theme-toggle-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      const current = document.documentElement.getAttribute('data-theme') || 'light';
      const next = current === 'dark' ? 'light' : 'dark';
      document.documentElement.setAttribute('data-theme', next);
      try {
        localStorage.setItem('teamsync-theme', next);
      } catch (e) {}
      updateThemeIcons(next);
    });
  });

  const bottomCtaBtn = document.getElementById('bottom-cta-btn');
  if (bottomCtaBtn && typeof handleSignupCta === 'function') {
    bottomCtaBtn.addEventListener('click', handleSignupCta);
  }
}
