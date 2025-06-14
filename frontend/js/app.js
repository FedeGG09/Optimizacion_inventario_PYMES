// app.js
console.log('Demo Sales Forecasting cargado');

document.addEventListener('DOMContentLoaded', async () => {
  // Carga dinámica de módulos upload, metrics y dashboard
  const modules = [
    '/static/js/upload.js',
    '/static/js/metrics.js',
    '/static/js/dashboard.js'
  ];
  for (let m of modules) {
    await new Promise((res, rej) => {
      const s = document.createElement('script');
      s.src = m;
      s.async = false;
      s.onload = res;
      s.onerror = () => rej();
      document.body.appendChild(s);
    });
  }
  console.log('Módulos frontend cargados.');
  // upload.js disparará csvUploaded y luego modelsTrained
});

async function initPredictionByFields() {
  const regionSel  = document.getElementById('pred-region');
  const productSel = document.getElementById('pred-product');
  const dateInput  = document.getElementById('pred-date');
  const form       = document.getElementById('prediction-form');
  const resDiv     = document.getElementById('prediction-result');
  const errDiv     = document.getElementById('prediction-error');

  // Limpiar mensajes previos
  resDiv.textContent = '';
  errDiv.textContent  = '';

  // Cargar metadatos de regiones y productos
  try {
    const [regs, prods] = await Promise.all([
      fetch('/metadata/regions').then(r => r.ok ? r.json() : Promise.reject()),
      fetch('/metadata/products').then(r => r.ok ? r.json() : Promise.reject())
    ]);
    regionSel.innerHTML  =
      `<option value="">Seleccione región</option>` +
      regs.map(r => `<option value="${r}">${r}</option>`).join('');
    productSel.innerHTML =
      `<option value="">Seleccione producto</option>` +
      prods.map(p => `<option value="${p}">${p}</option>`).join('');
  } catch {
    console.warn('No se pudo cargar metadata para predicción');
    errDiv.textContent = 'Error cargando opciones de predicción';
    return;
  }

  // Capturar submit del formulario
  form.addEventListener('submit', async e => {
    e.preventDefault();
    resDiv.textContent = 'Calculando…';
    errDiv.textContent  = '';

    const payload = {
      region:  regionSel.value,
      product: productSel.value,
      date:    dateInput.value
    };

    try {
      const resp = await fetch('/predict', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
      });
      const body = await resp.json();
      if (!resp.ok) throw new Error(body.detail || `Error ${resp.status}`);

      resDiv.innerHTML = `
        • Cantidad predicha: ${body.quantity.toFixed(2)}<br>
        • Ganancia predicha: $${body.profit.toFixed(2)}
      `;
    } catch (err) {
      console.error('Error /predict:', err);
      errDiv.textContent = err.message || 'Error al predecir';
      resDiv.textContent = '';
    }
  });
}

// Listener para mostrar dashboard y arrancar predicción tras entrenar
document.addEventListener('modelsTrained', () => {
  const actions = document.getElementById('actions');
  if (actions) actions.style.display = '';
  if (window.initPredictionByFields) {
    window.initPredictionByFields();
  }
});

// Exponer globalmente
window.initPredictionByFields = initPredictionByFields;
