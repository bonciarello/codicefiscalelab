/**
 * CodiceFiscaleLab — Frontend logic
 * Form submission, validation UI, results rendering.
 */

const form = document.getElementById('cf-form');
const input = document.getElementById('cf-input');
const errorEl = document.getElementById('cf-error');
const resultsSection = document.getElementById('results');
const inputWrapper = input.closest('.input-wrapper');
const submitBtn = form.querySelector('.submit-btn');

// Block type definitions for the breakdown
const BLOCK_TYPES = [
  { key: 'cognome',   start: 0,  end: 3,  label: 'Cognome' },
  { key: 'nome',      start: 3,  end: 6,  label: 'Nome' },
  { key: 'anno',      start: 6,  end: 8,  label: 'Anno' },
  { key: 'mese',      start: 8,  end: 9,  label: 'Mese' },
  { key: 'giorno',    start: 9,  end: 11, label: 'Giorno' },
  { key: 'catastale', start: 11, end: 15, label: 'Comune' },
  { key: 'cin',       start: 15, end: 16, label: 'Contr.' },
];

/**
 * Auto-uppercase and filter input
 */
input.addEventListener('input', () => {
  input.value = input.value.toUpperCase().replace(/[^A-Z0-9]/g, '');
  clearError();
});

/**
 * Clear error state
 */
function clearError() {
  errorEl.textContent = '';
  inputWrapper.classList.remove('input-error');
}

/**
 * Show error
 */
function showError(msg) {
  errorEl.textContent = msg;
  inputWrapper.classList.add('input-error');
}

/**
 * Show loading state
 */
function setLoading(loading) {
  if (loading) {
    submitBtn.classList.add('loading');
    submitBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83"/></svg>`;
  } else {
    submitBtn.classList.remove('loading');
    submitBtn.innerHTML = `<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M9 18l6-6-6-6"/></svg>`;
  }
}

/**
 * Form submit
 */
form.addEventListener('submit', async (e) => {
  e.preventDefault();
  clearError();

  const cf = input.value.trim().toUpperCase();

  if (!cf) {
    showError('Inserisci un codice fiscale.');
    input.focus();
    return;
  }

  setLoading(true);

  try {
    const resp = await fetch('api/valida', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ cf }),
    });

    if (!resp.ok) {
      const errData = await resp.json().catch(() => ({}));
      showError(errData.errore || 'Errore di comunicazione con il server.');
      return;
    }

    const data = await resp.json();

    if (!data.valido) {
      showError(data.errori.join(' '));
      resultsSection.hidden = true;
      return;
    }

    renderResults(data);
    resultsSection.hidden = false;

    // Smooth scroll to results on mobile
    if (window.innerWidth < 600) {
      resultsSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }

  } catch (err) {
    showError('Impossibile contattare il server. Riprova più tardi.');
    console.error(err);
  } finally {
    setLoading(false);
  }
});

/**
 * Render decoded results
 */
function renderResults(data) {
  const { dati, comune, comune_trovato } = data;

  // CF code display
  document.getElementById('result-cf').textContent = dati.codice_fiscale;

  // Validity badge
  const badge = document.getElementById('validity-badge');
  badge.textContent = 'Valido';
  badge.className = 'cf-card-badge valid';

  // Breakdown blocks
  const breakdown = document.getElementById('cf-breakdown');
  breakdown.innerHTML = '';
  const cf = dati.codice_fiscale;

  BLOCK_TYPES.forEach((block) => {
    const chars = cf.substring(block.start, block.end);
    const div = document.createElement('div');
    div.className = `cf-block cf-block-${block.key}`;

    const charsSpan = document.createElement('span');
    charsSpan.className = 'cf-block-chars';
    charsSpan.textContent = chars;

    const labelSpan = document.createElement('span');
    labelSpan.className = 'cf-block-label';
    labelSpan.textContent = block.label;

    div.appendChild(charsSpan);
    div.appendChild(labelSpan);
    breakdown.appendChild(div);
  });

  // Data grid
  const dataGrid = document.getElementById('data-grid');
  dataGrid.innerHTML = '';

  const items = [
    { label: 'Cognome (derivato)', value: dati.cognome_derivato, mono: true },
    { label: 'Nome (derivato)', value: dati.nome_derivato, mono: true },
    { label: 'Data di nascita', value: dati.data_nascita },
    { label: 'Anno', value: dati.anno },
    { label: 'Mese', value: dati.mese },
    { label: 'Giorno', value: dati.giorno },
    { label: 'Sesso', value: dati.sesso },
    { label: 'Codice catastale', value: dati.codice_catastale, mono: true },
    { label: 'Carattere di controllo', value: dati.carattere_controllo, mono: true },
  ];

  items.forEach((item) => {
    const div = document.createElement('div');
    div.className = 'data-item';

    const labelEl = document.createElement('div');
    labelEl.className = 'data-item-label';
    labelEl.textContent = item.label;

    const valueEl = document.createElement('div');
    valueEl.className = 'data-item-value';
    if (item.mono) valueEl.classList.add('mono');
    valueEl.textContent = item.value;

    div.appendChild(labelEl);
    div.appendChild(valueEl);
    dataGrid.appendChild(div);
  });

  // Comune card
  const comuneCard = document.getElementById('comune-card');
  if (comune_trovato) {
    comuneCard.innerHTML = `
      <div class="comune-card-icon" aria-hidden="true">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"/>
          <circle cx="12" cy="10" r="3"/>
        </svg>
      </div>
      <div class="comune-card-body">
        <div class="comune-card-label">Comune di nascita</div>
        <div class="comune-card-name">${escapeHtml(comune)}</div>
        <div class="comune-card-code">Codice catastale: ${dati.codice_catastale}</div>
      </div>
    `;
  } else {
    comuneCard.innerHTML = `
      <div class="comune-card-icon" aria-hidden="true">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/>
        </svg>
      </div>
      <div class="comune-card-body">
        <div class="comune-card-label">Comune di nascita</div>
        <div class="comune-card-notfound">
          Comune non trovato per il codice <strong>${dati.codice_catastale}</strong>.
          <br>Il database potrebbe non includere tutti i comuni italiani.
        </div>
      </div>
    `;
  }
}

/**
 * Escape HTML entities
 */
function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

/**
 * Allow Enter to submit
 */
input.addEventListener('keydown', (e) => {
  if (e.key === 'Enter') {
    e.preventDefault();
    form.dispatchEvent(new Event('submit', { cancelable: true }));
  }
});
