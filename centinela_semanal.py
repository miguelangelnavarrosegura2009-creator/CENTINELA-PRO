import os
import json
import time
import requests
import pandas as pd
import numpy as np
from datetime import datetime

# ==========================================
# CONFIGURACIÓN GENERAL Y LÍMITES
# ==========================================
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "8352601243:AAH3k_lG0mC6fFjE5Jk5JvQ")  # Ajustar según tu entorno
DESTINATARIOS = [
    "-1003562999737",  # Supergrupo
    "7240172969"        # Chat privado
]

MAX_ENTRADAS_DIA = 10
ARCHIVO_REGISTRO_DIARIO = "registro_diario.json"
ARCHIVO_POSICIONES = "posiciones_activas.json"
ARCHIVO_EXCEL = "registro_operaciones_centinela.csv"

# ==========================================
# CONTROL DE CUPO DIARIO
# ==========================================
def contar_alertas_hoy() -> int:
    hoy = datetime.now().strftime("%Y-%m-%d")
    if os.path.exists(ARCHIVO_REGISTRO_DIARIO):
        try:
            with open(ARCHIVO_REGISTRO_DIARIO, "r", encoding="utf-8") as f:
                data = json.load(f)
                if data.get("fecha") == hoy:
                    return len(data.get("entradas", []))
        except Exception:
            return 0
    return 0

def registrar_alerta_diaria(ticker: str):
    hoy = datetime.now().strftime("%Y-%m-%d")
    data = {"fecha": hoy, "entradas": []}
    if os.path.exists(ARCHIVO_REGISTRO_DIARIO):
        try:
            with open(ARCHIVO_REGISTRO_DIARIO, "r", encoding="utf-8") as f:
                contenido = json.load(f)
                if contenido.get("fecha") == hoy:
                    data = contenido
        except Exception:
            pass
    data["entradas"].append({"ticker": ticker, "hora": datetime.now().isoformat()})
    with open(ARCHIVO_REGISTRO_DIARIO, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

# ==========================================
# RECOLECCIÓN DE MERCADO CRYPTO (BINANCE)
# ==========================================
def obtener_pares_binance(volumen_minimo_usdt: float = 3000000.0):
    """
    Descarga todos los pares spot contra USDT en Binance, incluyendo Memecoins.
    Filtra por volumen de 24h para garantizar liquidez real.
    """
    url = "https://api.binance.com/api/v3/ticker/24hr"
    pares_filtrados = []
    try:
        res = requests.get(url, timeout=12)
        if res.status_code == 200:
            tickers = res.json()
            for t in tickers:
                symbol = t.get("symbol", "")
                if symbol.endswith("USDT") and not any(ign in symbol for ign in ["UPUSDT", "DOWNUSDT", "BEARUSDT", "BULLUSDT"]):
                    volumen_usdt = float(t.get("quoteVolume", 0))
                    if volumen_usdt >= volumen_minimo_usdt:
                        pares_filtrados.append({
                            "symbol": symbol,
                            "last_price": float(t.get("lastPrice", 0)),
                            "high_24h": float(t.get("highPrice", 0)),
                            "low_24h": float(t.get("lowPrice", 0)),
                            "volumen_usdt": volumen_usdt,
                            "price_change_pct": float(t.get("priceChangePercent", 0))
                        })
            pares_filtrados.sort(key=lambda x: x["volumen_usdt"], reverse=True)
    except Exception as e:
        print(f"Error conectando a Binance: {e}")
    return pares_filtrados

def obtener_klines_binance(symbol: str, intervalo: str = "1d", limit: int = 100):
    """Descarga velas OHLCV desde Binance."""
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={intervalo}&limit={limit}"
    try:
        r = requests.get(url, timeout=10)
        if r.status_code == 200:
            raw = r.json()
            df = pd.DataFrame(raw, columns=[
                "open_time", "open", "high", "low", "close", "volume",
                "close_time", "quote_asset_volume", "number_of_trades",
                "taker_buy_base_asset_volume", "taker_buy_quote_asset_volume", "ignore"
            ])
            df["close"] = df["close"].astype(float)
            df["high"] = df["high"].astype(float)
            df["low"] = df["low"].astype(float)
            return df
    except Exception:
        pass
    return pd.DataFrame()

# ==========================================
# CÁLCULOS TÉCNICOS (RSI, ATR, EMAs)
# ==========================================
def calcular_indicadores(df: pd.DataFrame):
    if len(df) < 30:
        return None
    close = df["close"]
    high = df["high"]
    low = df["low"]

    # EMA 20 y EMA 50
    ema20 = close.ewm(span=20, adjust=False).mean().iloc[-1]
    ema50 = close.ewm(span=50, adjust=False).mean().iloc[-1]

    # RSI (14 periodos)
    delta = close.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss + 1e-9)
    rsi = 100 - (100 / (1 + rs))
    rsi_val = float(rsi.iloc[-1])

    # ATR (14 periodos)
    tr1 = high - low
    tr2 = (high - close.shift()).abs()
    tr3 = (low - close.shift()).abs()
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr_val = float(tr.rolling(14).mean().iloc[-1])

    return {
        "precio": float(close.iloc[-1]),
        "ema20": float(ema20),
        "ema50": float(ema50),
        "rsi": round(rsi_val, 1),
        "atr": round(atr_val, 4)
    }

# ==========================================
# EVALUACIÓN DE ACTIVOS CRYPTO
# ==========================================
def evaluar_activo_crypto(par_info: dict):
    symbol = par_info["symbol"]
    df = obtener_klines_binance(symbol, intervalo="1d", limit=80)
    if df.empty:
        return None, "Sin datos de velas"

    ind = calcular_indicadores(df)
    if not ind:
        return None, "Datos insuficientes"

    precio = ind["precio"]
    rsi = ind["rsi"]
    atr = ind["atr"]

    # Criterio: Pullback saludable en tendencia o consolidación con rebote en RSI (30 a 62)
    if not (30 <= rsi <= 62):
     return None, f"RSI fuera de zona ({rsi})"

    # Corrección desde el máximo reciente
    max_reciente = df["high"].tail(20).max()
    descuento = round(((max_reciente - precio) / max_reciente) * 100, 1) if max_reciente > 0 else 0

    if descuento < 2.0:
        return None, f"Descuento insuficiente ({descuento}%)"

    # Definir Take-Profit y Stop-Loss (Ratio 2:1 con ATR)
    distancia_sl = max(atr * 1.5, precio * 0.04)
    distancia_tp = distancia_sl * 2.0

    sl = round(precio - distancia_sl, 4 if precio < 1 else 2)
    tp = round(precio + distancia_tp, 4 if precio < 1 else 2)

    pct_tp = round(((tp - precio) / precio) * 100, 1)
    pct_sl = round(((precio - sl) / precio) * 100, 1)

    rango_min = round(precio * 0.985, 4 if precio < 1 else 2)
    score = round(100 - rsi + (descuento * 0.5), 1)

    nombre = symbol.replace("USDT", "")

    datos_alerta = {
        "ticker": symbol,
        "nombre_empresa": f"{nombre} Crypto / Token",
        "precio": precio,
        "rango_entrada": f"${rango_min} - ${precio}",
        "descuento": descuento,
        "rsi": rsi,
        "atr": atr,
        "dinamica": "🪙 CRYPTO / ALTA VOLATILIDAD" if descuento > 15 else "🚀 MEME / SWING TOKEN",
        "soporte": "Zona ATR / Soporte Dinámico",
        "score_tecnico": score,
        "take_profit": tp,
        "stop_loss": sl,
        "pct_tp": pct_tp,
        "pct_sl": pct_sl,
        "tiempo_estimado": "3 a 7 días",
        "token_symbol": nombre,
        "par_binance": symbol,
        "fecha_deteccion": datetime.now().strftime("%d/%m/%Y %I:%M %p")
    }
    return datos_alerta, "Aprobada"

# ==========================================
# DESPACHO A TELEGRAM
# ==========================================
def enviar_alerta_telegram(mensaje: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in DESTINATARIOS:
        payload = {"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown"}
        try:
            requests.post(url, json=payload, timeout=8)
        except Exception as e:
            print(f"Error despachando hacia {chat_id}: {e}")

def formato_mensaje_telegram(alerta: dict, posicion: int) -> str:
    return (
        f"🚨 *SEÑAL #{posicion} DETECTADA: {alerta['ticker']}*\n"
        f"🏷 *Activo:* {alerta['nombre_empresa']}\n"
        f"⚡ *Dinámica:* {alerta['dinamica']}\n\n"
        f"🎯 *Zona de Compra:* {alerta['rango_entrada']}\n"
        f"💵 *Precio Actual:* ${alerta['precio']}\n"
        f"📊 *RSI:* {alerta['rsi']} | Corrección: -{alerta['descuento']}%\n\n"
        f"🟢 *Take-Profit:* ${alerta['take_profit']} (+{alerta['pct_tp']}%)\n"
        f"🔴 *Stop-Loss:* ${alerta['stop_loss']} (-{alerta['pct_sl']}%)\n"
        f"⚖️ *Ratio Riesgo/Beneficio:* 2.0:1\n"
        f"🕒 *Temporalidad:* {alerta['tiempo_estimado']}\n"
    )

# ==========================================
# BUCLE PRINCIPAL DE EJECUCIÓN
# ==========================================
def ejecutar_escaneo():
    cupo_actual = contar_alertas_hoy()
    disponibles = MAX_ENTRADAS_DIA - cupo_actual

    print(f"--- INICIANDO CENTINELA PRO (Cupo diario emitido: {cupo_actual}/{MAX_ENTRADAS_DIA}) ---")
    if disponibles <= 0:
        print("Cupo diario cubierto (10/10). No se emitirán más señales hoy.")
        return []

    print("Obteniendo universo de pares y memecoins desde Binance Spot...")
    pares = obtener_pares_binance()
    print(f"Total de pares con volumen relevante: {len(pares)}")

    candidatas = []
    for par in pares:
        symbol = par["symbol"]
        datos, motivo = evaluar_activo_crypto(par)
        if datos:
            print(f" -> [APROBADA] {symbol} | RSI: {datos['rsi']} | Score: {datos['score_tecnico']}")
            candidatas.append(datos)
        time.sleep(0.05)  # Respetar rate limit de la API pública

    candidatas.sort(key=lambda x: x["score_tecnico"], reverse=True)
    seleccionadas = candidatas[:disponibles]

    for i, alerta in enumerate(seleccionadas, start=cupo_actual + 1):
        msg = formato_mensaje_telegram(alerta, i)
        enviar_alerta_telegram(msg)
        registrar_alerta_diaria(alerta["ticker"])
        print(f"Alerta enviada a Telegram y registrada: {alerta['ticker']}")

    return seleccionadas

if __name__ == "__main__":
    ejecutar_escaneo()