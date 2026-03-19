/**
 * AUTH.JS — Authentication Guard for AI Fundamental Terminal
 * Include via <script src="auth.js"></script> as FIRST script in <head>
 * 
 * Checks localStorage for a valid session. If none found → redirect to login.html
 * Exposes window.NQ_AUTH = { user, email, logout() }
 */
(function () {
  'use strict';

  const SESSION_KEY = 'nq_whale_session';
  const SESSION_MAX_AGE = 24 * 60 * 60 * 1000; // 24 hours
  const LOGIN_PAGE = 'login.html';

  // Don't guard the login page or the index (index uses auth_gate.js modal)
  const currentPage = window.location.pathname.split('/').pop() || 'index.html';
  if (currentPage === LOGIN_PAGE || currentPage === 'index.html') return;

  // Check for valid session
  let session = null;
  try {
    session = JSON.parse(localStorage.getItem(SESSION_KEY));
  } catch (e) {
    session = null;
  }

  const isValid = session
    && session.user
    && session.timestamp
    && (Date.now() - session.timestamp < SESSION_MAX_AGE);

  if (!isValid) {
    // Clear expired/invalid session
    localStorage.removeItem(SESSION_KEY);
    // Save current page so login can redirect back
    sessionStorage.setItem('nq_redirect', currentPage);
    // Redirect to login
    window.location.replace(LOGIN_PAGE);
    // Stop page execution — nothing else should render
    document.documentElement.innerHTML = '';
    return;
  }

  // ✅ Valid session — expose auth API
  window.NQ_AUTH = {
    user: session.user,
    email: session.email,
    logout: function () {
      localStorage.removeItem(SESSION_KEY);
      window.location.replace(LOGIN_PAGE);
    }
  };
})();
