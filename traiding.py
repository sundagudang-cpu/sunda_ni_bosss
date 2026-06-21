import requests
import time
import hmac
import hashlib
import threading
from flask import Flask, render_template_string, jsonify, request

# =====================================================================
# 1. SETINGAN UTAMA (MASUKKAN API KEY DEMO ABANG)
# =====================================================================
API_KEY = '8DG9zekBnsnfLYiU0q6hBaLB2kW2Dfv6CcoGTn2TXVGM71F5X9P4lz0MEdE3oAhL'
SECRET_KEY = 'ri2NQMyMH3yLuLJNnmTNRasTpYV8X4tgW4lJcEqEgieM11taZ4AfQM4LqIxVNMgY'
BASE_URL = "https://testnet.binance.vision"

app = Flask(__name__)

# DATA SERVER LIVE UNTUK KEDUA MECHA ROBOT
data_terminal = {
    "harga_live": 0.0,
    "ma_cepat": 0.0, # Buat Mecha 1 (15m)
    "ma_lambat": 0.0, # Buat Mecha 2 (1h)
    "usdt": 0.0,
    "btc": 0.0,
    
    # PARAMETER MECHA 1: EJEN RONI (COPTER MIKRO)
    "m1_status": "MENCARI MOMENTUM 🔍",
    "m1_trailing": 0.2, # Jaring 0.2%
    "m1_posisi": "KOSONG ⭕",
    "m1_color": "#00ffcc",
    
    # PARAMETER MECHA 2: GUSTIAN BEAST
    "m2_status": "MENCARI MOMENTUM 🔍",
    "m2_trailing": 1.5, # Jaring longgar 1.5%
    "m2_posisi": "KOSONG ⭕",
    "m2_color": "#ff0055",
    
    # LOG PERANG TERPISAH
    "logs_roni": ["System Roni initialized..."],
    "logs_beast": ["System Beast initialized..."]
}

# Variabel Internal Robot 1 (Ejen Roni)
m1_bought = False
m1_buy_price = 0.0
m1_highest = 0.0

# Variabel Internal Robot 2 (Gustian Beast)
m2_bought = False
m2_buy_price = 0.0
m2_highest = 0.0

# =====================================================================
# 2. MESIN KONEKSI BINANCE API
# =====================================================================
def ambil_harga_live():
    try:
        r = requests.get(f"{BASE_URL}/api/v3/ticker/price?symbol=BTCUSDT").json()
        return float(r['price'])
    except: return 0.0

def ambil_ma(interval, limit=20):
    try:
        url = f"{BASE_URL}/api/v3/klines?symbol=BTCUSDT&interval={interval}&limit={limit}"
        data = requests.get(url).json()
        closes = [float(candle[4]) for candle in data]
        return sum(closes) / len(closes)
    except: return 0.0

def ambil_saldo_dompet():
    try:
        url = f"{BASE_URL}/api/v3/account"
        server_time = requests.get(f"{BASE_URL}/api/v3/time").json()['serverTime']
        query = f"timestamp={server_time}"
        sig = hmac.new(SECRET_KEY.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
        headers = {'X-MBX-APIKEY': API_KEY}
        res = requests.get(f"{url}?{query}&signature={sig}", headers=headers).json()
        saldo = {"USDT": 0.0, "BTC": 0.0}
        for b in res['balances']:
            if b['asset'] == 'USDT': saldo['USDT'] = float(b['free'])
            if b['asset'] == 'BTC': saldo['BTC'] = float(b['free'])
        return saldo
    except: return {"USDT": 0.0, "BTC": 0.0}

def kirim_order_pasar(side, qty):
    try:
        url = f"{BASE_URL}/api/v3/order"
        server_time = requests.get(f"{BASE_URL}/api/v3/time").json()['serverTime']
        query = f"symbol=BTCUSDT&side={side}&type=MARKET&quantity={qty}&timestamp={server_time}"
        sig = hmac.new(SECRET_KEY.encode('utf-8'), query.encode('utf-8'), hashlib.sha256).hexdigest()
        headers = {'X-MBX-APIKEY': API_KEY}
        return requests.post(f"{url}?{query}&signature={sig}", headers=headers).json()
    except: return None

def tambah_log(robot, pesan):
    waktu = time.strftime("%H:%M:%S")
    key = "logs_roni" if robot == "roni" else "logs_beast"
    data_terminal[key].insert(0, f"[{waktu}] {pesan}")
    if len(data_terminal[key]) > 4: data_terminal[key].pop()

# =====================================================================
# 3. KORIDOR MECHA CORES (DUAL THREADED BATTLE)
# =====================================================================


def core_war_engine():
    global data_terminal, m1_bought, m1_buy_price, m1_highest, m2_bought, m2_buy_price, m2_highest
    
    while True:
        try:
            harga = ambil_harga_live()
            ma15m = ambil_ma("15m") # Tren Cepat Roni
            ma1h = ambil_ma("1h")   # Tren Kuat Beast
            dompet = ambil_saldo_dompet() # <--- SUDAH BERSIH DARI TYPO, BANG!
            
            data_terminal["harga_live"] = harga
            data_terminal["ma_cepat"] = ma15m
            data_terminal["ma_lambat"] = ma1h
            data_terminal["usdt"] = dompet["USDT"]
            data_terminal["btc"] = dompet["BTC"]
            
            # --- ROBOT 1: EJEN RONI ENGINE (15m, Jaring Rapat) ---
            if not m1_bought:
                data_terminal["m1_status"] = "MENCARI MOMENTUM SCALPING 🔍"
                data_terminal["m1_posisi"] = "KOSONG ⭕"
                if harga > ma15m and ma15m > 0:
                    order = kirim_order_pasar("BUY", "0.005")
                    if order and 'orderId' in order:
                        m1_bought, m1_buy_price, m1_highest = True, harga, harga
                        tambah_log("roni", f"🛒 BUY: 0.005 BTC @${harga:,.2f}")
            else:
                data_terminal["m1_status"] = f"MENJAGA CUAN MIKRO (Beli: ${m1_buy_price:,.2f}) 🛡️"
                data_terminal["m1_posisi"] = "MENGGENGGAM ASSET 💎"
                if harga > m1_highest: m1_highest = harga
                jaring = m1_highest * (1 - (data_terminal["m1_trailing"] / 100))
                if harga <= jaring:
                    order = kirim_order_pasar("SELL", "0.005")
                    if order and 'orderId' in order:
                        m1_bought = False
                        pnl = ((harga - m1_buy_price) / m1_buy_price) * 100
                        tambah_log("roni", f"💰 AUTO SELL: @${harga:,.2f} ({pnl:+.2f}%)")

            # --- ROBOT 2: GUSTIAN BEAST ENGINE (1h, Jaring Longgar SWING) ---
            if not m2_bought:
                data_terminal["m2_status"] = "MENGINTIP TREN RAKSASA 📊"
                data_terminal["m2_posisi"] = "KOSONG ⭕"
                if harga > ma1h and ma1h > 0:
                    order = kirim_order_pasar("BUY", "0.01")
                    if order and 'orderId' in order:
                        m2_bought, m2_buy_price, m2_highest = True, harga, harga
                        tambah_log("beast", f"🛸 BEAST BUY: 0.01 BTC @${harga:,.2f}")
            else:
                data_terminal["m2_status"] = f"BEAST MODE HOLDING (Beli: ${m2_buy_price:,.2f}) 🌋"
                data_terminal["m2_posisi"] = "HOLDING TREND 🚀"
                if harga > m2_highest: m2_highest = harga
                jaring_beast = m2_highest * (1 - (data_terminal["m2_trailing"] / 100))
                if harga <= jaring_beast:
                    order = kirim_order_pasar("SELL", "0.01")
                    if order and 'orderId' in order:
                        m2_bought = False
                        pnl = ((harga - m2_buy_price) / m2_buy_price) * 100
                        tambah_log("beast", f"💥 BEAST SELL: @${harga:,.2f} ({pnl:+.2f}%)")
                        
        except: pass
        time.sleep(1.5)


# =====================================================================
# 4. DASHBOARD CYBERPUNK 2076 TRADING TERMINAL UI
# =====================================================================
CYBER_HTML = """
<!DOCTYPE html>
<html>
<head>
    <title>⚡ CYBER TRADING TERMINAL v5.0 ⚡</title>
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body { background-color: #060810; color: #00ffcc; font-family: 'Courier New', monospace; margin: 0; padding: 10px; }
        .terminal { max-width: 600px; margin: 0 auto; border: 2px solid #00ffcc; box-shadow: 0 0 20px #00ffcc; padding: 15px; background: #0a0e1a; border-radius: 8px; }
        h1 { text-align: center; color: #fff; text-shadow: 0 0 10px #00ffcc, 0 0 20px #00ffcc; font-size: 20px; margin: 5px 0; }
        .glitch-sub { text-align: center; font-size: 10px; color: #ff0055; letter-spacing: 3px; font-weight: bold; margin-bottom: 15px; }
        .grid-split { display: block; margin-bottom: 15px; }
        .card { border: 1px dashed rgba(0,255,204,0.3); padding: 10px; margin-bottom: 10px; background: rgba(0,0,0,0.4); border-radius: 5px; }
        .price-center { font-size: 32px; font-weight: bold; text-align: center; margin: 10px 0; text-shadow: 0 0 10px currentColor; }
        .mecha-box { border-top: 2px solid #fff; margin-top: 15px; padding-top: 10px; }
        .roni-theme { border-color: #00ffcc; box-shadow: inset 0 0 10px rgba(0,255,204,0.1); }
        .beast-theme { border-color: #ff0055; box-shadow: inset 0 0 10px rgba(255,0,85,0.1); color: #ff0055; }
        .mecha-title { font-weight: bold; font-size: 14px; background: #fff; color: #000; padding: 2px 5px; width: fit-content; margin-bottom: 8px; }
        .roni-theme .mecha-title { background: #00ffcc; color: #000; }
        .beast-theme .mecha-title { background: #ff0055; color: #fff; text-shadow: 0 0 5px #fff; }
        .log-box { font-size: 11px; background: #020408; padding: 8px; border-radius: 3px; height: 75px; overflow: hidden; margin-top: 5px; border: 1px solid rgba(255,255,255,0.1); }
        .log-item { margin: 2px 0; color: #fff; }
        .input-cyber { background: #000; border: 1px solid currentColor; color: inherit; padding: 3px 5px; width: 50px; text-align: center; font-family: inherit; }
        .btn-cyber { background: currentColor; color: #000; border: none; padding: 3px 8px; cursor: pointer; font-family: inherit; font-weight: bold; }
        .btn-cyber:hover { opacity: 0.8; }
    </style>
    <script>
        function updateTerminal() {
            fetch('/api/status').then(res => res.json()).then(data => {
                document.getElementById('live-price').innerText = '$' + data.harga_live.toLocaleString();
                document.getElementById('wallet-usdt').innerText = '$' + data.usdt.toLocaleString(undefined,{minimumFractionDigits:2});
                document.getElementById('wallet-btc').innerText = data.btc.toFixed(4) + ' BTC';
                
                // Mecha 1 Update
                document.getElementById('m1-status').innerText = data.m1_status;
                document.getElementById('m1-pos').innerText = data.m1_posisi;
                let roniLogs = document.getElementById('m1-logs');
                roniLogs.innerHTML = '';
                data.logs_roni.forEach(l => roniLogs.innerHTML += `<div class="log-item" style="color:#00ffcc">${l}</div>`);
                
                // Mecha 2 Update
                document.getElementById('m2-status').innerText = data.m2_status;
                document.getElementById('m2-pos').innerText = data.m2_posisi;
                let beastLogs = document.getElementById('m2-logs');
                beastLogs.innerHTML = '';
                data.logs_beast.forEach(l => beastLogs.innerHTML += `<div class="log-item" style="color:#ff0055">${l}</div>`);
            });
        }
        function gantiJaring(robot) {
            let val = document.getElementById('inp-' + robot).value;
            fetch('/api/update_config', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({robot: robot, value: parseFloat(val)})
            }).then(() => alert('MECHA CORE DATABASE RE-CONFIGURED!'));
        }
        setInterval(updateTerminal, 1000);
    </script>
</head>
<body>
    <div class="terminal">
        <h1>⚡ CYBER QUANTUM TERMINAL v5.0 ⚡</h1>
        <div class="glitch-sub">🔥 TWIN MECHA WAR AUTOPILOT ON HP 🔥</div>
        
        <div class="card" style="color: #fff; text-align: center; border-color: #fff;">
            <div style="font-size: 11px; opacity: 0.6;">⚡ INTERCEPTING BINANCE CORE PRICE</div>
            <div id="live-price" class="price-center" style="color: #00ffcc;">$0.00</div>
            <div style="font-size: 11px; color:#ffcc00;">
                TOTAL ASSET: <span id="wallet-usdt">0</span> | <span id="wallet-btc">0</span>
            </div>
        </div>

        <div class="mecha-box roni-theme">
            <div class="mecha-title">🤖 MECHA 01: EJEN RONI (SCALPER COPET)</div>
            <div style="font-size:12px;">
                • STATUS CORE: <span id="m1-status" style="font-weight:bold;">LOAD...</span><br>
                • AMUNISI BARANG: <span id="m1-pos">LOAD...</span><br>
                • SET JARING: <input id="inp-roni" class="input-cyber" type="number" step="0.05" value="0.2"> % 
                <button class="btn-cyber" onclick="gantiJaring('roni')">RE-CONFIG</button>
            </div>
            <div class="log-box" id="m1-logs"></div>
        </div>

        <div class="mecha-box beast-theme">
            <div class="mecha-title">🤖 MECHA 02: GUSTIAN BEAST (SWING HUNTER)</div>
            <div style="font-size:12px;">
                • STATUS CORE: <span id="m2-status" style="font-weight:bold;">LOAD...</span><br>
                • AMUNISI BARANG: <span id="m2-pos">LOAD...</span><br>
                • SET JARING: <input id="inp-beast" class="input-cyber" type="number" step="0.1" value="1.5"> % 
                <button class="btn-cyber" onclick="gantiJaring('beast')">RE-CONFIG</button>
            </div>
            <div class="log-box" id="m2-logs"></div>
        </div>
    </div>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(CYBER_HTML)

@app.route('/api/status')
def get_status():
    return jsonify(data_terminal)

@app.route('/api/update_config', methods=['POST'])
def update_config():
    req = request.json
    if req['robot'] == 'roni':
        data_terminal["m1_trailing"] = float(req['value'])
        tambah_log("roni", f"🔧 Jaring di-tweak ke {req['value']}%")
    elif req['robot'] == 'beast':
        data_terminal["m2_trailing"] = float(req['value'])
        tambah_log("beast", f"🔧 Jaring di-tweak ke {req['value']}%")
    return jsonify({"status": "success"})

if __name__ == "__main__":
    print("🛸 DUAL MECHA WAR INITIATING ON PORT 5000... GET READY!")
    t = threading.Thread(target=core_war_engine)
    t.daemon = True
    t.start()
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
