/* AI Calculator — vanilla client for the Flask JSON contract. */
(() => {
  const app = document.getElementById('app');
  const themeToggle = document.getElementById('theme-toggle');
  const aiStatus = document.getElementById('ai-status');
  const state = { aiAvailable: false, history: [], lastResult: null };
  const featureGroups = {
    core: {
      label: 'Core Calculation',
      tone: 'mint',
      icon: 'bi-calculator',
      intro: 'Reliable tools for the math that keeps your day moving.',
      features: [
        ['normal', 'Normal Calculator', 'Arithmetic with a readable result and optional note.', 'bi-calculator'],
        ['scientific', 'Scientific Calculator', 'Trigonometry, powers, roots, and logarithms.', 'bi-bezier2'],
        ['shape', 'Shape Calculator', 'Area, perimeter, surface area, and volume.', 'bi-bounding-box'],
        ['equation', 'Equation Calculator', 'Linear and quadratic equations with steps.', 'bi-signpost-split'],
        ['unit', 'Unit Converter', 'Convert common length, mass, time, and temperature units.', 'bi-arrow-left-right'],
        ['financial', 'Financial Calculator', 'Interest, discount, GST, profit/loss, and EMI.', 'bi-wallet2']
      ]
    },
    ai: {
      label: 'AI-Based Calculation',
      tone: 'blue',
      icon: 'bi-stars',
      intro: 'When the question needs interpretation, not just arithmetic.',
      features: [
        ['prompt', 'Prompt Calculator', 'Ask a plain-language question and keep the answer close.', 'bi-chat-square-text'],
        ['image', 'Image Math Solver', 'Upload a worksheet or handwritten problem.', 'bi-image'],
        ['voice', 'Voice Calculator', 'Speak a calculation when your hands are busy.', 'bi-mic'],
        ['solver', 'AI Math Solver', 'Choose answer-only, short, or detailed reasoning.', 'bi-lightbulb'],
        ['mistake', 'Mistake Detector', 'Compare your work with a careful explanation.', 'bi-search'],
        ['explain', 'Explain My Answer', 'Turn a result into a level-appropriate explanation.', 'bi-person-raised-hand']
      ]
    },
    advanced: {
      label: 'Advanced Features',
      tone: 'coral',
      icon: 'bi-grid-3x3-gap',
      intro: 'Explore patterns, compare assumptions, and see the bigger picture.',
      features: [
        ['graph', 'Graph Calculator', 'Plot an equation, then zoom into its behavior.', 'bi-graph-up'],
        ['whatif', 'What-If Comparison', 'Change assumptions side-by-side and see the delta.', 'bi-columns-gap'],
        ['quadratic', 'Multiple Solution Methods', 'Solve a quadratic three different ways.', 'bi-diagram-3'],
        ['tutor', 'AI Math Tutor', 'A patient, focused conversation starter for a problem.', 'bi-mortarboard'],
        ['advanced-financial', 'Advanced Financial Tools', 'Compare amortization and investment scenarios.', 'bi-bar-chart-line'],
        ['dashboard', 'Math Dashboard', 'See your practice rhythm and most-used tools.', 'bi-speedometer2']
      ]
    },
    history: {
      label: 'History',
      tone: 'lavender',
      icon: 'bi-clock-history',
      intro: 'Your solved work, organized for the next time you need it.',
      features: []
    }
  };

  const featureTitles = Object.fromEntries(Object.values(featureGroups).flatMap(group => group.features).map(([id, title]) => [id, title]));
  const featureDescriptions = Object.fromEntries(Object.values(featureGroups).flatMap(group => group.features).map(([id, title, description]) => [id, description]));
  const historyCategoryByTool = {
    'Normal Calculator': 'Basic',
    'Scientific Calculator': 'Scientific',
    'Shape Calculator': 'Shape',
    'Equation Calculator': 'Equation',
    'Unit Converter': 'Unit',
    'Financial Calculator': 'Financial',
    'Prompt Calculator': 'AI',
    'Image Math Solver': 'AI',
    'Voice Calculator': 'AI',
    'AI Math Solver': 'AI',
    'Mistake Detector': 'AI',
    'Explain My Answer': 'AI',
    'AI Math Tutor': 'AI',
    'Graph Calculator': 'Advanced',
    'What-If Comparison': 'Advanced',
    'Multiple Solution Methods': 'Advanced',
    'Advanced Financial Tools': 'Advanced'
  };

  function esc(value) {
    return String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[char]));
  }
  function formatDate(value) {
    if (!value) return 'just now';
    const date = new Date(value);
    if (Number.isNaN(date.getTime())) return value;
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', hour: 'numeric', minute: '2-digit' }).format(date);
  }
  function notify(message, tone = 'default') {
    const note = document.createElement('div');
    note.className = 'toast-note';
    note.style.borderLeft = `4px solid ${tone === 'error' ? 'var(--coral)' : 'var(--mint)'}`;
    note.textContent = message;
    document.getElementById('toast-area').appendChild(note);
    setTimeout(() => note.remove(), 3700);
  }
  function loading(message = 'Working through that…') {
    return `<div class="loading-state"><span class="spinner-border me-2" role="status" aria-hidden="true"></span>${esc(message)}</div>`;
  }
  function apiError(error) {
    const message = error?.message || 'The calculation could not be completed.';
    return `<div class="alert alert-warning border-0" role="alert"><i class="bi bi-info-circle me-2"></i>${esc(message)}</div>`;
  }
  async function api(path, options = {}) {
    const response = await fetch(path, { credentials: 'include', ...options });
    let body = {};
    try { body = await response.json(); } catch (_) { /* handled below */ }
    if (!response.ok) throw new Error(body.error || body.message || `Request failed (${response.status}).`);
    return body;
  }

  function renderShell(content, eyebrow = 'Math workspace', title = 'A little more clarity, one problem at a time.') {
    app.innerHTML = `<section class="view-shell">
      <a class="back-link" href="#home"><i class="bi bi-arrow-left"></i> Back to workspace</a>
      <div class="view-title"><div><span class="eyebrow">${esc(eyebrow)}</span><h1>${title}</h1></div></div>
      ${content}
    </section>`;
  }

  function renderHome() {
    const recent = state.history.slice(0, 3);
    app.innerHTML = `<section class="hero">
      <div>
        <span class="eyebrow">AI Calculator</span>
        <h1>Calculate. <em>Solve. Understand.</em></h1>
        <p class="hero-copy">A dependable space for routine calculations, guided math support, and solved work you can find again. Choose one of the four areas below to begin.</p>
      </div>
      <div class="hero-orbit" aria-label="An equation orbit illustration">
        <div class="orbit-equation">x² + y² = r²<small>make the unknown less unknown</small></div>
      </div>
    </section>
    <div class="section-heading"><div><span class="eyebrow">choose your way in</span><h2>Four places to begin</h2></div><p>Small tools, steady progress.</p></div>
    <section class="category-grid" aria-label="Primary navigation">
      ${Object.entries(featureGroups).map(([key, group]) => categoryCard(key, group)).join('')}
    </section>
    <section class="recent-strip">
      <div class="recent-strip-head"><h3><i class="bi bi-clock-history me-2"></i>Recent Calculations</h3><a href="#history" class="category-link">Open history <i class="bi bi-arrow-up-right"></i></a></div>
      ${recent.length ? `<div class="recent-list">${recent.map(recentItem).join('')}</div>` : `<div class="empty-state py-3"><i class="bi bi-journal-plus"></i><div>Your next solved problem will live here.</div></div>`}
    </section>`;
  }
  function categoryCard(key, group) {
    const href = key === 'history' ? '#history' : `#category/${key}`;
    const copy = key === 'history' ? 'Search, revisit, and keep your solved work in reach.' : group.intro;
    return `<a class="category-card" data-tone="${group.tone}" href="${href}">
      <span class="category-icon"><i class="bi ${group.icon}"></i></span>
      <h3>${esc(group.label)}</h3><p>${esc(copy)}</p>
      <span class="category-link">${key === 'history' ? 'Browse history' : `${group.features.length} tools`} <i class="bi bi-arrow-up-right"></i></span>
    </a>`;
  }
  function recentItem(item) {
    const result = cleanSchoolText(item.result || '');
    // Keep the home-page recent strip compact. Full saved work remains available in History.
    const preview = result.length > 220 ? `${result.slice(0, 220).trimEnd()}…` : result;
    return `<div class="recent-item"><div class="recent-expression"><strong>${esc(item.input_expression || 'Saved calculation')}</strong><small>${esc(item.calculator_type || item.category || 'Calculation')} · ${formatDate(item.created_at)}</small></div><span class="recent-result" title="${esc(result)}">${esc(preview)}</span></div>`;
  }

  function renderCategory(key) {
    const group = featureGroups[key] || featureGroups.core;
    if (key === 'history') return renderHistory();
    renderShell(`<section class="feature-grid">${group.features.map(([id, title, desc, icon]) => `<article class="feature-card">
      <span class="mini-icon"><i class="bi ${icon}"></i></span><h3>${esc(title)}</h3><p>${esc(desc)}</p>
      <button type="button" data-feature="${id}">Open tool <i class="bi bi-arrow-right ms-1"></i></button>
    </article>`).join('')}</section>`, group.label, `${esc(group.label)}<span class="serif">, your way.</span>`);
    app.querySelectorAll('[data-feature]').forEach(button => button.addEventListener('click', () => { location.hash = `#feature/${button.dataset.feature}`; }));
  }

  function formGroup(label, input, help = '') {
    return `<div class="mb-3"><label class="form-label">${esc(label)}</label>${input}${help ? `<div class="form-text">${esc(help)}</div>` : ''}</div>`;
  }
  function textInput(name, placeholder = '', value = '', type = 'text') {
    return `<input class="form-control" name="${esc(name)}" type="${type}" value="${esc(value)}" placeholder="${esc(placeholder)}">`;
  }
  function selectInput(name, options, selected = '') {
    return `<select class="form-select" name="${esc(name)}">${options.map(([value, label]) => `<option value="${esc(value)}" ${value === selected ? 'selected' : ''}>${esc(label)}</option>`).join('')}</select>`;
  }
  function workspaceForm(id, title, content, category, submitLabel = 'Calculate') {
    return `<div class="workspace"><div class="panel"><h2>${esc(title)}</h2><form id="tool-form" data-tool="${id}" data-category="${category}">${content}<div class="d-flex gap-2 flex-wrap"><button class="btn btn-primary px-4" type="submit"><i class="bi bi-play-fill me-1"></i>${esc(submitLabel)}</button><button class="btn btn-soft" type="reset">Reset</button></div></form></div><div id="result-column"><div class="panel result-panel"><h3>Result</h3><div id="result-content"><div class="empty-state py-2"><i class="bi bi-arrow-return-left"></i><div>Your result will appear here.</div></div></div></div></div></div>`;
  }
  // Apply the same clean Class 8-12 notebook formatting everywhere in the UI,
  // not only inside History. This is a frontend safety net for older saved answers
  // or any Gemini response that still contains raw Markdown/LaTeX.
  function cleanSchoolText(value) {
    if (value == null) return '';
    let text = String(value).replace(/\r\n/g, '\n').replace(/\r/g, '\n').replace(/\\n/g, '\n');
    text = text.replace(/```(?:text|latex|markdown)?/gi, '').replace(/```/g, '').replace(/\*\*/g, '');
    text = text.replace(/\\\[|\\\]|\\\(|\\\)|\$\$/g, '').replace(/\$/g, '');
    for (let i = 0; i < 4; i++) {
      text = text.replace(/\\frac\{([^{}]+)\}\{([^{}]+)\}/g, '($1)/($2)');
    }
    text = text.replace(/\\sqrt\{([^{}]+)\}/g, '√($1)');
    text = text.replace(/\\text\{([^{}]*)\}/g, '$1');
    text = text.replace(/\\mathrm\{([^{}]*)\}/g, '$1');
    text = text.replace(/\\left|\\right/g, '');
    text = text.replace(/\\(?:cdot|times)/g, '×');
    text = text.replace(/\\div/g, '÷');
    text = text.replace(/\\pm/g, '±').replace(/\\leq/g, '≤').replace(/\\geq/g, '≥').replace(/\\neq/g, '≠');
    text = text.replace(/\\infty/g, '∞').replace(/\\alpha/g, 'α').replace(/\\beta/g, 'β').replace(/\\theta/g, 'θ').replace(/\\pi/g, 'π');
    text = text.replace(/\^\{2\}/g, '²').replace(/\^2/g, '²').replace(/\^\{3\}/g, '³').replace(/\^3/g, '³');
    text = text.replace(/\\([A-Za-z]+)/g, '$1');
    text = text.replace(/\u2212/g, '-').replace(/[ \t]+/g, ' ');
    text = text.split('\n').map(line => line.trim()).join('\n');
    text = text.replace(/\n{3,}/g, '\n\n');
    return text.trim();
  }
  function richMath(value) {
    // Deliberately render school math as plain readable text rather than raw
    // MathJax/LaTeX. This keeps every result screen consistent and understandable.
    return esc(cleanSchoolText(value)).replace(/\n/g, '<br>');
  }
  function typesetMath(target) {
    // Kept as a no-op for compatibility with existing callers.
  }
  function resultHTML(result) {
    const steps = Array.isArray(result.steps) && result.steps.length ? `<div class="mt-3"><strong class="small">Working</strong><ol class="steps">${result.steps.map(step => `<li>${richMath(step)}</li>`).join('')}</ol></div>` : '';
    return `<div class="result-value math-output">${richMath(result.result ?? result.answer ?? 'No result')}</div>${result.formula ? `<div class="formula math-output">${richMath(result.formula)}</div>` : ''}${steps}<div class="mt-4"><label class="form-label">Purpose / note <span class="text-lowercase fw-normal">(optional)</span></label><input class="form-control" id="save-purpose" placeholder="e.g. revision for Thursday"></div><button class="btn btn-soft btn-sm mt-3" id="save-result"><i class="bi bi-bookmark-plus me-1"></i>Save to history</button>`;
  }
  function showResult(result, inputExpression, category, calculatorType) {
    state.lastResult = { result, inputExpression, category: historyCategoryByTool[calculatorType] || category, calculatorType };
    const target = document.getElementById('result-content');
    if (target) { target.innerHTML = resultHTML(result); typesetMath(target); }
    const save = document.getElementById('save-result');
    if (save) save.addEventListener('click', () => saveCurrentResult());
  }
  async function saveCurrentResult() {
    if (!state.lastResult) return;
    const purpose = document.getElementById('save-purpose')?.value || '';
    try {
      await api('/calc-api/history', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({
        input_expression: state.lastResult.inputExpression,
        result: state.lastResult.result.result ?? state.lastResult.result.answer ?? '',
        category: state.lastResult.category,
        calculator_type: state.lastResult.calculatorType,
        purpose
      }) });
      notify('Saved to history.');
      await loadRecent();
    } catch (error) { notify(error.message, 'error'); }
  }

  const coreForms = {
    normal: {
      title: 'Normal Calculator', category: 'Core Calculation',
      content: `${formGroup('Expression', textInput('expression', 'e.g. (18.5 × 4) − 7', '', 'text'), 'Use +, −, ×, ÷, parentheses, and percentages.')}`
    },
    scientific: {
      title: 'Scientific Calculator', category: 'Core Calculation',
      content: `<div class="row g-3">${formGroup('Expression', textInput('expression', 'e.g. sin(45) + √(16)', ''), 'Try sin, cos, tan, log, ln, sqrt, ^, and π.')}${formGroup('Angle mode', selectInput('angle_mode', [['degrees', 'Degrees'], ['radians', 'Radians']], 'degrees'))}</div>`
    },
    shape: {
      title: 'Shape Calculator', category: 'Core Calculation',
      content: `${formGroup('Shape', selectInput('shape', [['circle', 'Circle'], ['square', 'Square'], ['rectangle', 'Rectangle'], ['triangle', 'Triangle'], ['sphere', 'Sphere'], ['cylinder', 'Cylinder']]))}<div id="shape-fields">${shapeFields('circle')}</div>`
    },
    equation: {
      title: 'Equation Calculator', category: 'Core Calculation',
      content: `${formGroup('Equation type', selectInput('equation_type', [['linear', 'Linear equation'], ['quadratic', 'Quadratic equation'], ['simultaneous', 'Simultaneous x + y equations']]))}<div id="equation-fields">${formGroup('Equation', textInput('equation', 'e.g. 2x + 5 = 15', '2x + 5 = 15'), 'For simultaneous equations choose the third option and enter both equations.')}</div>`
    },
    unit: {
      title: 'Unit Converter', category: 'Core Calculation',
      content: `${formGroup('Category', selectInput('unit_category', [['length', 'Length'], ['weight', 'Weight'], ['temperature', 'Temperature'], ['area', 'Area'], ['volume', 'Volume'], ['speed', 'Speed']], 'length'))}<div class="row g-3"><div class="col-md-4">${formGroup('Value', textInput('value', '100', '', 'number'))}</div><div id="unit-fields" class="col-md-8">${unitFields('length')}</div></div>`
    },
    financial: {
      title: 'Financial Calculator', category: 'Core Calculation',
      content: `${formGroup('Calculation', selectInput('financial_type', [['percentage', 'Percentage of a number'], ['profit_loss', 'Profit or loss'], ['discount', 'Discounted price'], ['gst', 'GST / tax inclusive price'], ['simple_interest', 'Simple interest'], ['compound_interest', 'Compound interest'], ['emi', 'Monthly EMI']]))}<div id="financial-fields">${financialFields('percentage')}</div>`
    }
  };

  function shapeFields(shape) {
    const fields = {
      circle: [['radius', 'Radius', '4']], square: [['side', 'Side', '4']], rectangle: [['length', 'Length', '5'], ['width', 'Width', '3']],
      triangle: [['base', 'Base', '6'], ['height', 'Height', '4'], ['side_a', 'Side a', '5'], ['side_b', 'Side b', '5'], ['side_c', 'Side c', '6']],
      sphere: [['radius', 'Radius', '4']], cylinder: [['radius', 'Radius', '3'], ['height', 'Height', '8']]
    }[shape] || [];
    return `<div class="row g-3">${fields.map(([name, label, value]) => `<div class="col-md-6">${formGroup(label, textInput(name, value, value, 'number'))}</div>`).join('')}</div>`;
  }
  function unitFields(category) {
    const choices = {
      length: [['meters', 'Meters'], ['kilometers', 'Kilometers'], ['centimeters', 'Centimeters'], ['miles', 'Miles'], ['feet', 'Feet'], ['inches', 'Inches']],
      weight: [['grams', 'Grams'], ['kilograms', 'Kilograms'], ['pounds', 'Pounds']],
      temperature: [['celsius', 'Celsius'], ['fahrenheit', 'Fahrenheit'], ['kelvin', 'Kelvin']],
      area: [['square_meters', 'Square meters'], ['square_kilometers', 'Square kilometers'], ['square_feet', 'Square feet']],
      volume: [['liters', 'Liters'], ['milliliters', 'Milliliters'], ['cubic_meters', 'Cubic meters']],
      speed: [['kilometers_per_hour', 'Kilometers per hour'], ['meters_per_second', 'Meters per second'], ['miles_per_hour', 'Miles per hour']]
    }[category] || [];
    return `<div class="row g-3">${formGroup('From', selectInput('from_unit', choices))}${formGroup('To', selectInput('to_unit', choices, choices[1]?.[0] || choices[0]?.[0] || ''))}</div>`;
  }
  function financialFields(type) {
    const sets = {
      percentage: [['value', 'Base amount', '240'], ['rate', 'Percentage', '15']],
      profit_loss: [['cost_price', 'Cost price', '80'], ['selling_price', 'Selling price', '104']],
      discount: [['price', 'Original price', '120'], ['rate', 'Discount', '20']],
      gst: [['price', 'Price before GST', '850'], ['rate', 'GST rate', '18']],
      simple_interest: [['principal', 'Principal', '10000'], ['rate', 'Annual rate (%)', '7'], ['time', 'Time (years)', '2']],
      compound_interest: [['principal', 'Principal', '10000'], ['rate', 'Annual rate (%)', '7'], ['time', 'Time (years)', '2'], ['frequency', 'Compounds / year', '4']],
      emi: [['principal', 'Loan amount', '250000'], ['rate', 'Annual rate (%)', '8.5'], ['time', 'Tenure (years)', '5']]
    };
    return `<div class="row g-3">${(sets[type] || sets.percentage).map(([name, label, value]) => `<div class="col-md-6">${formGroup(label, textInput(name, value, value, 'number'))}</div>`).join('')}</div>`;
  }

  function renderCoreFeature(id) {
    const config = coreForms[id];
    renderShell(workspaceForm(id, config.title, config.content, config.category), config.category, `${esc(config.title)}<span class="serif">, with context.</span>`);
    bindCoreForm(id);
  }
  function bindCoreForm(id) {
    const form = document.getElementById('tool-form');
    if (!form) return;
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const submit = form.querySelector('[type=submit]');
      submit.disabled = true;
      document.getElementById('result-content').innerHTML = loading('Calculating with care…');
      const data = Object.fromEntries(new FormData(form).entries());
      const inputExpression = data.expression || (
        id === 'shape' ? `${data.shape}: ${JSON.stringify(data)}` :
        id === 'equation' ? (data.equation_type === 'simultaneous' ? `${data.equation1} ; ${data.equation2}` : data.equation) :
        id === 'unit' ? `${data.value} ${data.from_unit} → ${data.to_unit}` :
        id === 'financial' ? `${data.financial_type}: ${JSON.stringify(data)}` :
        `${data.value || id}`
      );
      try {
        const result = await api('/calc-api/calculate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ calculator_type: id, category: 'Core Calculation', expression: data.expression, inputs: data, angle_mode: data.angle_mode }) });
        showResult(result, inputExpression, 'Core Calculation', featureTitles[id]);
      } catch (error) { document.getElementById('result-content').innerHTML = apiError(error); }
      submit.disabled = false;
    });
    form.addEventListener('reset', () => setTimeout(() => {
      if (id === 'shape') document.getElementById('shape-fields').innerHTML = shapeFields(form.shape.value);
      if (id === 'financial') document.getElementById('financial-fields').innerHTML = financialFields(form.financial_type.value);
    }, 0));
    if (id === 'shape') form.shape.addEventListener('change', () => { document.getElementById('shape-fields').innerHTML = shapeFields(form.shape.value); });
    if (id === 'financial') form.financial_type.addEventListener('change', () => { document.getElementById('financial-fields').innerHTML = financialFields(form.financial_type.value); });
    if (id === 'equation') {
      const updateEquationFields = () => {
        const target = document.getElementById('equation-fields');
        if (form.equation_type.value === 'simultaneous') {
          target.innerHTML = `<div class="row g-3"><div class="col-md-6">${formGroup('Equation 1', textInput('equation1', '2x + 3y = 12', '2x + 3y = 12'))}</div><div class="col-md-6">${formGroup('Equation 2', textInput('equation2', 'x − y = 1', 'x - y = 1'))}</div></div>`;
        } else {
          const example = form.equation_type.value === 'quadratic' ? 'x^2 + 5x + 6 = 0' : '2x + 5 = 15';
          target.innerHTML = formGroup('Equation', textInput('equation', example, example), 'Enter the equation directly. The calculator returns the solution and steps.');
        }
      };
      form.equation_type.addEventListener('change', updateEquationFields);
    }
    if (id === 'unit') {
      const updateUnitFields = () => { document.getElementById('unit-fields').innerHTML = unitFields(form.unit_category.value); };
      form.unit_category.addEventListener('change', updateUnitFields);
      form.addEventListener('reset', () => setTimeout(updateUnitFields, 0));
    }
  }

  function renderNormalWithKeypad() {
    renderCoreFeature('normal');
    const expression = document.querySelector('[name=expression]');
    expression.insertAdjacentHTML('afterend', `<div class="calculator-keypad">${['7','8','9','÷','4','5','6','×','1','2','3','−','0','.','(',')','%','+','⌫','AC','='].map(key => `<button class="key ${['÷','×','−','+','%','⌫','AC'].includes(key) ? 'action' : ''} ${key === '=' ? 'equals' : ''}" type="button" data-key="${key}">${key}</button>`).join('')}</div>`);
    document.querySelectorAll('[data-key]').forEach(key => key.addEventListener('click', () => {
      const value = key.dataset.key;
      if (value === 'AC') expression.value = '';
      else if (value === '⌫') expression.value = expression.value.slice(0, -1);
      else if (value === '=') document.getElementById('tool-form').requestSubmit();
      else expression.value += value.replace('×', '*').replace('÷', '/').replace('−', '-');
      expression.focus();
    }));
  }

  function aiNotice() {
    return state.aiAvailable ? '' : `<div class="alert alert-warning border-0 mb-3"><i class="bi bi-cloud-slash me-2"></i><strong>AI is unavailable right now.</strong> Add GEMINI_API_KEY in the server environment. Core calculations and history still work.</div>`;
  }
  function aiForm(id, title, category, promptLabel, placeholder, detail = true, submitLabel = 'Ask AI') {
    const fields = `${formGroup(promptLabel, `<textarea class="form-control" name="prompt" rows="7" placeholder="${esc(placeholder)}"></textarea>`)}`;
    const selectors = detail ? `<div class="row g-3"><div class="col-sm-6">${formGroup('Answer style', selectInput('mode', [['answer-only', 'Answer only'], ['short', 'Short explanation'], ['detailed', 'Detailed reasoning']], 'short'))}</div><div class="col-sm-6">${formGroup('Level', selectInput('detail_level', [['beginner', 'Beginner'], ['student', 'Student'], ['detailed', 'Detailed']], 'student'))}</div></div>` : '';
    return workspaceForm(id, title, `${aiNotice()}${selectors}${fields}`, category, submitLabel);
  }
  function renderAiFeature(id) {
    const config = {
      prompt: ['Prompt Calculator', 'Ask a question in the words you would use with a helpful classmate.', 'What is 18% of 245, and how can I check it?', 'Prompt Calculator'],
      solver: ['AI Math Solver', 'Give a problem, then choose how much reasoning you want to see.', 'Solve 3x² − 5x − 2 = 0', 'AI Math Solver'],
      mistake: ['Mistake Detector', 'Paste the problem and your working. The useful part is the comparison.', 'Problem: 2x + 4 = 12\\nMy work: 2x = 12 + 4, so x = 8', 'Mistake Detector'],
      explain: ['Explain My Answer', 'Bring your answer; leave with an explanation that fits your level.', 'Why is the derivative of x² equal to 2x?', 'Explain My Answer'],
      tutor: ['AI Math Tutor', 'A patient starting point for a focused study session.', 'I understand the first step of factoring, but not what comes next.', 'AI Math Tutor']
    }[id];
    renderShell(aiForm(id, config[0], id === 'tutor' ? 'Advanced Features' : 'AI-Based Calculation', 'Your problem or question', config[2], true, id === 'tutor' ? 'Start tutoring' : 'Ask AI'), id === 'tutor' ? 'Advanced Features' : 'AI-Based Calculation', `${esc(config[0])}<span class="serif">, at your pace.</span>`);
    const form = document.getElementById('tool-form');
    form.addEventListener('submit', async event => {
      event.preventDefault();
      const button = form.querySelector('[type=submit]');
      button.disabled = true;
      document.getElementById('result-content').innerHTML = loading('Thinking through the wording…');
      const data = Object.fromEntries(new FormData(form).entries());
      try {
        const result = await api('/calc-api/ai/solve', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ feature: id, mode: data.mode || 'short', prompt: data.prompt, detail_level: data.detail_level || 'student', my_answer: id === 'mistake' ? data.prompt : undefined }) });
        const aiResult = { result: result.answer, formula: result.interpreted_problem, steps: [result.calculation, result.explanation].filter(Boolean) };
        showResult(aiResult, data.prompt, 'AI-Based Calculation', config[0]);
      } catch (error) { document.getElementById('result-content').innerHTML = apiError(error); }
      button.disabled = false;
    });
  }

  function renderImageFeature() {
    renderShell(`${aiNotice()}<div class="workspace"><div class="panel"><h2>Image Math Solver</h2><form id="image-form">${formGroup('Problem image', `<input class="form-control" name="image" type="file" accept=".jpg,.jpeg,.png,.webp,image/jpeg,image/png,image/webp" required>`, 'Upload a JPEG, PNG, or WebP image under 8 MB.') }<div class="row g-3">${formGroup('Answer style', selectInput('mode', [['answer-only', 'Answer only'], ['short', 'Short explanation'], ['detailed', 'Detailed reasoning']], 'detailed'))}${formGroup('Level', selectInput('detail_level', [['beginner', 'Beginner'], ['student', 'Student'], ['detailed', 'Detailed']], 'student'))}</div><button class="btn btn-primary" type="submit"><i class="bi bi-scan me-2"></i>Read and solve</button></form></div><div class="panel result-panel"><h3>Result</h3><div id="result-content"><div class="empty-state py-2"><i class="bi bi-image"></i><div>Upload a problem to begin.</div></div></div></div></div>`, 'AI-Based Calculation', 'Image Math Solver<span class="serif">, made legible.</span>');
    document.getElementById('image-form').addEventListener('submit', async event => {
      event.preventDefault();
      const form = event.currentTarget; const body = new FormData(form);
      document.getElementById('result-content').innerHTML = loading('Reading the problem…');
      try {
        const result = await api('/calc-api/ai/image', { method: 'POST', body });
        showResult({ result: result.answer, formula: result.interpreted_problem, steps: [result.calculation, result.explanation].filter(Boolean) }, form.image.files[0]?.name || 'Uploaded math image', 'AI-Based Calculation', 'Image Math Solver');
      } catch (error) { document.getElementById('result-content').innerHTML = apiError(error); }
    });
  }
  function renderVoiceFeature() {
    renderShell(`${aiNotice()}<div class="workspace"><div class="panel"><h2>Voice Calculator</h2><p class="text-secondary small">Speak a calculation, then edit the transcript before sending it.</p><form id="voice-form">${formGroup('Transcript', `<textarea class="form-control" name="prompt" rows="5" placeholder="e.g. what is 14 percent of 280"></textarea>`)}<div class="d-flex gap-2 flex-wrap"><button type="button" class="btn btn-soft" id="voice-listen"><i class="bi bi-mic me-2"></i>Start listening</button><button class="btn btn-primary" type="submit">Calculate</button></div><div id="voice-support" class="form-text mt-3"></div></form></div><div class="panel result-panel"><h3>Result</h3><div id="result-content"><div class="empty-state py-2"><i class="bi bi-mic"></i><div>Your spoken calculation will land here.</div></div></div></div></div>`, 'AI-Based Calculation', 'Voice Calculator<span class="serif">, hands free.</span>');
    const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition;
    const support = document.getElementById('voice-support');
    const listen = document.getElementById('voice-listen');
    const prompt = document.querySelector('[name=prompt]');
    if (!SpeechRecognition) { listen.disabled = true; support.textContent = 'Speech recognition is not available in this browser. Type your calculation instead.'; }
    else {
      support.textContent = 'Speech recognition is available. Your browser will ask for microphone access.';
      listen.addEventListener('click', () => {
        const recognition = new SpeechRecognition(); recognition.lang = 'en-US'; recognition.interimResults = false;
        listen.innerHTML = '<i class="bi bi-record-circle me-2"></i>Listening…'; listen.disabled = true;
        recognition.onresult = event => { prompt.value = event.results[0][0].transcript; };
        recognition.onerror = () => notify('I could not hear that. You can type it instead.', 'error');
        recognition.onend = () => { listen.innerHTML = '<i class="bi bi-mic me-2"></i>Start listening'; listen.disabled = false; };
        recognition.start();
      });
    }
    document.getElementById('voice-form').addEventListener('submit', async event => {
      event.preventDefault(); document.getElementById('result-content').innerHTML = loading('Translating that into a calculation…');
      try { const result = await api('/calc-api/ai/solve', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ feature: 'voice', mode: 'short', prompt: prompt.value, detail_level: 'student' }) }); showResult({ result: result.answer, formula: result.interpreted_problem, steps: [result.calculation, result.explanation].filter(Boolean) }, prompt.value, 'AI-Based Calculation', 'Voice Calculator'); }
      catch (error) { document.getElementById('result-content').innerHTML = apiError(error); }
    });
  }

  function renderGraph() {
    renderShell(`<div class="workspace"><div class="panel"><h2>Graph Calculator</h2><form id="graph-form">${formGroup('Function / equation', textInput('expression', 'e.g. y = 5*x - 8 or x^2 - 4*x + 3', 'x^2 - 4*x + 3'), 'Supports y = f(x), such as y = x^2 - 4*x + 3, and linear equations such as 5*x - 8*y + 1 = 0.') }<div class="row g-3">${formGroup('x minimum', textInput('xmin', '-10', '-10', 'number'))}${formGroup('x maximum', textInput('xmax', '10', '10', 'number'))}</div><div class="d-flex gap-2 flex-wrap"><button class="btn btn-primary" type="submit"><i class="bi bi-graph-up me-2"></i>Plot function</button><button class="btn btn-soft" id="reset-graph" type="button">Reset view</button></div></form></div><div class="panel chart-shell"><div id="plot" style="width:100%;height:340px;"></div></div><div class="panel"><h3>X / Y values</h3><div id="xy-table" class="table-responsive"><div class="empty-state py-2">Plot a function to see calculated X and Y values.</div></div></div></div>`, 'Advanced Features', 'Graph Calculator<span class="serif">, see the shape.</span>');
    const draw = async (expr, min, max) => {
      const response = await api('/calc-api/graph', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ expression: expr, xmin: min, xmax: max }) });
      const points = response.points || [];
      const valid = points.filter(point => point.y !== null && Number.isFinite(point.y));
      Plotly.newPlot('plot', [{ x: valid.map(point => point.x), y: valid.map(point => point.y), mode: 'lines', name: response.expression, line: { width: 3 }, hovertemplate: 'x=%{x:.2f}<br>y=%{y:.2f}<extra></extra>' }], { margin: { t: 12, r: 12, b: 45, l: 48 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { family: 'Manrope', color: getComputedStyle(document.body).color }, xaxis: { title: 'x', showgrid: true, zeroline: true }, yaxis: { title: 'y', showgrid: true, zeroline: true } }, { responsive: true, displaylogo: false, modeBarButtonsToRemove: ['select2d', 'lasso2d'] });
      const table = response.table || valid.slice(0, 12);
      document.getElementById('xy-table').innerHTML = table.length ? `<table class="table align-middle mb-0"><thead><tr><th>#</th><th>X</th><th>Y</th></tr></thead><tbody>${table.map((point, index) => `<tr><td>${index + 1}</td><td>${Number(point.x).toFixed(4)}</td><td>${Number(point.y).toFixed(4)}</td></tr>`).join('')}</tbody></table>` : '<div class="alert alert-warning border-0 mb-0">No finite X/Y values were found in this range.</div>';
    };
    draw('x^2 - 4*x + 3', -10, 10).catch(error => notify(error.message, 'error'));
    document.getElementById('graph-form').addEventListener('submit', event => { event.preventDefault(); const data = Object.fromEntries(new FormData(event.currentTarget)); draw(data.expression, Number(data.xmin), Number(data.xmax)).catch(error => notify(error.message, 'error')); });
    document.getElementById('reset-graph').addEventListener('click', () => draw('x^2 - 4*x + 3', -10, 10).catch(error => notify(error.message, 'error')));
  }

  function renderWhatIf() {
    renderShell(`<div class="panel"><h2>What-If Comparison</h2><p class="text-secondary">Change a value across three scenarios. Useful for budgets, grades, rates, and plans.</p><form id="whatif-form"><div class="row g-3">${formGroup('Label', textInput('label', 'Monthly savings', 'Monthly savings'))}${formGroup('Formula', selectInput('formula', [['multiply', 'Value × rate'], ['add', 'Value + adjustment'], ['percentage', 'Value × (1 + rate)']], 'multiply'))}</div><div class="row g-3"><div class="col-md-4">${formGroup('Base value', textInput('base', '1000', '1000', 'number'))}</div><div class="col-md-4">${formGroup('Rate / adjustment', textInput('rate', '5', '5', 'number'))}</div><div class="col-md-4">${formGroup('Scenario spread', textInput('spread', '10', '10', 'number'))}</div></div><button class="btn btn-primary" type="submit">Compare scenarios</button></form><div id="comparison" class="mt-4"></div></div>`, 'Advanced Features', 'What-If <span class="serif">Comparison.</span>');
    document.getElementById('whatif-form').addEventListener('submit', event => {
      event.preventDefault(); const d = Object.fromEntries(new FormData(event.currentTarget)); const base = Number(d.base); const rate = Number(d.rate); const spread = Number(d.spread);
      const calc = scenario => d.formula === 'multiply' ? base * ((rate + scenario) / 100) : d.formula === 'add' ? base + rate + scenario : base * (1 + ((rate + scenario) / 100));
      document.getElementById('comparison').innerHTML = `<div class="what-if-table"><div class="comparison-row"><strong>${esc(d.label)}</strong><strong>Conservative</strong><strong>Base plan</strong><strong>Stretch</strong></div><div class="comparison-row"><span>Outcome</span><span>${calc(-spread).toFixed(2)}</span><span>${calc(0).toFixed(2)}</span><span>${calc(spread).toFixed(2)}</span></div><div class="comparison-row"><span>Difference from base</span><span>${(calc(-spread) - calc(0)).toFixed(2)}</span><span>—</span><span>+${(calc(spread) - calc(0)).toFixed(2)}</span></div></div>`;
    });
  }

  function renderQuadratic() {
    renderShell(`<div class="workspace"><div class="panel"><h2>Multiple Solution Methods</h2><p class="text-secondary small">For ax² + bx + c = 0. Compare the quadratic formula, factoring, and completing the square.</p><form id="quadratic-form"><div class="row g-3"><div class="col-md-4">${formGroup('a', textInput('a', '1', '1', 'number'))}</div><div class="col-md-4">${formGroup('b', textInput('b', '-5', '-5', 'number'))}</div><div class="col-md-4">${formGroup('c', textInput('c', '6', '6', 'number'))}</div></div><button class="btn btn-primary" type="submit">Show methods</button></form></div><div class="panel result-panel"><h3>Methods</h3><div id="method-results"><div class="empty-state py-2"><i class="bi bi-diagram-3"></i><div>Enter coefficients to compare.</div></div></div></div></div>`, 'Advanced Features', 'Solve it three ways<span class="serif">.</span>');
    document.getElementById('quadratic-form').addEventListener('submit', event => {
      event.preventDefault(); const d = Object.fromEntries(new FormData(event.currentTarget)); const a = Number(d.a), b = Number(d.b), c = Number(d.c), disc = b * b - 4 * a * c;
      const roots = disc < 0 ? 'No real roots' : `${((-b + Math.sqrt(disc)) / (2 * a)).toFixed(4)}, ${((-b - Math.sqrt(disc)) / (2 * a)).toFixed(4)}`;
      const factoring = (disc >= 0 && Number.isInteger(Math.sqrt(disc))) ? 'Look for factors of c that sum to b.' : 'This one does not factor neatly over the integers.';
      document.getElementById('method-results').innerHTML = `<div class="formula">Discriminant = ${disc}</div><div class="mb-3"><strong>Quadratic formula</strong><p class="small text-secondary mb-1">x = (−b ± √(b² − 4ac)) / 2a</p><div class="result-value fs-4">${roots}</div></div><div class="mb-3"><strong>Factoring</strong><p class="small text-secondary mb-1">${factoring}</p></div><div><strong>Complete the square</strong><p class="small text-secondary mb-0">Divide by ${a}, move the constant, then add (b / 2a)² to both sides. The same roots are ${roots}.</p></div>`;
    });
  }

  function renderAdvancedFinancial() {
    renderShell(`<div class="workspace"><div class="panel"><h2>Advanced Financial Tools</h2><p class="text-secondary small">Compare two investment scenarios with monthly compounding.</p><form id="invest-form">${formGroup('Starting principal', textInput('principal', '10000', '10000', 'number'))}<div class="row g-3">${formGroup('Monthly contribution', textInput('contribution', '400', '400', 'number'))}${formGroup('Years', textInput('years', '10', '10', 'number'))}</div><div class="row g-3">${formGroup('Plan A annual return (%)', textInput('rate_a', '5', '5', 'number'))}${formGroup('Plan B annual return (%)', textInput('rate_b', '7', '7', 'number'))}</div><button class="btn btn-primary" type="submit">Compare growth</button></form></div><div class="panel result-panel"><h3>Projection</h3><div id="investment-results"><div class="empty-state py-2"><i class="bi bi-bar-chart-line"></i><div>Your comparison will appear here.</div></div></div></div></div>`, 'Advanced Features', 'Advanced Financial Tools<span class="serif">, with a longer view.</span>');
    document.getElementById('invest-form').addEventListener('submit', event => {
      event.preventDefault(); const d = Object.fromEntries(new FormData(event.currentTarget)); const principal = Number(d.principal), contribution = Number(d.contribution), years = Number(d.years);
      const future = rate => { let total = principal; for (let month = 0; month < years * 12; month++) total = total * (1 + Number(rate) / 1200) + contribution; return total; };
      const a = future(d.rate_a), b = future(d.rate_b);
      document.getElementById('investment-results').innerHTML = `<div class="result-value">${b.toLocaleString(undefined, { style: 'currency', currency: 'INR' })}</div><p class="result-muted">Plan B projected value after ${years} years.</p><div class="formula">Plan A: ${a.toLocaleString(undefined, { style: 'currency', currency: 'INR' })}<br>Plan B: ${b.toLocaleString(undefined, { style: 'currency', currency: 'INR' })}<br>Difference: ${(b - a).toLocaleString(undefined, { style: 'currency', currency: 'INR' })}</div>`;
    });
  }

  function renderDashboard() {
    renderShell(`<div id="dashboard-content">${loading('Gathering your math rhythm…')}</div>`, 'Advanced Features', 'Math Dashboard<span class="serif">, a useful little mirror.</span>');
    api('/calc-api/dashboard').then(data => {
      document.getElementById('dashboard-content').innerHTML = `<div class="dashboard-grid">${[['Total calculations', data.total_calculations, 'bi-calculator'], ['Today', data.today_calculations, 'bi-sun'], ['This week', data.week_calculations, 'bi-calendar3'], ['Most used', data.most_used_calculator || '—', 'bi-bookmark-star']].map(([label, value, icon]) => `<div class="stat-card"><i class="bi ${icon} text-success"></i><div class="stat-value">${esc(value)}</div><small>${esc(label)}</small></div>`).join('')}</div><div class="workspace"><div class="panel chart-shell"><h3>Monthly activity</h3><div id="activity-chart" style="width:100%;height:275px;"></div></div><div class="panel"><h3>Your patterns</h3><p class="text-secondary small">Most common category</p><div class="result-value fs-3">${esc(data.most_common_category || 'No pattern yet')}</div><h3 class="mt-4">Recent activity</h3>${(data.recent_activity || []).slice(0, 4).map(recentItem).join('') || '<div class="empty-state py-2">No saved activity yet.</div>'}</div></div>`;
      const months = data.monthly_activity || []; Plotly.newPlot('activity-chart', [{ x: months.map(item => item.month), y: months.map(item => item.count), type: 'bar', marker: { color: '#b9e6d3' }, hovertemplate: '%{x}: %{y}<extra></extra>' }], { margin: { t: 8, r: 8, b: 35, l: 35 }, paper_bgcolor: 'transparent', plot_bgcolor: 'transparent', font: { family: 'Manrope', color: getComputedStyle(document.body).color }, xaxis: { showgrid: false }, yaxis: { showgrid: true, gridcolor: '#dfe5df' } }, { responsive: true, displaylogo: false, displayModeBar: false });
    }).catch(error => { document.getElementById('dashboard-content').innerHTML = apiError(error); });
  }

  async function loadRecent() {
    try { const data = await api('/calc-api/history?period=month'); state.history = data.items || []; if (location.hash === '#home') renderHome(); } catch (_) { /* home remains useful without history */ }
  }
  async function renderHistory() {
    renderShell(`<div id="history-page">${loading('Opening your solved work…')}</div>`, 'History', 'History<span class="serif">, without the hunting.</span>');
    const page = document.getElementById('history-page');
    page.innerHTML = historyToolbar() + '<div id="history-list"></div>';
    bindHistoryToolbar();
    await fetchHistory();
  }
  function historyToolbar() {
    return `<form class="history-toolbar" id="history-filters"><div class="search-field">${formGroup('Search', textInput('search', 'Search expressions or notes'))}</div>${formGroup('Category', selectInput('category', [['', 'All categories'], ['Basic', 'Basic'], ['Scientific', 'Scientific'], ['Shape', 'Shape'], ['Equation', 'Equation'], ['Unit', 'Unit'], ['Financial', 'Financial'], ['AI', 'AI'], ['Advanced', 'Advanced']]))}${formGroup('Tool', `<input class="form-control" name="calculator_type" placeholder="Any tool">`)}${formGroup('Period', selectInput('period', [['', 'Any time'], ['today', 'Today'], ['yesterday', 'Yesterday'], ['week', 'This week'], ['month', 'This month'], ['custom', 'Custom dates']]))}<button class="btn btn-primary" type="submit"><i class="bi bi-search me-1"></i>Filter</button><button class="btn btn-coral" id="clear-history" type="button"><i class="bi bi-trash3 me-1"></i>Clear all</button><div class="custom-dates d-none" style="grid-column:1/-1"><div class="row g-2"><div class="col-sm-6">${formGroup('Start date', textInput('start_date', '', '', 'date'))}</div><div class="col-sm-6">${formGroup('End date', textInput('end_date', '', '', 'date'))}</div></div></div></form>`;
  }
  function bindHistoryToolbar() {
    const filters = document.getElementById('history-filters');
    filters.addEventListener('submit', event => { event.preventDefault(); fetchHistory(); });
    filters.period.addEventListener('change', () => filters.querySelector('.custom-dates').classList.toggle('d-none', filters.period.value !== 'custom'));
    document.getElementById('clear-history').addEventListener('click', () => {
      const modal = new bootstrap.Modal(document.getElementById('confirm-modal')); document.getElementById('confirm-action').onclick = async () => { try { await api('/calc-api/history', { method: 'DELETE' }); modal.hide(); notify('History cleared.'); fetchHistory(); } catch (error) { notify(error.message, 'error'); } }; modal.show();
    });
  }
  async function fetchHistory() {
    const list = document.getElementById('history-list'); if (!list) return;
    list.innerHTML = loading('Finding saved work…');
    const data = Object.fromEntries(new FormData(document.getElementById('history-filters')).entries());
    const query = new URLSearchParams(Object.fromEntries(Object.entries(data).filter(([, value]) => value)));
    try {
      const response = await api(`/calc-api/history?${query}`); state.history = response.items || [];
      list.innerHTML = state.history.length ? `<div class="history-list">${state.history.map(historyRow).join('')}</div>` : `<div class="panel">${emptyState('No calculations match that filter.', 'bi-funnel')}</div>`;
      list.querySelectorAll('[data-delete-id]').forEach(button => button.addEventListener('click', async () => { if (!confirm('Delete this saved calculation?')) return; try { await api(`/calc-api/history/${button.dataset.deleteId}`, { method: 'DELETE' }); notify('Calculation removed.'); fetchHistory(); } catch (error) { notify(error.message, 'error'); } }));
    } catch (error) { list.innerHTML = apiError(error); }
  }
  function historyRow(item) {
    return `<article class="history-row"><div class="history-main"><strong>${esc(item.input_expression || 'Saved calculation')}</strong><small>${esc(item.calculator_type || 'Calculation')} · ${esc(item.category || '')} · ${formatDate(item.created_at)}</small>${item.purpose ? `<div class="history-meta mt-1"><i class="bi bi-sticky me-1"></i>${esc(item.purpose)}</div>` : ''}</div><div class="history-result math-output">${richMath(item.result || '')}</div><div class="history-actions"><button type="button" title="Delete calculation" data-delete-id="${esc(item.id)}"><i class="bi bi-trash3"></i></button></div></article>`;
  }
  function emptyState(text, icon = 'bi-inbox') { return `<div class="empty-state"><i class="bi ${icon}"></i><div>${esc(text)}</div></div>`; }

  function route() {
    const hash = location.hash.replace(/^#/, '') || 'home';
    if (hash === 'home') return renderHome();
    if (hash === 'history') return renderHistory();
    const [type, id] = hash.split('/');
    if (type === 'category') return renderCategory(id);
    if (type === 'feature') {
      if (coreForms[id]) return id === 'normal' ? renderNormalWithKeypad() : renderCoreFeature(id);
      if (id === 'image') return renderImageFeature();
      if (id === 'voice') return renderVoiceFeature();
      if (id === 'graph') return renderGraph();
      if (id === 'whatif') return renderWhatIf();
      if (id === 'quadratic') return renderQuadratic();
      if (id === 'advanced-financial') return renderAdvancedFinancial();
      if (id === 'dashboard') return renderDashboard();
      if (['prompt', 'solver', 'mistake', 'explain', 'tutor'].includes(id)) return renderAiFeature(id);
    }
    location.hash = '#home';
  }

  function setupTheme() {
    const saved = localStorage.getItem('ai-calculator-theme'); if (saved) document.documentElement.dataset.theme = saved;
    const update = () => { const dark = document.documentElement.dataset.theme === 'dark'; themeToggle.innerHTML = `<i class="bi bi-${dark ? 'sun' : 'moon-stars'}" aria-hidden="true"></i>`; themeToggle.setAttribute('aria-label', dark ? 'Switch to light mode' : 'Switch to dark mode'); };
    update(); themeToggle.addEventListener('click', () => { const next = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark'; document.documentElement.dataset.theme = next; localStorage.setItem('ai-calculator-theme', next); update(); });
  }
  async function init() {
    setupTheme();
    try { const status = await api('/calc-api/status'); state.aiAvailable = Boolean(status.ai_available); aiStatus.innerHTML = state.aiAvailable ? '<i class="bi bi-stars me-1"></i>AI ready' : '<i class="bi bi-cloud-slash me-1"></i>AI unavailable'; } catch (_) { aiStatus.textContent = 'Offline mode'; }
    route(); window.addEventListener('hashchange', route); loadRecent();
  }
  init();
})();