var executionId = null;

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

async function loadData() {
  var params = new URLSearchParams(window.location.search);
  executionId = parseInt(params.get('id'));
  if (!executionId) return;

  var record = await api.getExecution(executionId);
  if (!record) {
    document.getElementById('page-title').textContent = 'Execution not found';
    return;
  }

  document.title = 'Execution #' + executionId + ' - Agent Cron Server';
  document.getElementById('page-title').textContent = 'Execution #' + executionId;

  var grid = document.getElementById('exec-info');
  grid.innerHTML = '';
  grid.appendChild(infoItem('ID', record.id));
  grid.appendChild(infoItem('Task', record.task_name + ' (ID: ' + record.task_id + ')'));

  var statusDiv = document.createElement('div');
  statusDiv.className = 'info-item';
  var statusLabel = document.createElement('div');
  statusLabel.className = 'info-label';
  statusLabel.textContent = 'STATUS';
  var statusVal = document.createElement('div');
  statusVal.className = 'info-value';
  statusVal.appendChild(makeStatusBadge(record.status));
  statusDiv.appendChild(statusLabel);
  statusDiv.appendChild(statusVal);
  grid.appendChild(statusDiv);

  grid.appendChild(infoItem('Trigger', record.trigger_type));
  grid.appendChild(infoItem('Started', formatTime(record.started_at)));
  grid.appendChild(infoItem('Finished', formatTime(record.finished_at)));
  grid.appendChild(infoItem('Duration', formatDuration(record.duration_ms)));
  grid.appendChild(infoItem('Exit Code', record.exit_code != null ? record.exit_code : '-'));
  grid.appendChild(infoItem('Error', record.error_message));

  var log = await api.getExecutionLog(executionId);
  if (log) {
    document.getElementById('log-card').style.display = '';
    document.getElementById('log-stdout').textContent = log.stdout || '';
    document.getElementById('log-stderr').textContent = log.stderr || '';
  }
}

document.addEventListener('DOMContentLoaded', loadData);
