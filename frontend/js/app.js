// app.js
console.log('Demo Sales Forecasting cargado');

document.addEventListener('DOMContentLoaded', () => {
  // 1) Carga dinámica de módulo upload, metrics y dashboard
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
      // 2) Una vez cargados, instalamos el handler de predicción
      initPredictionForm();
    } catch (err) {
      console.error(err);
    }
  })();
});

// Función que instala el listener sobre el form de predicción
function initPredictionForm() {
  const form       = document.getElementById("prediction-form");
  const modelSel   = document.getElementById("model-select");
  const featuresCt = document.getElementById("features-container");
  const resultDiv  = document.getElementById("prediction-result");
  const errorDiv   = document.getElementById("prediction-error");

  if (!form) {
    console.warn("No encontré #prediction-form en el DOM");
    return;
  }

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    resultDiv.textContent = "Calculando…";
    errorDiv.textContent  = "";

    // 1) Extraer features
    const inputs = featuresCt.querySelectorAll("input[type=number]");
    let features;
    try {
      features = Array.from(inputs).map((inp) => {
        const v = parseFloat(inp.value);
        if (isNaN(v)) throw new Error(`Valor inválido en ${inp.name}`);
        return v;
      });
    } catch (err) {
      errorDiv.textContent  = err.message;
      resultDiv.textContent = "";
      return;
    }

    // 2) Elegir endpoint
    const modelo = modelSel.value; // "profit" o "quantity"

    // 3) Llamada al backend
    try {
      const resp = await fetch(`/predict/${modelo}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ features })
      });

      if (!resp.ok) {
        const err = await resp.json().catch(() => ({}));
        throw new Error(err.detail || `Error ${resp.status}`);
      }

      const { prediction } = await resp.json();
      resultDiv.textContent = `Predicción ${modelo.toUpperCase()}: ${prediction.toFixed(2)}`;
    } catch (err) {
      errorDiv.textContent  = err.message;
      resultDiv.textContent = "";
      console.error(err);
    }
  });
}

