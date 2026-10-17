/* Administrator module script (loaded by admin/base.html on every admin page). */
(function () {
  'use strict';

  if (window.lucide) { window.lucide.createIcons(); }

  // ----- Burger menu: slide the violet sidebar drawer in over a dimmed
  // backdrop. Closed via the dimmed area, the x button, or Escape.
  var toggleBtn = document.getElementById('sidebar-toggle');
  var closeBtn = document.getElementById('sidebar-close');
  var sidebar = document.getElementById('adm-sidebar');
  var overlay = document.getElementById('sidebar-overlay');

  function setOpen(open) {
    if (!sidebar) { return; }
    sidebar.classList.toggle('open', open);
    document.body.classList.toggle('adm-no-scroll', open);
    if (overlay) { overlay.hidden = !open; }
    if (toggleBtn) { toggleBtn.setAttribute('aria-expanded', open ? 'true' : 'false'); }
    if (open && closeBtn) { closeBtn.focus(); }
  }
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', function () {
      setOpen(!sidebar.classList.contains('open'));
    });
  }
  if (closeBtn) { closeBtn.addEventListener('click', function () { setOpen(false); }); }
  if (overlay) { overlay.addEventListener('click', function () { setOpen(false); }); }
  document.addEventListener('keydown', function (e) {
    if (e.key === 'Escape') { setOpen(false); }
  });

  // ----- Header greeting uses the visitor's own clock.
  var greeting = document.getElementById('adm-header-greeting');
  if (greeting) {
    var h = new Date().getHours();
    greeting.textContent = h < 12 ? 'Good morning,' : h < 18 ? 'Good afternoon,' : 'Good evening,';
  }

  // ----- Confirm before any form marked data-confirm (status changes).
  document.addEventListener('submit', function (event) {
    var form = event.target;
    if (!form.dataset || !form.dataset.confirm) { return; }
    if (!window.confirm(form.dataset.confirm)) { event.preventDefault(); }
  });

  // ----- A logged-out page can still be restored from the browser cache on
  // Back, so re-check the session and send the user to login if it has gone.
  window.addEventListener('pageshow', function (event) {
    if (!event.persisted) { return; }
    fetch('/', { method: 'HEAD', cache: 'no-store' })
      .then(function (response) {
        var target = new URL(response.url, window.location.origin);
        if (target.pathname === '/login') { window.location.replace(target.href); }
      })
      .catch(function () { /* offline or blocked: leave the page as it is */ });
  });
})();
