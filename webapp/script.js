function loadProjects() {
  const data = localStorage.getItem('projects');
  return data ? JSON.parse(data) : [];
}

function saveProjects(projects) {
  localStorage.setItem('projects', JSON.stringify(projects));
}

function renderProjects() {
  const projects = loadProjects();
  const list = document.getElementById('projects');
  list.innerHTML = '';
  projects.forEach((p, index) => {
    const li = document.createElement('li');
    const btn = document.createElement('button');
    btn.textContent = p.title + ' (' + p.progress + '/' + p.goal + ')';
    btn.onclick = () => openProject(index);
    li.appendChild(btn);
    list.appendChild(li);
  });
}

function openProject(idx) {
  const projects = loadProjects();
  const project = projects[idx];
  currentProject = { index: idx, data: project };

  document.getElementById('project-list').classList.add('hidden');
  document.getElementById('project-details').classList.remove('hidden');
  document.getElementById('project-title').textContent = project.title;
  renderEntries();
}

function renderEntries() {
  const entries = currentProject.data.entries || [];
  const ul = document.getElementById('entries');
  ul.innerHTML = '';
  let total = 0;
  entries.forEach(e => { total += e.count; });
  currentProject.data.progress = total;
  document.getElementById('project-progress').textContent = 'Progress: ' + total + '/' + currentProject.data.goal;

  entries.forEach((e, i) => {
    const li = document.createElement('li');
    li.textContent = e.date + ': ' + e.count + ' chars';
    ul.appendChild(li);
  });
  saveCurrentProject();
}

function saveCurrentProject() {
  const projects = loadProjects();
  projects[currentProject.index] = currentProject.data;
  saveProjects(projects);
}

function showProjectDialog() {
  document.getElementById('project-title-input').value = '';
  document.getElementById('project-goal-input').value = 10000;
  document.getElementById('project-dialog').classList.remove('hidden');
}

function hideProjectDialog() {
  document.getElementById('project-dialog').classList.add('hidden');
}

function addProject() {
  const title = document.getElementById('project-title-input').value || 'Untitled';
  const goal = parseInt(document.getElementById('project-goal-input').value, 10) || 0;
  const projects = loadProjects();
  projects.push({ title, goal, progress: 0, entries: [] });
  saveProjects(projects);
  hideProjectDialog();
  renderProjects();
}

function showEntryDialog() {
  document.getElementById('entry-date').valueAsDate = new Date();
  document.getElementById('entry-count').value = '';
  document.getElementById('entry-dialog').classList.remove('hidden');
}

function hideEntryDialog() {
  document.getElementById('entry-dialog').classList.add('hidden');
}

function addEntry() {
  const date = document.getElementById('entry-date').value;
  const count = parseInt(document.getElementById('entry-count').value, 10) || 0;
  if (!currentProject.data.entries) currentProject.data.entries = [];
  currentProject.data.entries.push({ date, count });
  hideEntryDialog();
  renderEntries();
}

let currentProject = null;

// Event bindings
window.addEventListener('DOMContentLoaded', () => {
  renderProjects();
  document.getElementById('add-project-btn').onclick = showProjectDialog;
  document.getElementById('save-project-btn').onclick = addProject;
  document.getElementById('cancel-project-btn').onclick = hideProjectDialog;
  document.getElementById('back-btn').onclick = () => {
    document.getElementById('project-details').classList.add('hidden');
    document.getElementById('project-list').classList.remove('hidden');
    renderProjects();
  };
  document.getElementById('add-entry-btn').onclick = showEntryDialog;
  document.getElementById('save-entry-btn').onclick = addEntry;
  document.getElementById('cancel-entry-btn').onclick = hideEntryDialog;
});
