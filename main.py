"""
================================================================================
THREATHUNTER M4 PRO - VERSION: 8.2.6 (Numeric Integrity Fix)
================================================================================
"""
from fastapi import FastAPI, UploadFile, File
from fastapi.staticfiles import StaticFiles
import duckdb
from typing import Optional, List
import os
import shutil
import json
import decimal
from datetime import datetime, date

app = FastAPI()
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
WEB_DIR = os.path.join(BASE_DIR, "web")
DATA_DIR = os.path.join(BASE_DIR, "data")

if not os.path.exists(DATA_DIR):
    os.makedirs(DATA_DIR)

def convert_csvs_to_parquets():
    if not os.path.exists(DATA_DIR): return
    csv_files = [f for f in os.listdir(DATA_DIR) if f.lower().endswith('.csv')]
    for f in csv_files:
        csv_path = os.path.join(DATA_DIR, f)
        parquet_path = os.path.join(DATA_DIR, f[:-4] + '.parquet')
        try:
            with duckdb.connect() as con:
                con.execute(f"COPY (SELECT * FROM read_csv_auto('{csv_path}')) TO '{parquet_path}' (FORMAT PARQUET)")
            os.remove(csv_path)
            print(f"✅ Đã chuyển đổi: {f} -> {f[:-4]}.parquet")
        except Exception as e:
            print(f"❌ Lỗi chuyển đổi {f}: {e}")

convert_csvs_to_parquets()

def get_from_clause(datasets_json: str = None):
    if not os.path.exists(DATA_DIR): return None
    all_parquets = [f for f in os.listdir(DATA_DIR) if f.endswith('.parquet')]
    if not all_parquets: return None
    
    target_files = all_parquets
    if datasets_json:
        try:
            selected = json.loads(datasets_json)
            valid_files = [f for f in selected if f in all_parquets]
            if valid_files: target_files = valid_files
            else: return None
        except: pass
        
    paths = ["'" + os.path.join(DATA_DIR, f).replace('\\', '/') + "'" for f in target_files]
    return f"read_parquet([{', '.join(paths)}], union_by_name=true, filename=true)"

def query_to_dict(sql, params=[]):
    """
    BẢN VÁ v8.2.6: Giữ nguyên định dạng Số (int, float), 
    chỉ ép kiểu String với Ngày tháng hoặc kiểu Decimal đặc biệt để tránh hỏng biểu đồ.
    """
    try: 
        with duckdb.connect() as con:
            cursor = con.execute(sql, params)
            cols = [x[0] for x in cursor.description]
            rows = cursor.fetchall()
            res = []
            for row in rows:
                row_dict = {}
                for i, val in enumerate(row):
                    if val is None or val == "":
                        row_dict[cols[i]] = "N/A"
                    elif isinstance(val, (int, float)):
                        row_dict[cols[i]] = val  # Giữ nguyên Số nguyên và Số thực
                    elif isinstance(val, decimal.Decimal):
                        row_dict[cols[i]] = float(val) # Ép Decimal thành Float an toàn
                    elif isinstance(val, (datetime, date)):
                        row_dict[cols[i]] = str(val) # Ép Ngày tháng thành String
                    else:
                        row_dict[cols[i]] = str(val)
                res.append(row_dict)
            return res
    except Exception as e: 
        print(f"SQL Error: {e}\nQuery: {sql}") 
        return []

def get_schema_cols(datasets_json: str = None):
    from_clause = get_from_clause(datasets_json)
    if not from_clause: return []
    try:
        with duckdb.connect() as con:
            res = con.execute(f"DESCRIBE SELECT * FROM {from_clause}").df()
            return [c for c in res['column_name'].tolist() if c != 'filename']
    except: return []

def get_time_col(cols: List[str]):
    for c in ["Generate Time", "Receive Time", "Time", "time", "timestamp", "Date", "Log Time"]:
        if c in cols:
            return f'"{c}"'
    return None

def build_where_clause(filters_json: str, q_search: str = None, start: str = None, end: str = None, cols: List[str] = []):
    conds, params = [], []
    if start and end:
        time_col = get_time_col(cols)
        if time_col:
            conds.append(f" ({time_col} BETWEEN ? AND ?)")
            params.extend([start.replace('T', ' '), end.replace('T', ' ')])
            
    if filters_json:
        try:
            for f in json.loads(filters_json):
                logic, col, op, val = f.get('logic','AND'), f.get('col'), f.get('op', '='), f.get('val')
                sql_op = "=" if op == '=' else ("!=" if op == '!=' else "ILIKE")
                actual_val = f"%{val}%" if sql_op == "ILIKE" else val
                conds.append(f" {logic} (\"{col}\" {sql_op} ?)")
                params.append(actual_val)
        except: pass
    where = "WHERE " + "".join(conds).lstrip(" AND").lstrip(" OR") if conds else ""
    if q_search:
        sc = "CONCAT_WS(' ', COLUMNS(*)) ILIKE ?"
        where = f"{where} AND ({sc})" if where else f"WHERE {sc}"
        params.append(f"%{q_search}%")
    return where, params

@app.get("/api/datasets")
def get_datasets():
    if not os.path.exists(DATA_DIR): return []
    return [f for f in os.listdir(DATA_DIR) if f.endswith('.parquet')]

@app.get("/api/columns")
def get_columns(datasets: Optional[str] = None):
    return get_schema_cols(datasets)

@app.get("/api/graph-edges")
def get_graph_edges(datasets: Optional[str] = None, filters: Optional[str] = None, start: str = None, end: str = None):
    from_clause = get_from_clause(datasets)
    if not from_clause: return []
    
    cols = get_schema_cols(datasets)
    where, params = build_where_clause(filters, None, start, end, cols)
    
    has_sent = "Bytes Sent" in cols
    weight_sql = 'COALESCE(ROUND(SUM(TRY_CAST("Bytes Sent" AS BIGINT))/1024, 2), 0)' if has_sent else 'COUNT(*)'
    having_sql = 'weight > 10' if has_sent else 'weight > 2'
    
    sql = f"""
        SELECT "Source address" as source, "Destination address" as target, 
               {weight_sql} as weight
        FROM {from_clause} {where}
        GROUP BY 1, 2 HAVING {having_sql} ORDER BY 3 DESC LIMIT 200
    """
    return query_to_dict(sql, params)

@app.get("/api/dynamic-stats")
def get_dynamic_stats(col: str, metric: str = "sessions", datasets: Optional[str] = None, filters: Optional[str] = None, start: str = None, end: str = None):
    from_clause = get_from_clause(datasets)
    if not from_clause: return []

    cols = get_schema_cols(datasets)
    byte_col = '"Bytes"' if "Bytes" in cols else '0'
    sent_col = '"Bytes Sent"' if "Bytes Sent" in cols else '0'
    recv_col = '"Bytes Received"' if "Bytes Received" in cols else '0'

    m_map = {
        "sessions": "COUNT(*)", 
        "bytes": f'COALESCE(ROUND(SUM(TRY_CAST({byte_col} AS BIGINT))/1024/1024, 2), 0)', 
        "sent": f'COALESCE(ROUND(SUM(TRY_CAST({sent_col} AS BIGINT))/1024/1024, 2), 0)', 
        "received": f'COALESCE(ROUND(SUM(TRY_CAST({recv_col} AS BIGINT))/1024/1024, 2), 0)'
    }
    m_sql = m_map.get(metric, "COUNT(*)")
    where, params = build_where_clause(filters, None, start, end, cols)
    sql = f'SELECT "{col}" as name, {m_sql} as count FROM {from_clause} {where} GROUP BY 1 ORDER BY 2 DESC LIMIT 10'
    return query_to_dict(sql, params)

@app.get("/api/flow-data")
def get_flow_data(cols: str, datasets: Optional[str] = None, filters: Optional[str] = None, start: str = None, end: str = None):
    from_clause = get_from_clause(datasets)
    if not from_clause: return []

    all_cols = get_schema_cols(datasets)
    where, params = build_where_clause(filters, None, start, end, all_cols)
    
    try: sc = json.loads(cols)
    except: sc = ["Source address", "Destination address"]
    sel = [f'"{c}" as col_{i}' for i, c in enumerate(sc)]
    grp = [str(i+1) for i in range(len(sc))]
    
    byte_col = '"Bytes"' if "Bytes" in all_cols else '0'
    sent_col = '"Bytes Sent"' if "Bytes Sent" in all_cols else '0'
    recv_col = '"Bytes Received"' if "Bytes Received" in all_cols else '0'

    sql = f'''
        SELECT {", ".join(sel)}, 
               COUNT(*) as value,
               COALESCE(ROUND(SUM(TRY_CAST({byte_col} AS BIGINT))/1024/1024, 2), 0) as total_mb,
               COALESCE(ROUND(SUM(TRY_CAST({sent_col} AS BIGINT))/1024/1024, 2), 0) as sent_mb,
               COALESCE(ROUND(SUM(TRY_CAST({recv_col} AS BIGINT))/1024/1024, 2), 0) as recv_mb
        FROM {from_clause} {where} 
        GROUP BY {", ".join(grp)} 
        ORDER BY value DESC LIMIT 100
    '''
    return query_to_dict(sql, params)

@app.get("/api/raw-logs")
def get_raw_logs(q: Optional[str] = None, datasets: Optional[str] = None, filters: Optional[str] = None, start: str = None, end: str = None):
    from_clause = get_from_clause(datasets)
    if not from_clause: return []

    cols = get_schema_cols(datasets)
    where, params = build_where_clause(filters, q, start, end, cols)
    
    time_col = get_time_col(cols)
    order_clause = f"ORDER BY {time_col} DESC" if time_col else ""

    sql = f'SELECT * FROM {from_clause} {where} {order_clause} LIMIT 200'
    return query_to_dict(sql, params)

@app.post("/api/upload")
async def upload_log(files: List[UploadFile] = File(...)):
    for file in files:
        file_path = os.path.join(DATA_DIR, file.filename)
        with open(file_path, "wb") as buffer: 
            shutil.copyfileobj(file.file, buffer)
    convert_csvs_to_parquets()
    return {"message": f"Successfully processed {len(files)} files."}

@app.post("/api/clear")
async def clear_logs():
    if os.path.exists(DATA_DIR):
        for f in os.listdir(DATA_DIR):
            os.remove(os.path.join(DATA_DIR, f))
    return {"message": "Cleared all logs."}

app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")