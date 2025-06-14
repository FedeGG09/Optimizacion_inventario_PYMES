import io
import joblib
import pandas as pd
from pathlib import Path
from datetime import datetime
import sys, os
import uvicorn


from fastapi import FastAPI, File, UploadFile, HTTPException, Query
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from backend.ml_utils import normalize_columns
from backend.train_xgb import train_and_save
BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))
# -------------------------------------------------------
# Configuración de la app
# -------------------------------------------------------
app = FastAPI(title="Sales Forecasting API", version="1.0")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

BASE_DIR      = Path(__file__).parent
PROJECT_DIR   = BASE_DIR.parent
MODELS_DIR    = BASE_DIR / "models"
TRAIN_CSV     = PROJECT_DIR / "stores_sales_forecasting.csv"
PIPE_QTY      = MODELS_DIR / "pipeline_quantity.pkl"
PIPE_PROF     = MODELS_DIR / "pipeline_profit.pkl"

pipe_q = pipe_p = None
uploaded_csv_path: Path | None = None

# Montar frontend estático
FRONTEND_DIR = PROJECT_DIR / "frontend"
app.mount("/static/css", StaticFiles(directory=FRONTEND_DIR / "css"), name="css")
app.mount("/static/js",  StaticFiles(directory=FRONTEND_DIR / "js"),  name="js")

@app.get("/")
def serve_index():
    index_file = FRONTEND_DIR / "src" / "index.html"
    if not index_file.exists():
        raise HTTPException(404, "index.html no encontrado")
    return FileResponse(str(index_file))

# -------------------------------------------------------
# Startup: intentar cargar pipelines sin romper si no existen
# -------------------------------------------------------
@app.on_event("startup")
def load_pipelines():
    global pipe_q, pipe_p
    MODELS_DIR.mkdir(exist_ok=True)
    if PIPE_QTY.exists() and PIPE_PROF.exists():
        pipe_q = joblib.load(PIPE_QTY)
        pipe_p = joblib.load(PIPE_PROF)
        print("▶️ Pipelines cargados.")
    else:
        pipe_q = pipe_p = None
        print("⚠️ Pipelines no encontrados. Usa /upload_csv + /train_xgb.")

# -------------------------------------------------------
# Auxiliar: carga del DataFrame de entrenamiento
# -------------------------------------------------------
def _get_df() -> pd.DataFrame:
    path = uploaded_csv_path or TRAIN_CSV
    if not path or not path.exists():
        raise HTTPException(400, "No hay CSV de entrenamiento disponible.")
    df = pd.read_csv(path, encoding="latin1")
    return df

# -------------------------------------------------------
# ENDPOINT: upload_csv
# -------------------------------------------------------
@app.post("/upload_csv")
def upload_training_csv(file: UploadFile = File(...)):
    global uploaded_csv_path
    try:
        data = file.file.read()
        target = PROJECT_DIR / "stores_sales_forecasting.csv"
        target.write_bytes(data)
        uploaded_csv_path = target
        return {"detail": f"CSV guardado como {target.name}"}
    except Exception as e:
        raise HTTPException(500, str(e))

# -------------------------------------------------------
# ENDPOINT: train_xgb
# -------------------------------------------------------
@app.post("/train_xgb")
def retrain():
    csv_path = uploaded_csv_path or TRAIN_CSV
    if not csv_path.exists():
        raise HTTPException(400, f"No hay CSV en {csv_path}. Usa /upload_csv primero.")
    try:
        train_and_save(str(csv_path), str(MODELS_DIR))
        load_pipelines()
        return {"detail": "Retraining completado."}
    except Exception as e:
        raise HTTPException(500, str(e))

# -------------------------------------------------------
# ENDPOINT: predict_csv (batch)
# -------------------------------------------------------
@app.post("/predict_csv")
def predict_csv(file: UploadFile = File(...)):
    if pipe_q is None or pipe_p is None:
        raise HTTPException(400, "Modelos no entrenados. Usa /upload_csv + /train_xgb.")
    try:
        raw = file.file.read()
        df = pd.read_csv(io.BytesIO(raw), encoding="latin1", parse_dates=["Order Date"])
        df = df.rename(columns={"Order Date": "date",
                                "Region": "region",
                                "Product Name": "product"}, errors="ignore")
        df = normalize_columns(df)
        df["date"] = pd.to_datetime(df["date"], errors="coerce")
        X = df[["date", "region", "product"]]
        return JSONResponse({
            "quantity": pipe_q.predict(X).tolist(),
            "profit":   pipe_p.predict(X).tolist()
        })
    except Exception as e:
        raise HTTPException(400, str(e))

# -------------------------------------------------------
# ENDPOINT: predict (JSON)
# -------------------------------------------------------
@app.post("/predict")
def predict_json(payload: dict):
    if pipe_q is None or pipe_p is None:
        raise HTTPException(400, "Modelos no entrenados. Usa /upload_csv + /train_xgb.")
    # Validación simplificada
    for k in ("region", "product", "date"):
        if k not in payload:
            raise HTTPException(422, f"Falta campo '{k}' en el JSON.")
    try:
        dt = datetime.strptime(payload["date"], "%Y-%m-%d")
    except:
        raise HTTPException(422, "Formato de 'date' inválido. Debe ser YYYY-MM-DD.")
    df = pd.DataFrame([{
        "date":    dt,
        "region":  payload["region"],
        "product": payload["product"]
    }])
    df = normalize_columns(df)
    qty  = pipe_q.predict(df)[0]
    prof = pipe_p.predict(df)[0]
    return {"quantity": float(qty), "profit": float(prof)}

# -------------------------------------------------------
# ENDPOINT: metrics_xgb
# -------------------------------------------------------
@app.get("/metrics_xgb")
def metrics_xgb_endpoint():
    try:
        df = _get_df()
        from model_utils import evaluate_model
        metrics = evaluate_model(df)
        return JSONResponse({"metrics": metrics})
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(500, str(e))

# -------------------------------------------------------
# ENDPOINT: metadata/regions & metadata/products
# -------------------------------------------------------
@app.get("/metadata/regions")
def metadata_regions():
    df = _get_df()
    # 1) renombrar a nombres “pythonic”
    df = df.rename(columns={
        "Order Date": "date",
        "Region":     "region",
        "Product Name": "product"
    }, errors="ignore")
    # 2) normalizar (lowercase, quitar espacios, etc)
    df = normalize_columns(df)
    # 3) ahora sí, existe df["region"]
    if "region" not in df.columns:
        raise HTTPException(500, "No se encontró columna 'region'")
    regions = sorted(df["region"].dropna().unique().tolist())
    return JSONResponse(regions)


@app.get("/metadata/products")
def metadata_products():
    df = _get_df()
    # 1) mismo renaming
    df = df.rename(columns={
        "Order Date": "date",
        "Region":     "region",
        "Product Name": "product"
    }, errors="ignore")
    # 2) luego normalizar
    df = normalize_columns(df)
    if "product" not in df.columns:
        raise HTTPException(500, "No se encontró columna 'product'")
    prods = sorted(df["product"].dropna().unique().tolist())
    return JSONResponse(prods)

# -------------------------------------------------------
# ENDPOINT: kpis, grouped, sales_trend (sin cambios)
# -------------------------------------------------------
@app.get("/kpis")
def get_kpis(
    month:   str  = Query(None),
    vendor:  str  = Query("Todos"),
    product: str  = Query("Todos")
):
    df = _get_df()
    if "Order Date" in df.columns:
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    if month:
        df = df[df["Order Date"].dt.to_period("M") == pd.Period(month, "M")]
    if vendor!="Todos":
        df = df[df["Customer Name"] == vendor]
    if product!="Todos":
        df = df[df["Product Name"] == product]
    for col in ["Sales","Profit"]:
        if col not in df.columns:
            raise HTTPException(500, f"Falta columna '{col}'")
    return {
        "total_sales":    float(df["Sales"].sum()),
        "avg_profit_pct": float((df["Profit"]/df["Sales"]).mean()),
        "sale_count":     int(df.shape[0]),
        "avg_sales":      float(df["Sales"].mean())
    }

@app.get("/grouped")
def get_grouped_data(
    field:   str  = Query(...),
    month:   str  = Query(None),
    vendor:  str  = Query("Todos"),
    product: str  = Query("Todos")
):
    df = _get_df()
    if "Order Date" in df.columns:
        df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    if month:
        df = df[df["Order Date"].dt.to_period("M") == pd.Period(month, "M")]
    if vendor!="Todos":
        df = df[df["Customer Name"] == vendor]
    if product!="Todos":
        df = df[df["Product Name"] == product]
    if field not in df.columns:
        raise HTTPException(400, f"Campo '{field}' no existe")
    for c in ["Sales","Quantity","Discount","Profit"]:
        if c not in df.columns:
            raise HTTPException(500, f"Falta columna '{c}'")
    grouped = (
        df.groupby(field, dropna=False)
          .agg(
            total_sales    = pd.NamedAgg("Sales","sum"),
            total_quantity = pd.NamedAgg("Quantity","sum"),
            avg_discount   = pd.NamedAgg("Discount","mean"),
            total_profit   = pd.NamedAgg("Profit","sum")
          )
          .reset_index()
          .rename(columns={field:"group"})
          .sort_values("total_sales", ascending=False)
    )
    return {"data": [
        {
          "group":           row["group"],
          "total_sales":     float(row["total_sales"]),
          "total_quantity":  int(row["total_quantity"]),
          "avg_discount":    float(row["avg_discount"]),
          "total_profit":    float(row["total_profit"])
        }
        for _, row in grouped.iterrows()
    ]}

@app.get("/sales_trend")
def sales_trend(
    year:   int  = Query(2020),
    month:  str  = Query(None),
    vendor: str  = Query("Todos")
):
    df = _get_df()
    if "Order Date" not in df.columns:
        raise HTTPException(500, "Falta 'Order Date'")
    df["Order Date"] = pd.to_datetime(df["Order Date"], errors="coerce")
    df = df[df["Order Date"].dt.year == year]

    # Ventas por día en un mes específico
    if month:
        try:
            periodo = pd.Period(month, "M")
        except:
            raise HTTPException(400, "Formato de month inválido")
        df = df[df["Order Date"].dt.to_period("M") == periodo]
        if vendor!="Todos":
            df = df[df["Customer Name"] == vendor]
        df["Day"] = df["Order Date"].dt.day
        pivot = (df.groupby(["Customer Name","Day"])["Sales"]
                   .sum().unstack(fill_value=0)
                   .reindex(range(1, periodo.days_in_month+1), fill_value=0)
                )
        labels = [f"{month}-{d:02d}" for d in pivot.index]
        return {"labels": labels, "datasets": [
            {"vendor": c, "values": pivot[c].tolist()} for c in pivot.columns
        ]}

    # Ventas mes a mes
    if vendor!="Todos":
        df = df[df["Customer Name"] == vendor]
    if "Sales" not in df.columns:
        raise HTTPException(500, "Falta 'Sales'")
    df["YearMonth"] = df["Order Date"].dt.to_period("M").astype(str)
    pivot = (df.groupby(["Customer Name","YearMonth"])["Sales"]
               .sum().unstack(fill_value=0)
               .reindex([f"{year}-{m:02d}" for m in range(1,13)], fill_value=0)
            )
    return {"labels": pivot.index.tolist(), "datasets": [
        {"vendor": c, "values": pivot[c].tolist()} for c in pivot.columns
    ]}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("backend.main:app", host="0.0.0.0", port=port)
