import os
import pandas as pd

def guardar_csv(df: pd.DataFrame, path_csv: str):
    d = os.path.dirname(path_csv)
    if d:
        os.makedirs(d, exist_ok=True)
    df.to_csv(path_csv, index=False, encoding="utf-8")
