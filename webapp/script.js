// Basic NFProgress web application

// Load projects from localStorage
function loadProjects() {
  const data = localStorage.getItem('projects');
  return data ? JSON.parse(data) : [];
}

// Save projects to localStorage
function saveProjects(projects) {
  localStorage.setItem('projects', JSON.stringify(projects));
}

let projects = loadProjects();
let currentIndex = null; // index of opened project
let chart = null; // Chart.js instance

// ----- Utility helpers -----
function byId(id) { return document.getElementById(id); }
function show(el) { el.classList.remove('hidden'); }
function hide(el) { el.classList.add('hidden'); }

function generateId() {
  return Date.now().toString(36) + Math.random().toString(36).slice(2);
}

// ----- Rendering -----
function renderProjects() {
  const list = byId('projects');
  list.innerHTML = '';
  projects.forEach((p, idx) => {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    const total = projectTotal(p);
    btn.textContent = `${p.title} (${total}/${p.goal})`;
    btn.onclick = () => openProject(idx);
    li.appendChild(btn);
    list.appendChild(li);
  });
}

function openProject(idx) {
  currentIndex = idx;
  show(byId('project-details'));
  hide(byId('project-list'));
  renderProjectDetails();
}

function renderProjectDetails() {
  const project = projects[currentIndex];
  byId('project-title').textContent = project.title;
  byId('project-goal').textContent = `Goal: ${project.goal}`;
  byId('project-total').textContent = `Total: ${projectTotal(project)}`;
  renderStages(project);
  renderEntries(project);
  updateChart(project);
}

function renderStages(project) {
  const list = byId('stages');
  list.innerHTML = '';
  project.stages = project.stages || [];
  project.stages.forEach(stage => {
    const li = document.createElement('li');
    const info = document.createElement('div');
    const progress = stageProgress(stage);
    info.textContent = `${stage.title} (${progress}/${stage.goal})`;
    li.appendChild(info);
    list.appendChild(li);
  });
}

function renderEntries(project) {
  const list = byId('entries');
  list.innerHTML = '';
  const allEntries = getAllEntries(project);
  allEntries.forEach(entry => {
    const li = document.createElement('li');
    const stage = project.stages?.find(s => s.id === entry.stageId);
    const stageInfo = stage ? `[${stage.title}] ` : '';
    li.textContent = `${stageInfo}${entry.date}: ${entry.count} chars`;
    list.appendChild(li);
  });
}

function updateChart(project) {
  const ctx = byId('progress-chart').getContext('2d');
  const data = cumulativeData(project);
  if (chart) chart.destroy();
  chart = new Chart(ctx, {
    type: 'line',
    data: {
      labels: data.map(d => d.date),
      datasets: [{
        label: 'Progress',
        data: data.map(d => d.total),
        fill: false,
        borderColor: '#4caf50'
      }]
    },
    options: {
      responsive: true,
      scales: { x: { ticks: { autoSkip: true } } }
    }
  });
}

// ----- Data helpers -----
function projectTotal(project) {
  return getAllEntries(project).reduce((sum, e) => sum + e.count, 0);
}

function getAllEntries(project) {
  const direct = project.entries || [];
  const stageEntries = (project.stages || []).flatMap(s => s.entries || []);
  return [...direct, ...stageEntries].sort((a,b) => a.date.localeCompare(b.date));
}

function stageProgress(stage) {
  return (stage.entries || []).reduce((s, e) => s + e.count, 0);
}

function cumulativeData(project) {
  const entries = getAllEntries(project);
  let total = 0;
  return entries.map(e => {
    total += e.count;
    return { date: e.date, total };
  });
}

// ----- Modals -----
function showProjectDialog(edit = false) {
  byId('project-dialog-title').textContent = edit ? 'Edit Project' : 'New Project';
  const project = edit ? projects[currentIndex] : { title: '', goal: 1000 };
  byId('project-title-input').value = project.title || '';
  byId('project-goal-input').value = project.goal || 1000;
  byId('project-save-btn').onclick = () => {
    if (edit) {
      project.title = byId('project-title-input').value || 'Untitled';
      project.goal = parseInt(byId('project-goal-input').value, 10) || 0;
      projects[currentIndex] = project;
    } else {
      const newProject = {
        id: generateId(),
        title: byId('project-title-input').value || 'Untitled',
        goal: parseInt(byId('project-goal-input').value, 10) || 0,
        entries: [],
        stages: []
      };
      projects.push(newProject);
    }
    saveProjects(projects);
    hide(byId('project-dialog'));
    renderProjects();
    if (edit) renderProjectDetails();
  };
  byId('project-cancel-btn').onclick = () => hide(byId('project-dialog'));
  show(byId('project-dialog'));
}

function showStageDialog() {
  const project = projects[currentIndex];
  byId('stage-dialog-title').textContent = 'New Stage';
  byId('stage-title-input').value = '';
  byId('stage-goal-input').value = 1000;
  byId('stage-save-btn').onclick = () => {
    const stage = {
      id: generateId(),
      title: byId('stage-title-input').value || 'Stage',
      goal: parseInt(byId('stage-goal-input').value, 10) || 0,
      entries: []
    };
    project.stages.push(stage);
    saveProjects(projects);
    hide(byId('stage-dialog'));
    renderProjectDetails();
  };
  byId('stage-cancel-btn').onclick = () => hide(byId('stage-dialog'));
  show(byId('stage-dialog'));
}

function showEntryDialog() {
  const project = projects[currentIndex];
  byId('entry-dialog-title').textContent = 'New Entry';
  byId('entry-date').valueAsDate = new Date();
  byId('entry-count').value = '';
  const select = byId('entry-stage-select');
  select.innerHTML = '<option value="">(No stage)</option>';
  project.stages.forEach(s => {
    const opt = document.createElement('option');
    opt.value = s.id;
    opt.textContent = s.title;
    select.appendChild(opt);
  });
  byId('entry-save-btn').onclick = () => {
    const entry = {
      id: generateId(),
      date: byId('entry-date').value,
      count: parseInt(byId('entry-count').value, 10) || 0,
      stageId: select.value || null
    };
    if (entry.stageId) {
      const stage = project.stages.find(s => s.id === entry.stageId);
      stage.entries.push(entry);
    } else {
      project.entries.push(entry);
    }
    saveProjects(projects);
    hide(byId('entry-dialog'));
    renderProjectDetails();
  };
  byId('entry-cancel-btn').onclick = () => hide(byId('entry-dialog'));
  show(byId('entry-dialog'));
}

// ----- Event bindings -----
window.addEventListener('DOMContentLoaded', () => {
  renderProjects();
  byId('add-project-btn').onclick = () => showProjectDialog(false);
  byId('edit-project-btn').onclick = () => showProjectDialog(true);
  byId('delete-project-btn').onclick = () => {
    if (currentIndex !== null) {
      projects.splice(currentIndex, 1);
      saveProjects(projects);
      hide(byId('project-details'));
      show(byId('project-list'));
      renderProjects();
    }
  };
  byId('back-btn').onclick = () => {
    hide(byId('project-details'));
    show(byId('project-list'));
    renderProjects();
  };
  byId('add-stage-btn').onclick = showStageDialog;
  byId('add-entry-btn').onclick = showEntryDialog;
});
