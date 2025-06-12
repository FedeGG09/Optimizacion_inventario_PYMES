import pandas as pd
from pathlib import Path
from datetime import datetime
from backend.main import load_profit_features, load_quantity_features

# Ajusta esta ruta si tu CSV se guarda en otro sitio
TRAIN_CSV = Path(__file__).parent.parent / "stores_sales_forecasting.csv"

def build_features(region: str,
                   product_id: str,
                   sub_category: str,
                   order_date: str,
                   model_type: str = "profit") -> pd.DataFrame:
    """
    1) Carga el CSV de entrenamiento con todas las ventas.
    2) A partir de los inputs sencillos construye:
       - Estadísticos por región (Profit_Region_Mean, _Min, _Max).
       - Count y estadísticos de Sub-Category.
       - Estadísticos de Product ID (Quantity y Profit).
       - Fechas: mes, día de la semana, etc.
       - Dummies de Region, Sub-Category, Product ID, etc.
    3) Alinea columnas al orden de tu modelo (995 features).
    """

    # 1) Leer CSV
    df_all = pd.read_csv(TRAIN_CSV, encoding="latin1")
    
    # 2) Parsear fecha
    od = pd.to_datetime(order_date)
    
    # 3) Empezar un dict con tus valores base
    base = {
        "Order Date": od,
        "Region":      region,
        "Product ID":  product_id,
        "Sub-Category": sub_category,
        # añade aquí otros campos sencillos si quieres
    }
    
    # 4) Variables de fecha
    base["Month"]     = od.month
    base["DayOfWeek"] = od.weekday()
    
    # 5) Estadísticos por región (ejemplo)
    reg_stats = (
        df_all.groupby("Region")["Profit"]
              .agg(["mean","min","max"])
              .rename(columns={
                  "mean":"Profit_Region_Mean",
                  "min": "Profit_Region_Min",
                  "max": "Profit_Region_Max"
              })
    )
    if region in reg_stats.index:
        for c in reg_stats.columns:
            base[c] = reg_stats.loc[region, c]
    else:
        for c in reg_stats.columns:
            base[c] = 0.0
    
    # 6) Count y media de Sub-Category (ejemplo)
    sub_stats = (
        df_all.groupby("Sub-Category")["Profit"]
              .agg(["count","mean"])
              .rename(columns={
                  "count":"Sub-Category_Count",
                  "mean": "Profit_Sub-Category_Mean"
              })
    )
    if sub_category in sub_stats.index:
        for c in sub_stats.columns:
            base[c] = sub_stats.loc[sub_category, c]
    else:
        for c in sub_stats.columns:
            base[c] = 0.0
    
    # 7) Estadísticos de Product ID (ejemplo Quantity)
    prod_qty = (
        df_all.groupby("Product ID")["Quantity"]
              .agg(["mean","std","median","max"])
              .rename(columns={
                  "mean":"Quantity_ProductID_Mean",
                  "std": "Quantity_ProductID_Std",
                  "median":"Quantity_ProductID_Median",
                  "max":"Quantity_ProductID_Max"
              })
    )
    if product_id in prod_qty.index:
        for c in prod_qty.columns:
            base[c] = prod_qty.loc[product_id, c]
    else:
        for c in prod_qty.columns:
            base[c] = 0.0

    # 8) Ahora montamos el DataFrame de 1 fila
    df_feat = pd.DataFrame([base])

    # 9) Dummies (one-hot) de categorías
    df_feat = pd.get_dummies(df_feat, drop_first=True)

    # 10) Alinear columnas al modelo elegido
    if model_type == "profit":
        cols = load_profit_features()
    else:
        cols = load_quantity_features()

    df_aligned = df_feat.reindex(columns=cols, fill_value=0)
    return df_aligned
