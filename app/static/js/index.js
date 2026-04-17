async function loadDashboard() {
  try {
    var data = await api.listTasks({ page: 1, page_size: 100 });
    var tasks = data.items || [];
    var enabled = tasks.filter(function(t) { return t.enabled; }).length;
    document.getElementById('stat-total').textContent = data.total;
    document.getElementById('stat-enabled').textContent = enabled;
    document.getElementById('stat-disabled').textContent = data.total - enabled;
  } catch (e) {
    document.getElementById('stat-total').textContent = 'Error';
  }

  try {
    var health = await api.getHealth();
    var el = document.getElementById('stat-health');
    el.textContent = health.status === 'ok' ? 'Running' : health.status;
    el.classList.add('text-success');
  } catch (e) {
    var el = document.getElementById('stat-health');
    el.textContent = 'Down';
    el.classList.add('text-danger');
  }

  try {
    var data = await api.listExecutions({ page: 1, page_size: 10 });
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

      var tdTask = tr.insertCell();
      var a = document.createElement('a');
      a.href = 'task-detail.html?id=' + r.task_id;
      a.textContent = r.task_name;
      tdTask.appendChild(a);

      var tdStatus = tr.insertCell();
      tdStatus.appendChild(makeStatusBadge(r.status));

      var tdTrigger = tr.insertCell();
      var tb = document.createElement('span');
      tb.className = 'badge ' + (r.trigger_type === 'manual' ? 'badge-primary' : 'badge-info');
      tb.textContent = r.trigger_type;
      tdTrigger.appendChild(tb);

      tr.insertCell().textContent = formatDuration(r.duration_ms);
      tr.insertCell().textContent = r.exit_code != null ? r.exit_code : '-';
      tr.insertCell().textContent = formatTime(r.started_at);
    });
  } catch (e) {
    var tbody = document.getElementById('exec-table');
    tbody.innerHTML = '';
    var row = tbody.insertRow();
    var cell = row.insertCell();
    cell.colSpan = 6;
    cell.textContent = 'Failed to load executions';
    cell.className = 'empty-state';
  }
}

document.addEventListener('DOMContentLoaded', loadDashboard);
