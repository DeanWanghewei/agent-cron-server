var taskId = null;
var execPage = 1;

function infoItem(label, value, mono) {
  var div = document.createElement('div');
  div.className = 'info-item';
  var lbl = document.createElement('div');
  lbl.className = 'info-label';
  lbl.textContent = label;
  var val = document.createElement('div');
  val.className = 'info-value' + (mono ? ' mono' : '');
  val.textContent = value || '-';
  div.appendChild(lbl);
  div.appendChild(val);
  return div;
}

async function loadTaskDetail() {
  var params = new URLSearchParams(window.location.search);
  taskId = parseInt(params.get('id'));
  if (!taskId) return;

  var task = await api.getTask(taskId);
  if (!task) {
    document.getElementById('task-title').textContent = 'Task not found';
    return;
  }

  document.title = task.name + ' - Agent Cron Server';
  document.getElementById('task-title').textContent = task.name;

  var grid = document.getElementById('task-info');
  grid.innerHTML = '';
  grid.appendChild(infoItem('ID', task.id));
  grid.appendChild(infoItem('Name', task.name));
  grid.appendChild(infoItem('Description', task.description));
  grid.appendChild(infoItem('Command', task.command, true));
  grid.appendChild(infoItem('Cron Expression', task.cron_expression));
  grid.appendChild(infoItem('Timezone', task.timezone));
  grid.appendChild(infoItem('Shell Mode', task.shell ? 'Yes' : 'No'));
  grid.appendChild(infoItem('Working Dir', task.working_dir));
  grid.appendChild(infoItem('Timeout', task.timeout + 's'));
  grid.appendChild(infoItem('Max Retries', task.max_retries));
  grid.appendChild(infoItem('Owner Agent', task.owner_agent));
  grid.appendChild(infoItem('Callback URL', task.callback_url));
  grid.appendChild(infoItem('Tags', task.tags ? task.tags.join(', ') : '-'));
  grid.appendChild(infoItem('Enabled', task.enabled ? 'Yes' : 'No'));
  grid.appendChild(infoItem('Created', formatTime(task.created_at)));

  var actions = document.getElementById('task-actions');
  actions.innerHTML = '';

  var triggerBtn = document.createElement('button');
  triggerBtn.className = 'btn btn-primary';
  triggerBtn.innerHTML = '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Trigger';
  triggerBtn.onclick = async function() {
    await api.triggerTask(taskId);
    alert('Task triggered');
    loadExecutions(1);
  };
  actions.appendChild(triggerBtn);

  var toggleBtn = document.createElement('button');
  toggleBtn.className = 'btn';
  toggleBtn.innerHTML = task.enabled
    ? '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg> Disable'
    : '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> Enable';
  toggleBtn.onclick = async function() {
    if (task.enabled) { await api.disableTask(taskId); } else { await api.enableTask(taskId); }
    loadTaskDetail();
  };
  actions.appendChild(toggleBtn);

  var delBtn = document.createElement('button');
  delBtn.className = 'btn btn-danger';
  delBtn.innerHTML = '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg> Delete';
  delBtn.onclick = async function() {
    if (!confirm('Delete this task and all execution history?')) return;
    await api.deleteTask(taskId);
    window.location.href = 'tasks.html';
  };
  actions.appendChild(delBtn);

  loadExecutions(1);
}

async function loadExecutions(page) {
  execPage = page || 1;
  var data = await api.listExecutions({ task_id: taskId, page: execPage, page_size: 15 });
  var tbody = document.getElementById('exec-table');
  tbody.innerHTML = '';

  if (!data.items || data.items.length === 0) {
    var row = tbody.insertRow();
    var cell = row.insertCell();
    cell.colSpan = 6;
    cell.textContent = 'No executions yet';
    cell.className = 'empty-state';
    return;
  }

  data.items.forEach(function(r) {
    var tr = tbody.insertRow();

    var tdId = tr.insertCell();
    var a = document.createElement('a');
    a.href = 'execution-detail.html?id=' + r.id;
    a.textContent = r.id;
    tdId.appendChild(a);

    tr.insertCell().appendChild(makeStatusBadge(r.status));
    var tdTrigger = tr.insertCell();
    var tb = document.createElement('span');
    tb.className = 'badge ' + (r.trigger_type === 'manual' ? 'badge-primary' : 'badge-info');
    tb.textContent = r.trigger_type;
    tdTrigger.appendChild(tb);
    tr.insertCell().textContent = formatDuration(r.duration_ms);
    tr.insertCell().textContent = r.exit_code != null ? r.exit_code : '-';
    tr.insertCell().textContent = formatTime(r.started_at);
  });

  var pagDiv = document.getElementById('pagination');
  pagDiv.innerHTML = '';
  var pagEl = makePagination(execPage, 15, data.total);
  if (pagEl) pagDiv.appendChild(pagEl);
}

function goPage(p) { loadExecutions(p); }

document.addEventListener('DOMContentLoaded', loadTaskDetail);
