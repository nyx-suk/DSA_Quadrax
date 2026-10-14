/**
 * Exam Timetable Visualizer - Frontend Controller
 * Handles UI interactions, Vis.js graph rendering, color-coordinated timetable grid,
 * step-by-step assignment animation, and Chart.js benchmarks.
 */

// Distinct qualitative color palette for slots
const SLOT_PALETTE = [
  '#38bdf8', // Sky 400
  '#f43f5e', // Rose 500
  '#10b981', // Emerald 500
  '#a855f7', // Purple 500
  '#f59e0b', // Amber 500
  '#06b6d4', // Cyan 500
  '#ec4899', // Pink 500
  '#84cc16', // Lime 500
  '#6366f1', // Indigo 500
  '#14b8a6', // Teal 500
  '#f97316', // Orange 500
  '#8b5cf6', // Violet 500
  '#22c55e', // Green 500
  '#eab308', // Yellow 500
  '#3b82f6', // Blue 500
  '#d946ef', // Fuchsia 500
];

function getSlotColor(slotIdx) {
  return SLOT_PALETTE[slotIdx % SLOT_PALETTE.length];
}

// Global App State
const state = {
  activeTab: 'file', // 'file' or 'generate'
  presets: {},
  latestSolution: null,
  network: null,
  networkNodes: null,
  networkEdges: null,
  animation: {
    steps: [],
    currentStep: 0,
    isPlaying: false,
    timer: null,
    intervalMs: 700
  },
  charts: {
    slots: null,
    runtime: null
  }
};

// DOM Elements
const elements = {
  tabFileBtn: document.getElementById('tab-file-btn'),
  tabGenBtn: document.getElementById('tab-generate-btn'),
  panelFile: document.getElementById('option-file-panel'),
  panelGen: document.getElementById('option-generate-panel'),
  presetSelect: document.getElementById('preset-select'),
  rawInputText: document.getElementById('raw-input-text'),
  fileUpload: document.getElementById('file-upload'),
  
  genNRange: document.getElementById('gen-n-range'),
  genNInput: document.getElementById('gen-n-input'),
  genRRange: document.getElementById('gen-r-range'),
  genRInput: document.getElementById('gen-r-input'),
  genDensityRange: document.getElementById('gen-density-range'),
  genDensityVal: document.getElementById('gen-density-val'),
  timeoutSelect: document.getElementById('timeout-select'),

  btnSolve: document.getElementById('btn-solve'),
  loadingState: document.getElementById('loading-state'),
  errorBanner: document.getElementById('error-banner'),
  errorMessage: document.getElementById('error-message'),
  resultsSection: document.getElementById('results-section'),

  optimalityBadge: document.getElementById('optimality-badge'),
  cardBestSlots: document.getElementById('card-best-slots'),
  cardBestMethod: document.getElementById('card-best-method'),
  cardLowerBound: document.getElementById('card-lower-bound'),
  cardNR: document.getElementById('card-n-r'),
  cardMConflicts: document.getElementById('card-m-conflicts'),
  cardExactTime: document.getElementById('card-exact-time'),
  cardExactStatus: document.getElementById('card-exact-status'),
  comparisonTbody: document.getElementById('comparison-tbody'),

  slotListContainer: document.getElementById('slot-list-container'),
  timetableGridTable: document.getElementById('timetable-grid-table'),
  btnDownloadCsv: document.getElementById('btn-download-csv'),
  graphSlotLegend: document.getElementById('graph-slot-legend'),
  networkContainer: document.getElementById('network-container'),

  animPlayBtn: document.getElementById('anim-play-btn'),
  animPlayText: document.getElementById('anim-play-text'),
  animPrevBtn: document.getElementById('anim-prev-btn'),
  animNextBtn: document.getElementById('anim-next-btn'),
  animResetBtn: document.getElementById('anim-reset-btn'),
  animScrubber: document.getElementById('anim-scrubber'),
  animStepCounter: document.getElementById('anim-step-counter'),
  animStatusText: document.getElementById('anim-status-text'),
  animLatestBadge: document.getElementById('anim-latest-badge'),

  btnRunBenchmark: document.getElementById('btn-run-benchmark'),
  chartSlotsCanvas: document.getElementById('chart-slots'),
  chartRuntimeCanvas: document.getElementById('chart-runtime')
};

// =====================================================================
// Initialization
// =====================================================================
document.addEventListener('DOMContentLoaded', async () => {
  if (window.lucide) {
    lucide.createIcons();
  }
  setupEventHandlers();
  await loadPresets();

  // Load small preset by default and run solve
  if (state.presets['small']) {
    elements.presetSelect.value = 'small';
    elements.rawInputText.value = state.presets['small'].text;
    solveCurrent();
  }
});

function setupEventHandlers() {
  // Tabs
  elements.tabFileBtn.addEventListener('click', () => switchTab('file'));
  elements.tabGenBtn.addEventListener('click', () => switchTab('generate'));

  // Preset Select
  elements.presetSelect.addEventListener('change', (e) => {
    const key = e.target.value;
    if (key && state.presets[key]) {
      elements.rawInputText.value = state.presets[key].text;
    }
  });

  // File Upload
  elements.fileUpload.addEventListener('change', (e) => {
    const file = e.target.files[0];
    if (file) {
      const reader = new FileReader();
      reader.onload = (evt) => {
        elements.rawInputText.value = evt.target.result;
        elements.presetSelect.value = '';
      };
      reader.readAsText(file);
    }
  });

  // Generator Range/Input sync
  elements.genNRange.addEventListener('input', (e) => {
    elements.genNInput.value = e.target.value;
  });
  elements.genNInput.addEventListener('input', (e) => {
    elements.genNRange.value = e.target.value;
  });

  elements.genRRange.addEventListener('input', (e) => {
    elements.genRInput.value = e.target.value;
  });
  elements.genRInput.addEventListener('input', (e) => {
    elements.genRRange.value = e.target.value;
  });

  elements.genDensityRange.addEventListener('input', (e) => {
    elements.genDensityVal.textContent = parseFloat(e.target.value).toFixed(2);
  });

  // Solve button
  elements.btnSolve.addEventListener('click', () => solveCurrent());

  // CSV download
  elements.btnDownloadCsv.addEventListener('click', () => downloadTimetableCsv());

  // Animation controls
  elements.animPlayBtn.addEventListener('click', () => togglePlayAnimation());
  elements.animPrevBtn.addEventListener('click', () => stepAnimation(-1));
  elements.animNextBtn.addEventListener('click', () => stepAnimation(1));
  elements.animResetBtn.addEventListener('click', () => resetAnimation());
  elements.animScrubber.addEventListener('input', (e) => {
    pauseAnimation();
    setAnimationStep(parseInt(e.target.value, 10));
  });

  // Benchmark trigger
  elements.btnRunBenchmark.addEventListener('click', () => runBenchmark());
}

function switchTab(tab) {
  state.activeTab = tab;
  if (tab === 'file') {
    elements.tabFileBtn.className = "px-4 py-2 rounded-lg text-xs font-semibold transition flex items-center gap-2 bg-sky-600 text-white shadow-md";
    elements.tabGenBtn.className = "px-4 py-2 rounded-lg text-xs font-semibold transition flex items-center gap-2 text-slate-400 hover:text-white";
    elements.panelFile.classList.remove('hidden');
    elements.panelGen.classList.add('hidden');
  } else {
    elements.tabGenBtn.className = "px-4 py-2 rounded-lg text-xs font-semibold transition flex items-center gap-2 bg-sky-600 text-white shadow-md";
    elements.tabFileBtn.className = "px-4 py-2 rounded-lg text-xs font-semibold transition flex items-center gap-2 text-slate-400 hover:text-white";
    elements.panelFile.classList.add('hidden');
    elements.panelGen.classList.remove('hidden');
  }
}

async function loadPresets() {
  try {
    const res = await fetch('/api/presets');
    state.presets = await res.json();
  } catch (err) {
    console.error("Failed to load presets", err);
  }
}

// =====================================================================
// Solve Engine
// =====================================================================
async function solveCurrent() {
  hideError();
  showLoading(true);

  const payload = {
    mode: state.activeTab,
    time_limit: parseFloat(elements.timeoutSelect.value)
  };

  if (state.activeTab === 'file') {
    payload.text = elements.rawInputText.value.trim();
    if (!payload.text) {
      showError("Please enter input text or load a preset sample.");
      showLoading(false);
      return;
    }
  } else {
    payload.n = parseInt(elements.genNInput.value, 10);
    payload.r = parseInt(elements.genRInput.value, 10);
    payload.density = parseFloat(elements.genDensityRange.value);
  }

  try {
    const response = await fetch('/api/solve', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    const data = await response.json();
    showLoading(false);

    if (!data.success) {
      showError(data.error || "Failed to solve instance.");
      return;
    }

    state.latestSolution = data;
    renderResults(data);
    elements.resultsSection.classList.remove('hidden');
    elements.resultsSection.scrollIntoView({ behavior: 'smooth' });

  } catch (err) {
    showLoading(false);
    showError("Network error: " + err.message);
  }
}

function showLoading(isLoading) {
  if (isLoading) {
    elements.loadingState.classList.remove('hidden');
    elements.btnSolve.disabled = true;
    elements.btnSolve.classList.add('opacity-75', 'cursor-not-allowed');
  } else {
    elements.loadingState.classList.add('hidden');
    elements.btnSolve.disabled = false;
    elements.btnSolve.classList.remove('opacity-75', 'cursor-not-allowed');
  }
}

function showError(msg) {
  elements.errorMessage.textContent = msg;
  elements.errorBanner.classList.remove('hidden');
}

function hideError() {
  elements.errorBanner.classList.add('hidden');
}

// =====================================================================
// Render Solution
// =====================================================================
function renderResults(data) {
  renderOutput1(data);
  renderOutput2(data);
  renderOutput3(data);
  renderGraphVisualization(data);
  initAnimation(data);
  initBenchmarkCharts(data);
}

// --- Output 1: Metrics & Comparison Table ---
function renderOutput1(data) {
  elements.cardBestSlots.textContent = data.best_slots;
  elements.cardBestMethod.textContent = `Via ${data.algorithms[data.best_method].name}`;
  elements.cardLowerBound.textContent = data.lower_bound;
  elements.cardNR.textContent = `${data.n} Courses`;
  elements.cardMConflicts.textContent = `Conflicts: ${data.m} | Capacity R: ${data.r}`;

  const exAlg = data.algorithms.exact;
  elements.cardExactTime.textContent = `${exAlg.runtime}s`;
  elements.cardExactStatus.textContent = exAlg.proven_optimal ? "Optimal Search Finished" : "Timed Out";

  // Optimality Badge
  if (data.is_optimal) {
    elements.optimalityBadge.className = "px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-1.5 badge-optimal";
    elements.optimalityBadge.innerHTML = `<i data-lucide="check-circle-2" class="w-3.5 h-3.5"></i> Proven Optimal (${data.best_slots} Slots)`;
  } else {
    elements.optimalityBadge.className = "px-3 py-1 rounded-full text-xs font-bold border flex items-center gap-1.5 badge-heuristic";
    elements.optimalityBadge.innerHTML = `<i data-lucide="info" class="w-3.5 h-3.5"></i> Heuristic Bound (${data.best_slots} Slots)`;
  }

  // Comparison Table
  const algKeys = ['welsh_powell', 'dsatur', 'exact'];
  const tbody = elements.comparisonTbody;
  tbody.innerHTML = '';

  algKeys.forEach((key) => {
    const alg = data.algorithms[key];
    const isBest = (key === data.best_method);
    const tr = document.createElement('tr');
    tr.className = isBest ? "bg-sky-500/10 font-semibold" : "hover:bg-slate-700/30 transition";

    const typeBadge = key === 'exact' 
      ? '<span class="px-2 py-0.5 rounded text-[10px] bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">Exact B&B</span>'
      : '<span class="px-2 py-0.5 rounded text-[10px] bg-slate-700 text-slate-300">Greedy Heuristic</span>';

    const optimalText = key === 'exact'
      ? (alg.proven_optimal ? '<span class="text-emerald-400 font-bold">Yes (Proven)</span>' : '<span class="text-amber-400">No (Timeout)</span>')
      : '<span class="text-slate-400">No (Heuristic)</span>';

    tr.innerHTML = `
      <td class="px-5 py-3 flex items-center gap-2">
        ${isBest ? '<i data-lucide="award" class="w-4 h-4 text-sky-400"></i>' : ''}
        ${alg.name}
      </td>
      <td class="px-5 py-3">${typeBadge}</td>
      <td class="px-5 py-3 text-center text-sm font-bold ${isBest ? 'text-sky-300' : 'text-slate-200'}">${alg.slots}</td>
      <td class="px-5 py-3 text-right font-mono">${alg.runtime}s</td>
      <td class="px-5 py-3 text-center">${optimalText}</td>
    `;
    tbody.appendChild(tr);
  });

  if (window.lucide) {
    lucide.createIcons();
  }
}

// --- Output 2: Slot-wise Courses ---
function renderOutput2(data) {
  const container = elements.slotListContainer;
  container.innerHTML = '';

  const slotCourses = data.slot_wise_courses;
  const slotKeys = Object.keys(slotCourses);

  slotKeys.forEach((slotLabel, idx) => {
    const courses = slotCourses[slotLabel];
    const color = getSlotColor(idx);

    const card = document.createElement('div');
    card.className = "p-3 rounded-xl bg-slate-900/90 border border-slate-800 hover:border-slate-700 transition flex flex-col gap-2 cursor-pointer";
    card.title = `Click to highlight Slot ${idx + 1} courses in graph`;

    card.innerHTML = `
      <div class="flex items-center justify-between">
        <div class="flex items-center gap-2">
          <span class="w-3.5 h-3.5 rounded-full shadow" style="background-color: ${color}"></span>
          <span class="text-xs font-bold text-white">${slotLabel}</span>
        </div>
        <span class="text-[10px] font-medium text-slate-400">${courses.length} / ${data.r} Halls</span>
      </div>
      <div class="flex flex-wrap gap-1.5 pt-1">
        ${courses.map(c => `
          <span class="px-2 py-0.5 rounded text-[11px] font-bold text-slate-900 shadow-sm" style="background-color: ${color}">
            C${c}
          </span>
        `).join('')}
      </div>
    `;

    // Highlight on click
    card.addEventListener('click', () => {
      highlightSlotCourses(courses);
    });

    container.appendChild(card);
  });
}

function highlightSlotCourses(courseIds) {
  if (!state.network || !state.networkNodes) return;
  state.network.selectNodes(courseIds);
}

// --- Output 3: Timetable Grid (Matching Color Scheme) ---
function renderOutput3(data) {
  const table = elements.timetableGridTable;
  table.innerHTML = '';

  // Header row: Slot Label + Hall 1..Hall R
  const thead = document.createElement('thead');
  const trHead = document.createElement('tr');
  trHead.className = "bg-slate-950 text-slate-300 text-xs font-bold uppercase tracking-wider";

  const thSlot = document.createElement('th');
  thSlot.className = "p-3 border border-slate-700 w-24 text-left pl-4";
  thSlot.textContent = "Slot";
  trHead.appendChild(thSlot);

  for (let i = 0; i < data.r; i++) {
    const thHall = document.createElement('th');
    thHall.className = "p-3 border border-slate-700";
    thHall.textContent = `Hall ${i + 1}`;
    trHead.appendChild(thHall);
  }
  thead.appendChild(trHead);
  table.appendChild(thead);

  // Body rows
  const tbody = document.createElement('tbody');
  data.grid_rows.forEach((row) => {
    const tr = document.createElement('tr');
    tr.className = "timetable-row border-b border-slate-700";

    const color = getSlotColor(row.slot_index);

    // Slot Header Cell
    const tdSlot = document.createElement('td');
    tdSlot.className = "p-3 border border-slate-700 text-left pl-4 font-bold text-xs text-white";
    tdSlot.style.backgroundColor = color;
    tdSlot.style.color = '#0f172a'; // Dark contrasting text
    tdSlot.textContent = row.slot_label;
    tr.appendChild(tdSlot);

    // Hall Cells (colored with matching color scheme)
    row.halls.forEach((course) => {
      const tdHall = document.createElement('td');
      tdHall.className = "p-3 border border-slate-700 timetable-cell font-semibold text-xs";

      if (course !== null) {
        // Active exam hall
        tdHall.style.backgroundColor = `${color}33`; // 20% opacity matching color
        tdHall.style.borderLeft = `3px solid ${color}`;
        tdHall.innerHTML = `
          <div class="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-md text-xs font-bold text-slate-100 bg-slate-900/80 border border-slate-700 shadow-sm">
            <span class="w-2 h-2 rounded-full" style="background-color: ${color}"></span>
            Course ${course}
          </div>
        `;
      } else {
        // Empty hall
        tdHall.className += " text-slate-500 bg-slate-950/40 italic";
        tdHall.textContent = "— Empty —";
      }
      tr.appendChild(tdHall);
    });

    tbody.appendChild(tr);
  });

  table.appendChild(tbody);
}

function downloadTimetableCsv() {
  if (!state.latestSolution) return;
  const csvContent = state.latestSolution.csv_content;
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
  const url = URL.createObjectURL(blob);
  const link = document.createElement('a');
  link.setAttribute('href', url);
  link.setAttribute('download', 'exam_timetable.csv');
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
}

// =====================================================================
// Visualization 1: Interactive Vis.js Conflict Graph
// =====================================================================
function renderGraphVisualization(data) {
  const container = elements.networkContainer;
  const legendContainer = elements.graphSlotLegend;
  legendContainer.innerHTML = '';

  // Render Legend Dots
  for (let s = 0; s < data.best_slots; s++) {
    const col = getSlotColor(s);
    const span = document.createElement('span');
    span.className = "inline-flex items-center gap-1 px-2 py-0.5 rounded-full bg-slate-900 border border-slate-800 text-[11px] text-slate-300";
    span.innerHTML = `<span class="w-2.5 h-2.5 rounded-full" style="background-color: ${col}"></span> Slot ${s + 1}`;
    legendContainer.appendChild(span);
  }

  // Build Vis.js nodes and edges
  const nodes = data.graph.nodes.map(n => {
    const col = getSlotColor(n.slot);
    return {
      id: n.id,
      label: n.label,
      title: n.title,
      color: {
        background: col,
        border: '#0f172a',
        highlight: { background: '#ffffff', border: col }
      },
      font: { color: '#0f172a', face: 'system-ui', size: 12, bold: true },
      shape: 'circle',
      size: 20 + Math.min(n.degree * 2, 16),
      borderWidth: 2
    };
  });

  const edges = data.graph.edges.map(e => ({
    from: e.from,
    to: e.to,
    color: { color: 'rgba(148, 163, 184, 0.35)', highlight: '#38bdf8' },
    width: 1.5,
    smooth: { type: 'continuous' }
  }));

  state.networkNodes = new vis.DataSet(nodes);
  state.networkEdges = new vis.DataSet(edges);

  const visData = {
    nodes: state.networkNodes,
    edges: state.networkEdges
  };

  const options = {
    physics: {
      stabilization: { iterations: 120 },
      barnesHut: {
        gravitationalConstant: -3500,
        centralGravity: 0.35,
        springLength: 95,
        springConstant: 0.04
      }
    },
    interaction: {
      hover: true,
      tooltipDelay: 100,
      zoomView: true
    }
  };

  if (state.network) {
    state.network.destroy();
  }
  state.network = new vis.Network(container, visData, options);
}

// =====================================================================
// Visualization 2: Assignment Process Animation
// =====================================================================
function initAnimation(data) {
  pauseAnimation();
  state.animation.steps = data.animation_steps || [];
  state.animation.currentStep = 0;

  const totalSteps = state.animation.steps.length;
  elements.animScrubber.max = totalSteps;
  elements.animScrubber.value = 0;
  elements.animStepCounter.textContent = `Step 0/${totalSteps}`;
  elements.animStatusText.textContent = "Ready. Press Play to animate course-to-slot assignment order.";
  elements.animLatestBadge.classList.add('hidden');
}

function togglePlayAnimation() {
  if (state.animation.isPlaying) {
    pauseAnimation();
  } else {
    playAnimation();
  }
}

function playAnimation() {
  const totalSteps = state.animation.steps.length;
  if (state.animation.currentStep >= totalSteps) {
    state.animation.currentStep = 0;
  }
  state.animation.isPlaying = true;
  elements.animPlayText.textContent = "Pause";
  elements.animPlayBtn.querySelector('i').setAttribute('data-lucide', 'pause');
  if (window.lucide) lucide.createIcons();

  state.animation.timer = setInterval(() => {
    if (state.animation.currentStep < totalSteps) {
      stepAnimation(1);
    } else {
      pauseAnimation();
    }
  }, state.animation.intervalMs);
}

function pauseAnimation() {
  state.animation.isPlaying = false;
  clearInterval(state.animation.timer);
  elements.animPlayText.textContent = "Play";
  elements.animPlayBtn.querySelector('i').setAttribute('data-lucide', 'play');
  if (window.lucide) lucide.createIcons();
}

function stepAnimation(direction) {
  const total = state.animation.steps.length;
  let next = state.animation.currentStep + direction;
  if (next < 0) next = 0;
  if (next > total) next = total;
  setAnimationStep(next);
}

function resetAnimation() {
  pauseAnimation();
  setAnimationStep(0);
}

function setAnimationStep(stepIdx) {
  state.animation.currentStep = stepIdx;
  elements.animScrubber.value = stepIdx;
  elements.animStepCounter.textContent = `Step ${stepIdx}/${state.animation.steps.length}`;

  if (!state.networkNodes || !state.latestSolution) return;

  if (stepIdx === 0) {
    // Reset all nodes to unassigned gray
    const updates = state.latestSolution.graph.nodes.map(n => ({
      id: n.id,
      color: { background: '#64748b', border: '#334155' }
    }));
    state.networkNodes.update(updates);
    elements.animStatusText.textContent = "All courses unassigned.";
    elements.animLatestBadge.classList.add('hidden');
    return;
  }

  const stepData = state.animation.steps[stepIdx - 1];
  const assignedMap = stepData.assignment;

  // Update node colors in vis.js
  const updates = state.latestSolution.graph.nodes.map(n => {
    const s = assignedMap[n.id.toString()];
    if (s !== undefined) {
      const col = getSlotColor(s);
      return {
        id: n.id,
        color: { background: col, border: n.id === stepData.course ? '#ffffff' : '#0f172a' },
        borderWidth: n.id === stepData.course ? 4 : 2
      };
    } else {
      return {
        id: n.id,
        color: { background: '#475569', border: '#334155' },
        borderWidth: 1.5
      };
    }
  });

  state.networkNodes.update(updates);

  // Status message
  const slotNum = stepData.slot + 1;
  elements.animStatusText.textContent = `Step ${stepIdx}: Assigned Course ${stepData.course} to Slot ${slotNum}.`;
  elements.animLatestBadge.textContent = `Course ${stepData.course} ➜ Slot ${slotNum}`;
  elements.animLatestBadge.classList.remove('hidden');
}

// =====================================================================
// Visualization 3: Benchmark Chart as N Increases (Chart.js)
// =====================================================================
function initBenchmarkCharts(data) {
  runBenchmark();
}

async function runBenchmark() {
  if (!state.latestSolution) return;

  const r = state.latestSolution.r;
  const density = 0.25;
  const nValues = [8, 12, 16, 20, 24, 28, 32];

  elements.btnRunBenchmark.disabled = true;
  elements.btnRunBenchmark.classList.add('opacity-50');

  try {
    const response = await fetch('/api/benchmark', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ r, density, n_values: nValues })
    });
    const benchData = await response.json();
    elements.btnRunBenchmark.disabled = false;
    elements.btnRunBenchmark.classList.remove('opacity-50');

    if (benchData.success) {
      renderBenchmarkCharts(benchData);
    }
  } catch (err) {
    elements.btnRunBenchmark.disabled = false;
    elements.btnRunBenchmark.classList.remove('opacity-50');
    console.error("Benchmark error", err);
  }
}

function renderBenchmarkCharts(bench) {
  const nLabels = bench.n_values.map(n => `N=${n}`);
  const wp = bench.results.welsh_powell;
  const ds = bench.results.dsatur;
  const ex = bench.results.exact;

  // Chart 1: Slots vs N
  if (state.charts.slots) {
    state.charts.slots.destroy();
  }
  state.charts.slots = new Chart(elements.chartSlotsCanvas, {
    type: 'line',
    data: {
      labels: nLabels,
      datasets: [
        {
          label: 'Welsh-Powell (Greedy)',
          data: wp.slots,
          borderColor: '#f97316',
          backgroundColor: '#f97316',
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 4
        },
        {
          label: 'DSatur (Greedy)',
          data: ds.slots,
          borderColor: '#38bdf8',
          backgroundColor: '#38bdf8',
          borderWidth: 2,
          pointRadius: 5
        },
        {
          label: 'Exact (Branch & Bound)',
          data: ex.slots,
          borderColor: '#10b981',
          backgroundColor: '#10b981',
          borderWidth: 2.5,
          pointRadius: 5
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#cbd5e1', font: { size: 10 } } }
      },
      scales: {
        x: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
        y: {
          grid: { color: '#334155' },
          ticks: { color: '#94a3b8', stepSize: 1 },
          title: { display: true, text: 'Slots Count', color: '#94a3b8' }
        }
      }
    }
  });

  // Chart 2: Runtime vs N (Log scale)
  if (state.charts.runtime) {
    state.charts.runtime.destroy();
  }
  state.charts.runtime = new Chart(elements.chartRuntimeCanvas, {
    type: 'line',
    data: {
      labels: nLabels,
      datasets: [
        {
          label: 'Welsh-Powell',
          data: wp.times,
          borderColor: '#f97316',
          backgroundColor: '#f97316',
          borderWidth: 2,
          borderDash: [5, 5],
          pointRadius: 4
        },
        {
          label: 'DSatur',
          data: ds.times,
          borderColor: '#38bdf8',
          backgroundColor: '#38bdf8',
          borderWidth: 2,
          pointRadius: 5
        },
        {
          label: 'Exact B&B',
          data: ex.times,
          borderColor: '#10b981',
          backgroundColor: '#10b981',
          borderWidth: 2.5,
          pointRadius: 5
        }
      ]
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: { labels: { color: '#cbd5e1', font: { size: 10 } } }
      },
      scales: {
        x: { grid: { color: '#334155' }, ticks: { color: '#94a3b8' } },
        y: {
          type: 'logarithmic',
          grid: { color: '#334155' },
          ticks: { color: '#94a3b8' },
          title: { display: true, text: 'Seconds (Log Scale)', color: '#94a3b8' }
        }
      }
    }
  });
}
