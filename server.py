# server.py
from flask import Flask, request, jsonify, render_template, send_file
from flask_cors import CORS
import pandas as pd
import io
import os
from datetime import datetime

app = Flask(__name__, template_folder='templates', static_folder='static')
CORS(app)

DATA_CSV = "sensor_data.csv"
DATA_XLSX = "sensor_data.xlsx"

# in-memory store
columns = ["timestamp", "temperature", "humidity"]
if os.path.exists(DATA_CSV):
    df_store = pd.read_csv(DATA_CSV, parse_dates=["timestamp"])
else:
    df_store = pd.DataFrame(columns=columns)

def append_and_save(timestamp, temp, hum):
    global df_store
    row = {"timestamp": timestamp, "temperature": float(temp), "humidity": float(hum)}
    df_store = pd.concat([df_store, pd.DataFrame([row])], ignore_index=True)
    # save CSV
    df_store.to_csv(DATA_CSV, index=False)
    # save XLSX
    df_store.to_excel(DATA_XLSX, index=False)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/data', methods=['POST'])
def data():
    # ESP32 posts JSON like: {"temperature": 25.2, "humidity": 60.3, "timestamp":"..."}
    content = request.get_json(force=True)
    if not content:
        return jsonify({"status":"error","message":"No JSON"}), 400
    temp = content.get('temperature')
    hum = content.get('humidity')
    timestamp = content.get('timestamp', None)
    # normalize timestamp: if ESP provided millis, convert to now
    try:
        if timestamp is None:
            ts = datetime.now()
        else:
            # Try iso-like string, else treat as millis
            try:
                ts = pd.to_datetime(timestamp)
            except:
                ts = datetime.now()
        append_and_save(ts, temp, hum)
        return jsonify({"status":"ok"})
    except Exception as e:
        return jsonify({"status":"error","error":str(e)}), 500

@app.route('/api/latest')
def api_latest():
    if df_store.empty:
        return jsonify({"status":"empty", "data": []})
    last = df_store.tail(1).to_dict(orient='records')[0]
    # ensure timestamp string
    last["timestamp"] = str(last["timestamp"])
    return jsonify({"status":"ok", "data": last})

@app.route('/api/all')
def api_all():
    # return last N or all
    maxrows = int(request.args.get('max', 1000))
    d = df_store.tail(maxrows)
    d_copy = d.copy()
    d_copy['timestamp'] = d_copy['timestamp'].astype(str)
    return jsonify({"status":"ok", "data": d_copy.to_dict(orient='records')})

@app.route('/download/csv')
def download_csv():
    if df_store.empty:
        return "No data", 404
    return send_file(DATA_CSV, as_attachment=True)

@app.route('/download/xlsx')
def download_xlsx():
    if df_store.empty:
        return "No data", 404
    return send_file(DATA_XLSX, as_attachment=True)

if __name__ == '__main__':
    # run on 0.0.0.0 so ESP32 can reach it
    app.run(host='0.0.0.0', port=5000, debug=True)
