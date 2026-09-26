// Employer module scripts (loaded on every employer page)

document.addEventListener('DOMContentLoaded', () => {
  // Render <i data-lucide="..."> icons
  if (window.lucide) window.lucide.createIcons();

  initTagInputs();
  initApplicantFilter();
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
