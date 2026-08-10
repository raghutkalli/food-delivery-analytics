"""Loads the 6 project tables live from the MySQL / phpMyAdmin database."""
import polars as pl

TABLE_MAP = {
    "users":             "users_tbl",
    "restaurants":       "restaurants_tbl",
    "delivery_partners": "delivery_partners_tbl",
    "orders":            "orders_tbl",
    "app_events":        "event_id_tbl",
    "nps_responses":     "nps_responses_tbl",
}


def load_from_database(host: str, port: int, database: str, user: str, password: str, table_map: dict = None):
    """Connects via SQLAlchemy + PyMySQL and pulls all 6 tables as Polars DataFrames.

    Raises on any connection/query failure — caller is expected to catch and fall back.
    """
    from sqlalchemy import create_engine

    table_map = table_map or TABLE_MAP
    conn_str = f"mysql+pymysql://{user}:{password}@{host}:{port}/{database}"
    engine = create_engine(conn_str, connect_args={"connect_timeout": 8})

    frames = {}
    with engine.connect() as conn:
        for key, table in table_map.items():
            frames[key] = pl.read_database(query=f"SELECT * FROM {table}", connection=conn)

    return (frames["users"], frames["restaurants"], frames["delivery_partners"],
            frames["orders"], frames["app_events"], frames["nps_responses"])


def ensure_bool(df: pl.DataFrame, cols: list) -> pl.DataFrame:
    """MySQL often returns TINYINT(1) 0/1 for boolean columns — cast them properly."""
    exprs = [
        pl.col(c).cast(pl.Int64, strict=False).cast(pl.Boolean).alias(c)
        for c in cols if c in df.columns and df.schema[c] != pl.Boolean
    ]
    return df.with_columns(exprs) if exprs else df
