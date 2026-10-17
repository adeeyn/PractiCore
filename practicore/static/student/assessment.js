/* Assessment page: open / close the "Your competency profile" panel.
   The panel animates with CSS; this only flips the "open" class and keeps
   aria-expanded in sync so screen readers and the keyboard work too. */
(function () {
  var panel = document.getElementById('assess-sec');
  var toggle = document.getElementById('assess-profile-toggle');
  if (!panel || !toggle) { return; }

  function setOpen(open) {
    panel.classList.toggle('open', open);
    toggle.setAttribute('aria-expanded', open ? 'true' : 'false');
  }

  toggle.addEventListener('click', function () {
    setOpen(!panel.classList.contains('open'));
  });

  // role="button" elements must react to Enter and Space like a real button
  toggle.addEventListener('keydown', function (event) {
    if (event.key === 'Enter' || event.key === ' ') {
      event.preventDefault();
      setOpen(!panel.classList.contains('open'));
    }
  });
})();
