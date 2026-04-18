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
      cell.colSpan = 8;
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

      var tdCallback = tr.insertCell();
      if (task.callback_url) {
        var cbLink = document.createElement('a');
        cbLink.href = task.callback_url;
        cbLink.textContent = task.callback_url.length > 30 ? task.callback_url.substring(0, 30) + '...' : task.callback_url;
        cbLink.title = task.callback_url;
        cbLink.target = '_blank';
        tdCallback.appendChild(cbLink);
      } else {
        tdCallback.textContent = '-';
      }

      var tdActions = tr.insertCell();
      var group = document.createElement('div');
      group.className = 'btn-group';

      var triggerBtn = document.createElement('button');
      triggerBtn.className = 'btn btn-sm btn-primary';
      triggerBtn.innerHTML = '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="5 3 19 12 5 21 5 3"/></svg> Trigger';
      triggerBtn.onclick = (function(tid, tname) {
        return function() { triggerTaskAction(tid, tname); };
      })(task.id, task.name);
      group.appendChild(triggerBtn);

      var toggleBtn = document.createElement('button');
      toggleBtn.className = 'btn btn-sm';
      toggleBtn.innerHTML = task.enabled
        ? '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><line x1="4.93" y1="4.93" x2="19.07" y2="19.07"/></svg> Disable'
        : '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M22 11.08V12a10 10 0 11-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg> Enable';
      toggleBtn.onclick = (function(tid, isEnabled) {
        return function() { toggleTaskAction(tid, isEnabled); };
      })(task.id, task.enabled);
      group.appendChild(toggleBtn);

      var delBtn = document.createElement('button');
      delBtn.className = 'btn btn-sm btn-danger';
      delBtn.innerHTML = '<svg class="btn-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 01-2 2H7a2 2 0 01-2-2V6m3 0V4a2 2 0 012-2h4a2 2 0 012 2v2"/></svg> Delete';
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
    cell.colSpan = 8;
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
