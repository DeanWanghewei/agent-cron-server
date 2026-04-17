var currentPage = 1;

async function loadTasks(page) {
  page = page || 1;
  currentPage = page;
  var enabled = document.getElementById('filter-enabled').value;
  var params = { page: page, page_size: 20 };
  if (enabled) params.enabled = enabled;

  try {
    var data = await api.listTasks(params);
    var tbody = document.getElementById('tasks-table');
    tbody.innerHTML = '';

    if (!data.items || data.items.length === 0) {
      var row = tbody.insertRow();
      var cell = row.insertCell();
      cell.colSpan = 7;
      cell.textContent = 'No tasks found';
      cell.className = 'empty-state';
      return;
    }

    data.items.forEach(function(task) {
      var tr = tbody.insertRow();
      tr.insertCell().textContent = task.id;

      var tdName = tr.insertCell();
      var link = document.createElement('a');
      link.href = 'task-detail.html?id=' + task.id;
      link.textContent = task.name;
      tdName.appendChild(link);

      tr.insertCell().textContent = task.cron_expression;

      var tdStatus = tr.insertCell();
      var badge = document.createElement('span');
      badge.className = 'badge ' + (task.enabled ? 'badge-success' : 'badge-gray');
      badge.textContent = task.enabled ? 'enabled' : 'disabled';
      tdStatus.appendChild(badge);

      var tdCmd = tr.insertCell();
      tdCmd.textContent = task.command;
      tdCmd.className = 'command-cell';

      tr.insertCell().textContent = task.owner_agent || '-';

      var tdActions = tr.insertCell();
      var group = document.createElement('div');
      group.className = 'btn-group';

      var triggerBtn = document.createElement('button');
      triggerBtn.className = 'btn btn-sm btn-primary';
      triggerBtn.textContent = 'Trigger';
      triggerBtn.onclick = (function(tid, tname) {
        return function() { triggerTaskAction(tid, tname); };
      })(task.id, task.name);
      group.appendChild(triggerBtn);

      var toggleBtn = document.createElement('button');
      toggleBtn.className = 'btn btn-sm';
      toggleBtn.textContent = task.enabled ? 'Disable' : 'Enable';
      toggleBtn.onclick = (function(tid, isEnabled) {
        return function() { toggleTaskAction(tid, isEnabled); };
      })(task.id, task.enabled);
      group.appendChild(toggleBtn);

      var delBtn = document.createElement('button');
      delBtn.className = 'btn btn-sm btn-danger';
      delBtn.textContent = 'Delete';
      delBtn.onclick = (function(tid, tname) {
        return function() { deleteTaskAction(tid, tname); };
      })(task.id, task.name);
      group.appendChild(delBtn);

      tdActions.appendChild(group);
    });

    var pagDiv = document.getElementById('pagination');
    pagDiv.innerHTML = '';
    var pagEl = makePagination(page, 20, data.total);
    if (pagEl) pagDiv.appendChild(pagEl);
  } catch (e) {
    document.getElementById('tasks-table').innerHTML = '';
    var row = document.getElementById('tasks-table').insertRow();
    var cell = row.insertCell();
    cell.colSpan = 7;
    cell.textContent = 'Failed to load tasks';
    cell.className = 'empty-state';
  }
}

async function triggerTaskAction(id, name) {
  try {
    await api.triggerTask(id);
    alert('Task "' + name + '" triggered');
  } catch (e) {
    alert('Failed to trigger: ' + e.message);
  }
}

async function toggleTaskAction(id, currentlyEnabled) {
  try {
    if (currentlyEnabled) {
      await api.disableTask(id);
    } else {
      await api.enableTask(id);
    }
    loadTasks(currentPage);
  } catch (e) {
    alert('Failed: ' + e.message);
  }
}

async function deleteTaskAction(id, name) {
  if (!confirm('Delete task "' + name + '" and all its execution history?')) return;
  try {
    await api.deleteTask(id);
    loadTasks(currentPage);
  } catch (e) {
    alert('Failed to delete: ' + e.message);
  }
}

function goPage(p) { loadTasks(p); }

document.addEventListener('DOMContentLoaded', function() { loadTasks(1); });
