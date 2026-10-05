// Employer module scripts (loaded on every employer page)

document.addEventListener('DOMContentLoaded', () => {
  // Render <i data-lucide="..."> icons
  if (window.lucide) window.lucide.createIcons();

  initTagInputs();
  initApplicantFilter();
  initLogoUpload();
  initDemoForms();
});

/* ---------- Toast ---------- */
function showToast(message) {
  let toast = document.querySelector('.toast');
  if (!toast) {
    toast = document.createElement('div');
    toast.className = 'toast';
    document.body.appendChild(toast);
  }
  toast.textContent = message;
  toast.classList.add('show');
  clearTimeout(toast._timer);
  toast._timer = setTimeout(() => toast.classList.remove('show'), 3000);
}

/* ---------- Skill tag input (Internship Posting) ----------
   Markup: <div class="tag-input" data-tag-input data-target="hiddenInputId"> ... </div>
   Tags are mirrored into the hidden input as a comma-separated list. */
function initTagInputs() {
  document.querySelectorAll('[data-tag-input]').forEach(box => {
    const field = box.querySelector('.tag-input-field');
    const hidden = document.getElementById(box.dataset.target);

    const tags = () => Array.from(box.querySelectorAll('.skill-tag')).map(t => t.dataset.value);
    const sync = () => { if (hidden) hidden.value = tags().join(', '); };

    function addTag(value) {
      const clean = value.trim().replace(/,$/, '');
      if (!clean || tags().some(t => t.toLowerCase() === clean.toLowerCase())) return;

      const tag = document.createElement('span');
      tag.className = 'skill-tag';
      tag.dataset.value = clean;
      tag.innerHTML = '<i data-lucide="tag"></i><span></span>' +
        '<button type="button" class="skill-tag-remove" aria-label="Remove skill">&times;</button>';
      tag.querySelector('span').textContent = clean;
      box.insertBefore(tag, field);
      if (window.lucide) window.lucide.createIcons();
      sync();
    }

    box.addEventListener('click', (e) => {
      if (e.target.closest('.skill-tag-remove')) {
        e.target.closest('.skill-tag').remove();
        sync();
        return;
      }
      field.focus();
    });

    field.addEventListener('keydown', (e) => {
      if (e.key === 'Enter' || e.key === ',') {
        e.preventDefault();
        addTag(field.value);
        field.value = '';
      } else if (e.key === 'Backspace' && !field.value) {
        const last = box.querySelectorAll('.skill-tag');
        if (last.length) { last[last.length - 1].remove(); sync(); }
      }
    });

    field.addEventListener('blur', () => {
      if (field.value.trim()) { addTag(field.value); field.value = ''; }
    });

    // Tags rendered by the server
    box.querySelectorAll('.skill-tag').forEach(() => sync());
    sync();
  });
}

/* ---------- Applicant search + status filter (Applicants) ---------- */
function initApplicantFilter() {
  const search = document.getElementById('applicant-search');
  const filter = document.getElementById('status-filter');
  const rows = document.querySelectorAll('[data-applicant-row]');
  const empty = document.getElementById('applicants-empty');
  if (!search || !rows.length) return;

  function apply() {
    const q = search.value.trim().toLowerCase();
    const status = filter ? filter.value : '';
    let visible = 0;

    rows.forEach(row => {
      const matchesText = !q || row.dataset.name.toLowerCase().includes(q);
      const matchesStatus = !status || row.dataset.status === status;
      row.hidden = !(matchesText && matchesStatus);
      if (!row.hidden) visible++;
    });

    if (empty) empty.hidden = visible > 0;
  }

  search.addEventListener('input', apply);
  if (filter) filter.addEventListener('change', apply);
}

/* ---------- Company logo upload (Company Profile) ----------
   Markup: #company-logo (preview box), #logo-pick / #logo-remove (buttons),
   #logo-input (file input), #logo-status (live region).
   The endpoint is read from the page so employer.js stays route-agnostic. */
function initLogoUpload() {
  const pick = document.getElementById('logo-pick');
  const input = document.getElementById('logo-input');
  const preview = document.getElementById('company-logo');
  if (!pick || !input || !preview) return;

  const remove = document.getElementById('logo-remove');
  const status = document.getElementById('logo-status');
  const endpoint = pick.dataset.logoEndpoint || '/employer/profile/logo';

  const say = (message, isError) => {
    if (!status) return;
    status.textContent = message;
    status.classList.toggle('error', !!isError);
  };

  // The employer can leave the page or press Back while this is in flight, and
  // an expired session comes back as a redirect to the login HTML, not JSON.
  const postJson = (options) => fetch(endpoint, options)
    .then(res => {
      const type = res.headers.get('content-type') || '';
      if (!type.includes('application/json')) {
        return Promise.reject({ error: 'Your session expired. Please log in again.' });
      }
      return res.json().then(data => ({ ok: res.ok, data: data }));
    })
    .then(({ ok, data }) => {
      if (!ok || data.status !== 'success') throw data;
      return data;
    });

  const showLogo = (url) => {
    preview.classList.add('has-image');
    preview.innerHTML = '';
    const img = document.createElement('img');
    img.src = url;
    img.alt = 'Company logo';
    preview.appendChild(img);
  };

  const showInitials = (text) => {
    preview.classList.remove('has-image');
    preview.textContent = text || '?';
  };

  pick.addEventListener('click', () => input.click());

  input.addEventListener('change', () => {
    const file = input.files[0];
    if (!file) return;

    const body = new FormData();
    body.append('logo', file);

    say('Uploading...', false);
    postJson({ method: 'POST', body: body })
      .then(data => {
        showLogo(data.logo_url);
        // The Remove button is only rendered server-side when a logo exists,
        // so it has to be created the first time one is uploaded.
        if (!document.getElementById('logo-remove')) {
          const button = document.createElement('button');
          button.type = 'button';
          button.className = 'btn btn-outline btn-sm';
          button.id = 'logo-remove';
          button.innerHTML = '<i data-lucide="trash-2"></i> Remove';
          button.addEventListener('click', removeLogo);
          pick.parentNode.appendChild(button);
          if (window.lucide) window.lucide.createIcons();
        }
        say('Logo updated.', false);
      })
      .catch(err => say((err && err.error) ? err.error : 'Upload failed. Please try again.', true))
      .finally(() => { input.value = ''; });
  });

  function removeLogo() {
    say('Removing...', false);
    postJson({ method: 'DELETE' })
      .then(data => {
        showInitials(data.logo_text);
        const button = document.getElementById('logo-remove');
        if (button) button.remove();
        say('Logo removed.', false);
      })
      .catch(err => say((err && err.error) ? err.error : 'Could not remove the logo.', true));
  }

  if (remove) remove.addEventListener('click', removeLogo);
}

/* ---------- Forms / buttons not wired to the backend yet ---------- */
function initDemoForms() {
  document.querySelectorAll('form[data-demo]').forEach(form => {
    form.addEventListener('submit', (e) => {
      e.preventDefault();
      showToast(form.dataset.demo || 'Saving is not connected to the database yet.');
    });
  });

  document.querySelectorAll('[data-demo-action]').forEach(btn => {
    btn.addEventListener('click', (e) => {
      e.preventDefault();
      showToast(btn.dataset.demoAction);
    });
  });
}
