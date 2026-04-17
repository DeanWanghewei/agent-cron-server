var currentPage = 1;

async function loadExecutions(page) {
  page = page || 1;
  currentPage = page;
  var status = document.getElementById('filter-status').value;
  var params = { page: page, page_size: 20 };
  if (status) params.status = status;

  try {
    var data = await api.listExecutions(params);
    var tbody = document.getElementById('exec-table');
    tbody.innerHTML = '';

    if (!data.items || data.items.length === 0) {
      var row = tbody.insertRow();
      var cell = row.insertCell();
      cell.colSpan = 8;
      cell.textContent = 'No executions found';
      cell.className = 'empty-state';
      return;
    }

    data.items.forEach(function(r) {
      var tr = tbody.insertRow();
      tr.insertCell().textContent = r.id;

      var tdTask = tr.insertCell();
      var a = document.createElement('a');
      a.href = 'task-detail.html?id=' + r.task_id;
      a.textContent = r.task_name;
      tdTask.appendChild(a);

      tr.insertCell().appendChild(makeStatusBadge(r.status));
      var tdTrigger = tr.insertCell();
      var tb = document.createElement('span');
      tb.className = 'badge ' + (r.trigger_type === 'manual' ? 'badge-primary' : 'badge-info');
      tb.textContent = r.trigger_type;
      tdTrigger.appendChild(tb);
      tr.insertCell().textContent = formatDuration(r.duration_ms);
      tr.insertCell().textContent = r.exit_code != null ? r.exit_code : '-';
      tr.insertCell().textContent = formatTime(r.started_at);

      var tdActions = tr.insertCell();
      var viewBtn = document.createElement('a');
      viewBtn.href = 'execution-detail.html?id=' + r.id;
      viewBtn.className = 'btn btn-sm';
      viewBtn.textContent = 'Log';
      tdActions.appendChild(viewBtn);
    });

    var pagDiv = document.getElementById('pagination');
    pagDiv.innerHTML = '';
    var pagEl = makePagination(page, 20, data.total);
    if (pagEl) pagDiv.appendChild(pagEl);
  } catch (e) {
    document.getElementById('exec-table').innerHTML = '';
    var row = document.getElementById('exec-table').insertRow();
    var cell = row.insertCell();
    cell.colSpan = 8;
    cell.textContent = 'Failed to load executions';
    cell.className = 'empty-state';
  }
}

function goPage(p) { loadExecutions(p); }

document.addEventListener('DOMContentLoaded', function() { loadExecutions(1); });
