# ml_utils.py

import pandas as pd
from rapidfuzz import process, fuzz
from nltk.corpus import wordnet as wn
from rapidfuzz import process, fuzz
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import FunctionTransformer, OneHotEncoder, StandardScaler
from sklearn.compose import ColumnTransformer
import xgboost as xgb

STANDARD_COLUMNS = ["date", "region", "product", "quantity", "profit"]

def normalize_columns(df: pd.DataFrame, threshold: int = 80) -> pd.DataFrame:
    """Fuzzy‑match + WordNet para renombrar columnas al estándar."""
    orig = list(df.columns)
    mapping = {}
    for std in STANDARD_COLUMNS:
        match, score, _ = process.extractOne(std, orig, scorer=fuzz.token_sort_ratio)
        if score >= threshold:
            mapping[match] = std
            continue
        for col in orig:
            synsets = wn.synsets(col, lang='eng') or wn.synsets(col)
            lemmas = {
                lemma.lower().replace('_',' ')
                for s in synsets for lemma in s.lemma_names()
            }
            if std in lemmas:
                mapping[col] = std
                break
    return df.rename(columns=mapping)

def extract_date_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extrae year, month y year_month de df['date'] (datetime)."""
    ds = df["date"]
    return pd.DataFrame({
        "year": ds.dt.year,
        "month": ds.dt.month,
        "year_month": ds.dt.year.astype(str) + "_" + ds.dt.month.astype(str),
    })

def get_preprocessor() -> ColumnTransformer:
    date_pipe = Pipeline([
        ("extract", FunctionTransformer(extract_date_features, validate=False)),
        ("ohe",     OneHotEncoder(handle_unknown="ignore", sparse_output=False))
    ])
    region_pipe = Pipeline([("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    product_pipe= Pipeline([("ohe", OneHotEncoder(handle_unknown="ignore", sparse_output=False))])
    return ColumnTransformer([
        ("date",    date_pipe,    ["date"]),
        ("region",  region_pipe,  ["region"]),
        ("product", product_pipe, ["product"]),
    ], remainder="drop")

def build_xgb_pipeline(model_params: dict) -> Pipeline:
    """
    Construye un pipeline completo con preprocessing y XGBRegressor.
    """

    return Pipeline([
        ("preproc",  get_preprocessor()),
        ("scale",    StandardScaler(with_mean=False)),
        ("model",    xgb.XGBRegressor(**model_params))
    ])