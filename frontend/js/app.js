// app.js
console.log('Demo Sales Forecasting cargado');

document.addEventListener('DOMContentLoaded', () => {
  // 1) Carga dinámica de módulos: upload, metrics y dashboard
  const scripts = [
    '/static/js/upload.js',
    '/static/js/metrics.js',
    '/static/js/dashboard.js'
  ];

  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src   = src;
      s.async = false; // respetar orden
      s.onload  = () => {
        console.log(`Módulo cargado: ${src}`);
        resolve();
      };
      s.onerror = () => reject(new Error(`Error cargando ${src}`));
      document.body.appendChild(s);
    });
  }

  (async () => {
    try {
      for (const src of scripts) {
        await loadScript(src);
      }
      console.log('Todos los módulos frontend han sido cargados.');
      // 2) Una vez cargados, inicializamos la lógica de predicción
      await initPredictionForm();
    } catch (err) {
      console.error(err);
    }
  })();
});

async function initPredictionForm() {
  const form       = document.getElementById("prediction-form");
  const modelSel   = document.getElementById("model-select");
  const featuresCt = document.getElementById("features-container");
  const resultDiv  = document.getElementById("prediction-result");
  const errorDiv   = document.getElementById("prediction-error");

  if (!form) {
    console.warn("No encontré #prediction-form en el DOM");
    return;
  }

  // 1) Obtener configuración de features desde el backend
  let config;
  try {
    const res = await fetch("/predict/config");
    if (!res.ok) throw new Error(`Error al cargar config (${res.status})`);
    config = await res.json();
  } catch (err) {
    console.error("No pude cargar /predict/config:", err);
    errorDiv.textContent = "Error cargando configuración de predicción.";
    return;
  }

  // 2) Función para renderizar los inputs según el modelo seleccionado
  function renderFields(model) {
    featuresCt.innerHTML = "";
    const featList = config[model] || [];
    featList.forEach((name, i) => {
      const row = document.createElement("div");
      row.className = "form-row";
      row.innerHTML = `
        <label for="f${i}">${name}:</label>
        <input
          type="number"
          id="f${i}"
          name="f${i}"
          step="any"
          required
        />
      `;
      featuresCt.appendChild(row);
    });
  }

  // 3) Al cambiar el selector de modelo, re-renderizar
  modelSel.addEventListener("change", () => renderFields(modelSel.value));

  // 4) Render inicial
  renderFields(modelSel.value);

  // 5) Capturar el envío del formulario
  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    resultDiv.textContent = "Calculando…";
    errorDiv.textContent  = "";

    // Recoger valores de todos los inputs
    let values;
    try {
      values = Array.from(featuresCt.querySelectorAll("input")).map(inp => {
        const v = parseFloat(inp.value);
        if (isNaN(v)) throw new Error(`Valor inválido en ${inp.id}`);
        return v;
      });
    } catch (err) {
      errorDiv.textContent  = err.message;
      resultDiv.textContent = "";
      return;
    }

    // Enviar al endpoint correcto
    try {
      const resp = await fetch(`/predict/${modelSel.value}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ features: values })
      });
      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${resp.status}`);
      }
      const { prediction } = await resp.json();
      resultDiv.textContent = `Predicción ${modelSel.value.toUpperCase()}: ${prediction.toFixed(2)}`;
    } catch (err) {
      errorDiv.textContent  = err.message;
      resultDiv.textContent = "";
      console.error(err);
    }
  });
}

