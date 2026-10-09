import os
import json
import csv
import urllib.parse
from datetime import datetime
import numpy as np
import pandas as pd
import requests
import feedparser
import yfinance as yf
import pandas_ta as ta

# ==========================================
# CONFIGURACIÓN GENERAL Y CREDENCIALES
# ==========================================
TELEGRAM_BOT_TOKEN = "8804398475:AAH-7HmRjGMBwPqX3vv4Jr4xSFaFMN-VqqI"

DESTINATARIOS = [
    "-1003562999737",  # Supergrupo 'MEJORES ENTRADAS ACCIONES'
    "7240172969"       # Chat privado
]

MAX_ENTRADAS_SEMANA = 4
TOP_CANDIDATAS_PREVIAS = 10
ARCHIVO_REGISTRO = "registro_semanal.json"
ARCHIVO_POSICIONES = "posiciones_activas.json"
ARCHIVO_MAPEO = "mapeo_simbolos_binance.json"
ARCHIVO_EXCEL = "registro_operaciones_centinela.csv"

DIAS_BLOQUEO_EARNINGS = 8
MULTIPLICADOR_TP_ATR = 3.0
MULTIPLICADOR_SL_ATR = 1.5
MAX_FACTOR_VOLUMEN_PANICO = 1.8
TOLERANCIA_SOPORTE_PCT = 1.8

# Catálogo consolidado de acciones (Sin criptos)
WATCHLIST_EXPANDIDA = {
    # --- RÁPIDAS / CRECIMIENTO / TECNOLOGÍA / IA ---
    "AMZN": {"nombre": "Amazon.com Inc.", "token": "AMZNB", "perfil_esperado": "RAPIDA"},
    "NVDA": {"nombre": "NVIDIA Corporation", "token": "NVDAB", "perfil_esperado": "RAPIDA"},
    "TSLA": {"nombre": "Tesla Inc.", "token": "TSLAB", "perfil_esperado": "RAPIDA"},
    "AMD":  {"nombre": "Advanced Micro Devices", "token": "AMDB",  "perfil_esperado": "RAPIDA"},
    "META": {"nombre": "Meta Platforms Inc.", "token": "METAB", "perfil_esperado": "RAPIDA"},
    "GOOGL":{"nombre": "Alphabet Inc.", "token": "GOOGLB", "perfil_esperado": "RAPIDA"},
    "MSFT": {"nombre": "Microsoft Corporation", "token": "MSFTB", "perfil_esperado": "RAPIDA"},
    "AAPL": {"nombre": "Apple Inc.", "token": "AAPLB", "perfil_esperado": "RAPIDA"},
    "AVGO": {"nombre": "Broadcom Inc.", "token": "AVGOB", "perfil_esperado": "RAPIDA"},
    "TSM":  {"nombre": "Taiwan Semiconductor (TSMC)", "token": "TSMB", "perfil_esperado": "RAPIDA"},
    "NFLX": {"nombre": "Netflix Inc.", "token": "NFLXB", "perfil_esperado": "RAPIDA"},
    "CRM":  {"nombre": "Salesforce Inc.", "token": "CRMB", "perfil_esperado": "RAPIDA"},
    "ADBE": {"nombre": "Adobe Inc.", "token": "ADBEB", "perfil_esperado": "RAPIDA"},
    "COIN": {"nombre": "Coinbase Global Inc.", "token": "COINB", "perfil_esperado": "RAPIDA"},
    "PLTR": {"nombre": "Palantir Technologies", "token": "PLTRB", "perfil_esperado": "RAPIDA"},
    "UBER": {"nombre": "Uber Technologies Inc.", "token": "UBERB", "perfil_esperado": "RAPIDA"},
    "QCOM": {"nombre": "Qualcomm Inc.", "token": "QCOMB", "perfil_esperado": "RAPIDA"},
    "ASML": {"nombre": "ASML Holding N.V.", "token": "ASMLB", "perfil_esperado": "RAPIDA"},
    "INTC": {"nombre": "Intel Corporation", "token": "INTCB", "perfil_esperado": "RAPIDA"},

    # --- CONSUMO MASIVO, RETAIL Y VALOR DEFENSIVO ---
    "MCD":  {"nombre": "McDonald's Corporation", "token": "MCDB", "perfil_esperado": "MODERADA"},
    "KO":   {"nombre": "The Coca-Cola Company", "token": "KOB", "perfil_esperado": "MODERADA"},
    "PEP":  {"nombre": "PepsiCo Inc.", "token": "PEPB", "perfil_esperado": "MODERADA"},
    "WMT":  {"nombre": "Walmart Inc.", "token": "WMTB", "perfil_esperado": "MODERADA"},
    "COST": {"nombre": "Costco Wholesale Corp.", "token": "COSTB", "perfil_esperado": "MODERADA"},
    "PG":   {"nombre": "Procter & Gamble Co.", "token": "PGB", "perfil_esperado": "MODERADA"},
    "DIS":  {"nombre": "The Walt Disney Company", "token": "DISB", "perfil_esperado": "MODERADA"},
    "NKE":  {"nombre": "Nike Inc.", "token": "NKEB", "perfil_esperado": "MODERADA"},

    # --- SALUD, FARMACÉUTICAS E INDUSTRIA ---
    "JNJ":  {"nombre": "Johnson & Johnson", "token": "JNJB", "perfil_esperado": "MODERADA"},
    "PFE":  {"nombre": "Pfizer Inc.", "token": "PFEB", "perfil_esperado": "MODERADA"},
    "ABBV": {"nombre": "AbbVie Inc.", "token": "ABBV", "perfil_esperado": "MODERADA"},
    "LLY":  {"nombre": "Eli Lilly and Company", "token": "LLYB", "perfil_esperado": "RAPIDA"},
    "MRK":  {"nombre": "Merck & Co. Inc.", "token": "MRKB", "perfil_esperado": "MODERADA"},
    "CAT":  {"nombre": "Caterpillar Inc.", "token": "CATB", "perfil_esperado": "MODERADA"},
    "BA":   {"nombre": "The Boeing Company", "token": "BAB", "perfil_esperado": "MODERADA"},
    "GE":   {"nombre": "GE Aerospace", "token": "GEB", "perfil_esperado": "MODERADA"},

    # --- BANCA, FINANZAS Y ENERGÍA ---
    "JPM":  {"nombre": "JPMorgan Chase & Co.", "token": "JPMB", "perfil_esperado": "MODERADA"},
    "V":    {"nombre": "Visa Inc.", "token": "VB", "perfil_esperado": "MODERADA"},
    "MA":   {"nombre": "Mastercard Inc.", "token": "MAB", "perfil_esperado": "MODERADA"},
    "GS":   {"nombre": "The Goldman Sachs Group", "token": "GSB", "perfil_esperado": "MODERADA"},
    "XOM":  {"nombre": "Exxon Mobil Corp.", "token": "XOMB", "perfil_esperado": "MODERADA"},
    "CVX":  {"nombre": "Chevron Corporation", "token": "CVXB", "perfil_esperado": "MODERADA"}
}


def registrar_en_excel(datos_alerta: dict):
    """Guarda la entrada en un archivo CSV/Excel para seguimiento y cálculo de win rate."""
    encabezados = [
        "Fecha_Hora", "Ticker", "Nombre_Empresa", "Perfil_Dinamica",
        "Precio_Entrada", "Take_Profit", "Stop_Loss", "Ratio_RR",
        "Pct_TP", "Pct_SL", "Soporte", "Score", "Estado", "Precio_Salida", "Rendimiento_Pct"
    ]
    archivo_existe = os.path.exists(ARCHIVO_EXCEL)

    fila = {
        "Fecha_Hora": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Ticker": datos_alerta["ticker"],
        "Nombre_Empresa": datos_alerta["nombre_empresa"],
        "Perfil_Dinamica": datos_alerta["dinamica"],
        "Precio_Entrada": datos_alerta["precio"],
        "Take_Profit": datos_alerta["take_profit"],
        "Stop_Loss": datos_alerta["stop_loss"],
        "Ratio_RR": "2.0:1",
        "Pct_TP": f"+{datos_alerta['pct_tp']}%",
        "Pct_SL": f"-{datos_alerta['pct_sl']}%",
        "Soporte": datos_alerta["soporte"],
        "Score": datos_alerta["score_tecnico"],
        "Estado": "ABIERTA",
        "Precio_Salida": "",
        "Rendimiento_Pct": ""
    }

    with open(ARCHIVO_EXCEL, mode="a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=encabezados)
        if not archivo_existe:
            writer.writeheader()
        writer.writerow(fila)


def calcular_winrate_excel() -> str:
    """Calcula el Win Rate histórico acumulado desde el archivo Excel."""
    if not os.path.exists(ARCHIVO_EXCEL):
        return "N/A (Sin histórico)"
    try:
        df = pd.read_csv(ARCHIVO_EXCEL)
        cerradas = df[df["Estado"].isin(["GANADA", "PERDIDA", "TAKE_PROFIT", "STOP_LOSS"])]
        if cerradas.empty:
            return "Pendiente (Trades abiertos)"
        ganadas = len(df[df["Estado"].isin(["GANADA", "TAKE_PROFIT"])])
        winrate = round((ganadas / len(cerradas)) * 100, 1)
        return f"{winrate}% ({ganadas}/{len(cerradas)})"
    except Exception:
        return "Pendiente"


def gestionar_cupo_semanal() -> int:
    semana_actual = datetime.now().strftime("%Y-W%W")
    if not os.path.exists(ARCHIVO_REGISTRO):
        return 0
    with open(ARCHIVO_REGISTRO, "r") as f:
        try:
            datos = json.load(f)
            if datos.get("semana") == semana_actual:
                return len(datos.get("entradas", []))
            return 0
        except Exception:
            return 0


def registrar_alerta(ticker: str):
    semana_actual = datetime.now().strftime("%Y-W%W")
    datos = {"semana": semana_actual, "entradas": []}
    if os.path.exists(ARCHIVO_REGISTRO):
        with open(ARCHIVO_REGISTRO, "r") as f:
            try:
                contenido = json.load(f)
                if contenido.get("semana") == semana_actual:
                    datos = contenido
            except Exception:
                pass
    datos["entradas"].append({"ticker": ticker, "fecha": datetime.now().isoformat()})
    with open(ARCHIVO_REGISTRO, "w") as f:
        json.dump(datos, f, indent=4)


def registrar_posicion_activa(datos_alerta: dict):
    posiciones = []
    if os.path.exists(ARCHIVO_POSICIONES):
        try:
            with open(ARCHIVO_POSICIONES, "r") as f:
                posiciones = json.load(f)
        except Exception:
            posiciones = []
    posicion = {
        "ticker": datos_alerta["ticker"],
        "token_symbol": datos_alerta["token_symbol"],
        "par_binance": datos_alerta.get("par_binance"),
        "precio_entrada": datos_alerta["precio"],
        "take_profit": datos_alerta["take_profit"],
        "stop_loss": datos_alerta["stop_loss"],
        "pct_tp": datos_alerta["pct_tp"],
        "pct_sl": datos_alerta["pct_sl"],
        "fecha": datetime.now().isoformat(),
        "breakeven_activado": False
    }
    posiciones.append(posicion)
    with open(ARCHIVO_POSICIONES, "w") as f:
        json.dump(posiciones, f, indent=4)


def enviar_alerta_telegram(mensaje: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    for chat_id in DESTINATARIOS:
        payload = {"chat_id": chat_id, "text": mensaje, "parse_mode": "Markdown", "disable_web_page_preview": False}
        try:
            res = requests.post(url, json=payload, timeout=10)
            if not res.json().get("ok"):
                payload.pop("parse_mode")
                requests.post(url, json=payload, timeout=10)
            print(f"-> Mensaje despachado a {chat_id}")
        except Exception as e:
            print(f"Error despachando hacia {chat_id}: {e}")


def obtener_sentimiento_mercado() -> str:
    try:
        url = "https://api.alternative.me/fng/?limit=1"
        res = requests.get(url, timeout=4).json()
        valor = res["data"][0]["value"]
        clasificacion = res["data"][0]["value_classification"]
        return f"{clasificacion} ({valor}/100)"
    except Exception:
        return "Neutral (50/100)"


def evaluar_regimen_mercado() -> tuple[bool, str]:
    try:
        spy = yf.Ticker("SPY")
        df = spy.history(period="6mo", interval="1d")
        if len(df) < 50:
            return True, "Datos SPY estándar."
        df['EMA50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        precio_spy = float(df['Close'].iloc[-1])
        ema50_spy = float(df['EMA50'].dropna().iloc[-1])
        rsi_spy = float(df['RSI'].dropna().iloc[-1])
        if precio_spy < (ema50_spy * 0.96) and rsi_spy < 32:
            return False, f"Mercado en pánico severo (SPY bajo EMA50 y RSI {round(rsi_spy,1)})."
        return True, "Condición Macro favorable / neutral."
    except Exception as e:
        return True, f"Modo estándar: {e}"


def proximo_a_earnings(stock_obj, ticker: str, dias_limite: int = DIAS_BLOQUEO_EARNINGS) -> tuple[bool, str]:
    try:
        cal = stock_obj.calendar
        fecha_reporte = None
        if isinstance(cal, pd.DataFrame) and not cal.empty and "Earnings Date" in cal.index:
            fecha_reporte = pd.to_datetime(cal.loc["Earnings Date"].iloc[0])
        elif isinstance(cal, dict) and "Earnings Date" in cal:
            val = cal["Earnings Date"]
            fecha_reporte = pd.to_datetime(val[0] if isinstance(val, list) else val)
        if fecha_reporte is not None:
            fecha_reporte = fecha_reporte.tz_localize(None) if fecha_reporte.tzinfo else fecha_reporte
            dias_restantes = (fecha_reporte - datetime.now()).days
            if 0 <= dias_restantes <= dias_limite:
                return True, f"Reporta resultados en {dias_restantes} días ({fecha_reporte.strftime('%Y-%m-%d')})"
    except Exception:
        pass
    return False, ""


def analizar_estacionalidad_mes(stock_obj) -> tuple[float, float, bool]:
    mes_actual = datetime.now().month
    try:
        df_m = stock_obj.history(period="8y", interval="1mo")
        if len(df_m) < 24:
            return 0.0, 50.0, True
        df_m["Ret"] = df_m["Close"].pct_change() * 100
        df_mes = df_m[df_m.index.month == mes_actual]
        if df_mes.empty:
            return 0.0, 50.0, True
        rets = df_mes["Ret"].dropna()
        if len(rets) == 0:
            return 0.0, 50.0, True
        ret_prom = float(rets.mean())
        win_rate = float(((rets > 0).sum() / len(rets)) * 100)
        return round(ret_prom, 1), round(win_rate, 1), (ret_prom >= -1.0 and win_rate >= 45.0)
    except Exception:
        return 0.0, 50.0, True


def evaluar_tecnico_historico(ticker: str, meta: dict):
    try:
        stock = yf.Ticker(ticker)

        # 1. Filtro de earnings
        riesgo_earnings, motivo_earnings = proximo_a_earnings(stock, ticker)
        if riesgo_earnings:
            return None, f"Earnings cercanos: {motivo_earnings}"

        # 2. Estacionalidad histórica mensual
        ret_mes, win_mes, estacionalidad_ok = analizar_estacionalidad_mes(stock)
        if not estacionalidad_ok:
            return None, f"Estacionalidad desfavorable ({ret_mes}% prom, {win_mes}% win)"

        # 3. Velas diarias
        df = stock.history(period="2y", interval="1d")
        if len(df) < 150:
            return None, "Historial insuficiente"

        df['EMA50'] = ta.ema(df['Close'], length=50)
        df['EMA100'] = ta.ema(df['Close'], length=100)
        df['EMA200'] = ta.ema(df['Close'], length=min(200, len(df)-1))
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)
        df['VOL_SMA20'] = df['Volume'].rolling(20).mean()

        bb = ta.bbands(df['Close'], length=20, std=2)
        bb_lower = float(bb[[c for c in bb.columns if 'BBL' in c][0]].dropna().iloc[-1]) if bb is not None else float(df['Close'].iloc[-1]) * 0.95

        precio = float(df['Close'].iloc[-1])
        ema50 = float(df['EMA50'].dropna().iloc[-1])
        ema100 = float(df['EMA100'].dropna().iloc[-1])
        ema200 = float(df['EMA200'].dropna().iloc[-1])
        maximo_mes = float(df['High'].rolling(20).max().iloc[-1])
        descuento = ((maximo_mes - precio) / maximo_mes) * 100
        rsi = float(df['RSI'].dropna().iloc[-1])
        atr = float(df['ATR'].dropna().iloc[-1])
        vol_actual = float(df['Volume'].iloc[-1])
        vol_medio = float(df['VOL_SMA20'].dropna().iloc[-1])

        # Dinámica de movimiento
        atr_pct = (atr / precio) * 100
        if atr_pct >= 2.3 or meta.get("perfil_esperado") == "RAPIDA":
            etiqueta_dinamica = "⚡ ALTA DINÁMICA / MOVIMIENTO RÁPIDO"
            rango_desc_min, rango_desc_max = 3.5, 16.0
        else:
            etiqueta_dinamica = "🐢 DEFENSIVA / MOVIMIENTO MODERADO"
            rango_desc_min, rango_desc_max = 2.0, 10.0

        if vol_medio > 0 and (vol_actual > vol_medio * MAX_FACTOR_VOLUMEN_PANICO) and (descuento > 5.0):
            return None, f"Volumen excesivo de venta ({round(vol_actual/vol_medio, 1)}x)"
        if precio < (ema200 * 0.90):
            return None, "Tendencia bajista mayor bajo EMA 200"
        if not (rango_desc_min <= descuento <= rango_desc_max):
            return None, f"Descuento fuera de rango ({round(descuento, 1)}%)"
        if rsi > 54:
            return None, f"RSI alto ({round(rsi, 1)})"

        dist_ema50 = abs((precio - ema50) / ema50) * 100
        dist_ema100 = abs((precio - ema100) / ema100) * 100
        dist_bb = abs((precio - bb_lower) / bb_lower) * 100
        en_soporte = (dist_ema50 <= TOLERANCIA_SOPORTE_PCT) or (dist_ema100 <= TOLERANCIA_SOPORTE_PCT) or (precio <= bb_lower or dist_bb <= TOLERANCIA_SOPORTE_PCT)
        if not en_soporte:
            return None, "Lejos de soporte clave"

        soporte_identificado = "Banda Bollinger Inferior" if (precio <= bb_lower or dist_bb <= TOLERANCIA_SOPORTE_PCT) else ("EMA 50 diaria" if dist_ema50 <= TOLERANCIA_SOPORTE_PCT else "EMA 100 diaria")

        cierre = float(df['Close'].iloc[-1])
        apertura = float(df['Open'].iloc[-1])
        minimo = float(df['Low'].iloc[-1])
        maximo = float(df['High'].iloc[-1])
        rango = max(0.01, maximo - minimo)
        ratio_mecha = (min(cierre, apertura) - minimo) / rango
        if not ((cierre >= apertura) or (ratio_mecha >= 0.28)):
            return None, f"Presión bajista sin absorción (Mecha: {round(ratio_mecha*100, 1)}%)"

        precios_rec = df['Low'].iloc[-15:].values
        rsi_rec = df['RSI'].iloc[-15:].values
        div_alcista = (precios_rec[-1] <= precios_rec[0] and rsi_rec[-1] > (rsi_rec[0] + 1.5)) if len(precios_rec) >= 15 else False

        score_tecnico = min(30, (descuento / 8.0) * 30) + max(0, (50 - rsi) * 1.5) + (15 if en_soporte else 0) + (15 if div_alcista else 0) + (10 if win_mes >= 60 else 0)

        tp_precio = round(precio + (atr * MULTIPLICADOR_TP_ATR), 2)
        sl_precio = round(precio - (atr * MULTIPLICADOR_SL_ATR), 2)
        pct_tp = round(((tp_precio - precio) / precio) * 100, 1)
        pct_sl = round(((precio - sl_precio) / precio) * 100, 1)

        dias_estimados = (atr * MULTIPLICADOR_TP_ATR / atr) if atr > 0 else 15
        sem_min = max(1, round(dias_estimados / 7))
        sem_max = round(sem_min * 1.5) + 1

        # Enlace oficial corporativo a Yahoo Finance Profile y TradingView
        link_perfil = f"https://finance.yahoo.com/quote/{ticker}/profile"
        link_grafico = f"https://www.tradingview.com/symbols/{ticker}/"

        return {
            "ticker": ticker,
            "nombre_empresa": meta.get("nombre", ticker),
            "precio": round(precio, 2),
            "rango_entrada": f"${round(precio*0.988, 2)} -${round(precio, 2)}",
            "descuento": round(descuento, 1),
            "rsi": round(rsi, 1),
            "atr": round(atr, 2),
            "dinamica": etiqueta_dinamica,
            "soporte": soporte_identificado,
            "estacionalidad": f"{win_mes}% win ({ret_mes}% prom)",
            "divergencia": "Confirmada 📈" if div_alcista else "No",
            "score_tecnico": round(score_tecnico, 1),
            "take_profit": tp_precio,
            "stop_loss": sl_precio,
            "pct_tp": pct_tp,
            "pct_sl": pct_sl,
            "tiempo_estimado": f"{sem_min} a {sem_max} semanas",
            "link_perfil": link_perfil,
            "link_grafico": link_grafico
        }, "Aprobada"
    except Exception as e:
        return None, f"Error técnico: {e}"


def obtener_info_mapeo_binance(ticker: str, token_symbol: str) -> dict:
    if os.path.exists(ARCHIVO_MAPEO):
        try:
            with open(ARCHIVO_MAPEO, "r") as f:
                mapa = json.load(f)
                if ticker in mapa:
                    return mapa[ticker]
        except Exception:
            pass
    return {"fuente_primaria": "BINANCE_SPOT", "par_binance": f"{token_symbol}USDT"}


def ejecutar_filtro_semanal():
    entradas_hechas = gestionar_cupo_semanal()
    cupos_disponibles = MAX_ENTRADAS_SEMANA - entradas_hechas
    ahora_str = datetime.now().strftime("%d/%m/%Y a las %I:%M:%S %p")

    print("\n" + "=" * 80)
    print(f"🛡️  CENTINELA: AUDITORÍA EXCLUSIVA DE ACCIONES EN POWERSHELL")
    print(f"🕒 Fecha y Hora: {ahora_str}")
    print("=" * 80)

    sentimiento = obtener_sentimiento_mercado()
    macro_ok, motivo_macro = evaluar_regimen_mercado()
    winrate_actual = calcular_winrate_excel()

    print(f"• Sentimiento Global (Fear & Greed): {sentimiento}")
    print(f"• Régimen Macro S&P 500: {'🟢 FAVORABLE' if macro_ok else '🔴 PRECAUCIÓN'} ({motivo_macro})")
    print(f"• Rendimiento Histórico Registrado (Win Rate): {winrate_actual}")

    if not macro_ok:
        print("\nEscaneo suspendido temporalmente por condiciones de pánico generalizado.")
        return

    print(f"\nAuditando {len(WATCHLIST_EXPANDIDA)} empresas...")
    print("-" * 80)
    print(f"{'TICKER':<8} | {'PERFIL':<12} | {'ESTADO / DIAGNÓSTICO':<55}")
    print("-" * 80)

    candidatas = []
    for ticker, meta in WATCHLIST_EXPANDIDA.items():
        datos, motivo = evaluar_tecnico_historico(ticker, meta)
        perfil = "RÁPIDA" if meta.get("perfil_esperado") == "RAPIDA" else "MODERADA"

        if datos:
            info_b = obtener_info_mapeo_binance(ticker, meta["token"])
            datos["token_symbol"] = meta["token"]
            datos["par_binance"] = info_b.get("par_binance")
            candidatas.append(datos)
            print(f"{ticker:<8} | {perfil:<12} | ✅ CALIFICA | Soporte: {datos['soporte'][:18]} | ${datos['precio']}")
        else:
            print(f"{ticker:<8} | {perfil:<12} | ❌ DESCARTADA: {motivo[:50]}")

    print("-" * 80)
    print(f"Total empresas analizadas: {len(WATCHLIST_EXPANDIDA)} | Calificaron: {len(candidatas)}")

    if not candidatas:
        print("\nNo hay acciones que cumplan con todos los requisitos en esta sesión.")
        return

    # Ordenar estrictamente por calidad cuantitativa
    candidatas.sort(key=lambda x: x["score_tecnico"], reverse=True)

    # TABLA RESUMEN EN CONSOLA
    print("\n" + "=" * 80)
    print("📋 RANKING FINAL DE OPORTUNIDADES")
    print("=" * 80)
    for i, item in enumerate(candidatas[:TOP_CANDIDATAS_PREVIAS], 1):
        print(f"#{i} | {item['ticker']} | {item['nombre_empresa'][:22]} | Score: {item['score_tecnico']}/100 | TP: +{item['pct_tp']}% | SL: -{item['pct_sl']}%")
    print("=" * 80)

    if cupos_disponibles <= 0:
        print(f"\nCupo semanal cubierto ({MAX_ENTRADAS_SEMANA}/{MAX_ENTRADAS_SEMANA}). No se enviaron nuevas alertas.")
        return

    las_mejores = candidatas[:cupos_disponibles]
    print(f"\nDespachando las {len(las_mejores)} mejores alertas al supergrupo de Telegram...")

    for sel in las_mejores:
        num = gestionar_cupo_semanal() + 1
        par_txt = sel['par_binance'] if sel['par_binance'] else f"{sel['token_symbol']} (Fallback)"
        
        mensaje = (
            f"💎 *MEJOR ENTRADA SEMANAL #{num} (Top 4)*\n"
            f"🕒 *Analizado el:* `{ahora_str}`\n\n"
            f"*1. IDENTIFICACIÓN Y PERFIL:*\n"
            f"• *Empresa:* `{sel['nombre_empresa']}` (`{sel['ticker']}`)\n"
            f"• *Token Binance:* `{par_txt}`\n"
            f"• *Dinámica del Movimiento:* `{sel['dinamica']}`\n"
            f"• *Puntuación de Calidad:* `{sel['score_tecnico']}/100`\n\n"
            f"*2. CONDICIONES DE MERCADO:*\n"
            f"• *Sentimiento Global:* `{sentimiento}`\n"
            f"• *Estacionalidad Histórica:* `{sel['estacionalidad']}`\n"
            f"• *Corrección Actual:* `-{sel['descuento']}%` | *RSI:* `{sel['rsi']}`\n\n"
            f"*3. ESTRUCTURA DE ENTRADA:*\n"
            f"• *Precio Actual:* `${sel['precio']}`\n"
            f"• *Zona de Compra Sugerida:* `{sel['rango_entrada']}`\n"
            f"• *Soporte Institucional:* `{sel['soporte']}`\n\n"
            f"*4. GESTIÓN DE RIESGO Y OBJETIVOS (2:1):*\n"
            f"🎯 *Take-Profit (+{sel['pct_tp']}%):* `${sel['take_profit']}` (3× ATR)\n"
            f"🛑 *Stop-Loss (-{sel['pct_sl']}%):* `${sel['stop_loss']}` (1.5× ATR)\n"
            f"⏱️ *Horizonte Estimado:* `{sel['tiempo_estimado']}`\n\n"
            f"*5. INFORMACIÓN CORPORATIVA Y MODELO DE NEGOCIO:*\n"
            f"🏢 [Haz clic aquí para ver a qué se dedica la empresa]({sel['link_perfil']})\n"
            f"📈 [Ver gráfico y análisis técnico en TradingView]({sel['link_grafico']})\n\n"
            f"*6. TESIS CUANTITATIVA:*\n"
            f"💡 Confluencia de sobreventa agotada en `{sel['soporte']}` con mecha de absorción institucional y ratio riesgo/beneficio asimétrico 2.0:1."
        )
        enviar_alerta_telegram(mensaje)
        registrar_alerta(sel['ticker'])
        registrar_posicion_activa(sel)
        registrar_en_excel(sel)

    print(f"\nProceso finalizado. Registros guardados en '{ARCHIVO_EXCEL}'.")


if __name__ == "__main__":
    ejecutar_filtro_semanal()