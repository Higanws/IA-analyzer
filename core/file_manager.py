import os
import pandas as pd

def guardar_csv(df: pd.DataFrame, path_csv: str):
    os.makedirs(os.path.dirname(path_csv), exist_ok=True)
    df.to_csv(path_csv, index=False, encoding="utf-8")
