// app.js
// Archivo principal que orquesta la carga de los módulos frontend.
// Se ejecuta una sola vez al cargar la página y se encarga de inyectar
// dinámicamente upload.js, metrics.js y dashboard.js.
// Así, si en el futuro quieres añadir o quitar módulos, basta
// con ajustar esta lista.

console.log('Demo Sales Forecasting cargado');

document.addEventListener('DOMContentLoaded', () => {
  const scripts = [
    '/static/js/upload.js',
    '/static/js/metrics.js',
    '/static/js/dashboard.js'
  ];

  // Función para cargar un <script> dinámicamente
  function loadScript(src) {
    return new Promise((resolve, reject) => {
      const s = document.createElement('script');
      s.src = src;
      s.async = false;       // respetar orden
      s.onload = () => {
        console.log(`Módulo cargado: ${src}`);
        resolve();
      };
      s.onerror = () => reject(new Error(`Error cargando ${src}`));
      document.body.appendChild(s);
    });
  }

  // Cargar todos los scripts en secuencia
  (async () => {
    try {
      for (const src of scripts) {
        await loadScript(src);
      }
      console.log('Todos los módulos frontend han sido cargados.');
    } catch (err) {
      console.error(err);
    }
document.addEventListener("DOMContentLoaded", () => {
  const form       = document.getElementById("prediction-form");
  const modelSel   = document.getElementById("model-select");
  const featuresCt = document.getElementById("features-container");
  const resultDiv  = document.getElementById("prediction-result");
  const errorDiv   = document.getElementById("prediction-error");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    resultDiv.textContent = "Calculando…";
    errorDiv.textContent  = "";

    // Recogemos todas las entradas numéricas
    const inputs = featuresCt.querySelectorAll("input[type=number]");
    let features;
    try {
      features = Array.from(inputs).map((inp) => {
        const v = parseFloat(inp.value);
        if (isNaN(v)) throw new Error(`Valor inválido en ${inp.name}`);
        return v;
      });
    } catch (err) {
      errorDiv.textContent = err.message;
      resultDiv.textContent = "";
      return;
    }

    const modelo = modelSel.value; // "profit" o "quantity"

    try {
      const resp = await fetch(`/predict/${modelo}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ features })
      });

      if (!resp.ok) {
        const err = await resp.json();
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
});
