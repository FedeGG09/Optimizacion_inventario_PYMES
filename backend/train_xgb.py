# backend/train_xgb.py

import pandas as pd, joblib
from pathlib import Path
from backend.ml_utils import normalize_columns, build_xgb_pipeline

def train_and_save(data_path, out_dir):
    out_path = Path(out_dir); out_path.mkdir(exist_ok=True, parents=True)
    df = pd.read_csv(data_path, parse_dates=["Order Date"], encoding="latin1")
    df = df.rename(columns={"Order Date":"date","Region":"region",
                            "Product Name":"product","Quantity":"quantity","Profit":"profit"})
    df = normalize_columns(df)
    X = df[["date","region","product"]]
    pipe_q = build_xgb_pipeline({})
    pipe_p = build_xgb_pipeline({})
    pipe_q.fit(X, df["quantity"])
    pipe_p.fit(X, df["profit"])
    joblib.dump(pipe_q, out_path/"pipeline_quantity.pkl")
    joblib.dump(pipe_p, out_path/"pipeline_profit.pkl")
    print("✅ Pipelines guardados en", out_path)

if __name__=="__main__":
    import argparse
    p=argparse.ArgumentParser()
    p.add_argument("--data", default="stores_sales_forecasting.csv")
    p.add_argument("--outdir", default="backend/models")
    args=p.parse_args()
    train_and_save(args.data, args.outdir)
