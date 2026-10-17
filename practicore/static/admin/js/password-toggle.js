/* Show/hide button on password fields (partner company form). */
(function () {
  'use strict';
  document.querySelectorAll('input[type="password"]').forEach(function (input) {
    var wrap = document.createElement('div');
    wrap.className = 'adm-pw';
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    var btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'adm-pw-toggle';
    btn.setAttribute('aria-label', 'Show password');
    btn.innerHTML = '<i data-lucide="eye"></i>';
    btn.addEventListener('click', function () {
      var show = input.type === 'password';
      input.type = show ? 'text' : 'password';
      btn.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
      btn.innerHTML = '<i data-lucide="' + (show ? 'eye-off' : 'eye') + '"></i>';
      if (window.lucide) { window.lucide.createIcons(); }
    });
    wrap.appendChild(btn);
  });
  if (window.lucide) { window.lucide.createIcons(); }
})();
