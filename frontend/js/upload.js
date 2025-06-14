// upload.js
console.log('upload.js cargado');

const csvInput   = document.getElementById('csvFileInput');
const uploadBtn  = document.getElementById('uploadBtn');
const statusP    = document.getElementById('uploadStatus');

// Habilita el botón cuando seleccionas un archivo
csvInput.addEventListener('change', () => {
  uploadBtn.disabled = !csvInput.files.length;
  statusP.textContent = '';
});

uploadBtn.addEventListener('click', async () => {
  if (!csvInput.files.length) return;
  
  // 1) Subir CSV
  statusP.textContent = 'Subiendo CSV…';
  const file = csvInput.files[0];
  const form = new FormData();
  form.append('file', file);

  let resp;
  try {
    resp = await fetch('/upload_csv', { method: 'POST', body: form });
  } catch (err) {
    console.error('Error al conectar con /upload_csv', err);
    statusP.textContent = 'Error de red al subir CSV';
    return;
  }

  if (!resp.ok) {
    const err = await resp.json().catch(() => ({}));
    statusP.textContent = err.detail || `Error al subir CSV (${resp.status})`;
    return;
  }

  statusP.textContent = 'CSV subido correctamente.';
  document.dispatchEvent(new Event('csvUploaded'));

  // 2) Entrenar modelos
  statusP.textContent = 'Entrenando modelos… (esto puede tardar unos segundos)';
  try {
    const trainResp = await fetch('/train_xgb', { method: 'POST' });
    if (!trainResp.ok) {
      const err = await trainResp.json().catch(() => ({}));
      statusP.textContent = err.detail || `Error entrenando (${trainResp.status})`;
      return;
    }
    statusP.textContent = '✅ Modelos entrenados.';
    document.dispatchEvent(new Event('modelsTrained'));
  } catch (err) {
    console.error('Error al conectar con /train_xgb', err);
    statusP.textContent = 'Error de red al entrenar modelos';
  }
});
