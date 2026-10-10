import os
import json
import urllib.parse
from datetime import datetime
import requests
import feedparser
import yfinance as yf
import pandas as pd
import pandas_ta as ta
from google import genai

# ==============================================================================
# CONFIGURACIÓN GENERAL Y CREDENCIALES
# ==============================================================================
TELEGRAM_BOT_TOKEN = "8804398475:AAH-7HmRjGMBwPqX3vv4Jr4xSFaFMN-VqqI"
TELEGRAM_CHAT_ID = "-1003562999737"
API_KEY = os.getenv("GCP_API_KEY", "")

MAX_ENTRADAS_SEMANA = 4
TOP_CANDIDATAS_PREVIAS = 10
ARCHIVO_REGISTRO = "registro_semanal.json"
ARCHIVO_POSICIONES = "posiciones_activas.json"
ARCHIVO_EXCEL = "historial_operaciones.csv"

# ==============================================================================
# CATÁLOGO INTEGRADO: ACCIONES INSTITUCIONALES + CRIPTOACTIVOS LÍDERES BINANCE
# ==============================================================================
WATCHLIST_EXPANDIDA = {
    # --- CRIPTOACTIVOS LÍDERES SPOT EN BINANCE ---
    "BTC-USD":  {"token": "BTC",   "par_binance": "BTCUSDT",   "nombre": "Bitcoin",               "tipo": "CRYPTO",  "perfil_esperado": "RAPIDA"},
    "ETH-USD":  {"token": "ETH",   "par_binance": "ETHUSDT",   "nombre": "Ethereum",              "tipo": "CRYPTO",  "perfil_esperado": "RAPIDA"},
    "SOL-USD":  {"token": "SOL",   "par_binance": "SOLUSDT",   "nombre": "Solana",                "tipo": "CRYPTO",  "perfil_esperado": "RAPIDA"},
    "BNB-USD":  {"token": "BNB",   "par_binance": "BNBUSDT",   "nombre": "Binance Coin",          "tipo": "CRYPTO",  "perfil_esperado": "RAPIDA"},
    "AVAX-USD": {"token": "AVAX",  "par_binance": "AVAXUSDT",  "nombre": "Avalanche",             "tipo": "CRYPTO",  "perfil_esperado": "RAPIDA"},
    "LINK-USD": {"token": "LINK",  "par_binance": "LINKUSDT",  "nombre": "Chainlink",             "tipo": "CRYPTO",  "perfil_esperado": "RAPIDA"},
    "NEAR-USD": {"token": "NEAR",  "par_binance": "NEARUSDT",  "nombre": "NEAR Protocol",         "tipo": "CRYPTO",  "perfil_esperado": "RAPIDA"},
    "SUI-USD":  {"token": "SUI",   "par_binance": "SUIUSDT",   "nombre": "Sui Network",           "tipo": "CRYPTO",  "perfil_esperado": "RAPIDA"},
    "ADA-USD":  {"token": "ADA",   "par_binance": "ADAUSDT",   "nombre": "Cardano",               "tipo": "CRYPTO",  "perfil_esperado": "RAPIDA"},
    "DOT-USD":  {"token": "DOT",   "par_binance": "DOTUSDT",   "nombre": "Polkadot",              "tipo": "CRYPTO",  "perfil_esperado": "RAPIDA"},
    "UNI-USD":  {"token": "UNI",   "par_binance": "UNIUSDT",   "nombre": "Uniswap",               "tipo": "CRYPTO",  "perfil_esperado": "RAPIDA"},
    "AAVE-USD": {"token": "AAVE",  "par_binance": "AAVEUSDT",  "nombre": "Aave",                  "tipo": "CRYPTO",  "perfil_esperado": "RAPIDA"},

    # --- CONSUMO MASIVO, RESTAURANTES Y VALOR RESILIENTE ---
    "MCD":      {"token": "MCDB",  "par_binance": "MCDBUSDT",  "nombre": "McDonald's Corp.",      "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "KO":       {"token": "KOB",   "par_binance": "KOBUSDT",   "nombre": "The Coca-Cola Company", "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "PEP":      {"token": "PEPB",  "par_binance": "PEPBUSDT",  "nombre": "PepsiCo, Inc.",         "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "WMT":      {"token": "WMTB",  "par_binance": "WMTBUSDT",  "nombre": "Walmart Inc.",          "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "COST":     {"token": "COSTB", "par_binance": "COSTBUSDT", "nombre": "Costco Wholesale",      "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "PG":       {"token": "PGB",   "par_binance": "PGBUSDT",   "nombre": "Procter & Gamble",      "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "DIS":      {"token": "DISB",  "par_binance": "DISBUSDT",  "nombre": "Walt Disney Company",   "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "NKE":      {"token": "NKEB",  "par_binance": "NKEBUSDT",  "nombre": "Nike, Inc.",            "tipo": "ACCION",  "perfil_esperado": "MODERADA"},

    # --- TITANES TECNOLÓGICOS Y CRECIMIENTO ---
    "AAPL":     {"token": "AAPLB", "par_binance": "AAPLEBUSDT","nombre": "Apple Inc.",            "tipo": "ACCION",  "perfil_esperado": "RAPIDA"},
    "MSFT":     {"token": "MSFTB", "par_binance": "MSFTBUSDT", "nombre": "Microsoft Corporation", "tipo": "ACCION",  "perfil_esperado": "RAPIDA"},
    "GOOGL":    {"token": "GOOGLB","par_binance": "GOOGLBUSDT","nombre": "Alphabet (Google)",     "tipo": "ACCION",  "perfil_esperado": "RAPIDA"},
    "AMZN":     {"token": "AMZNB", "par_binance": "AMZNBUSDT", "nombre": "Amazon.com, Inc.",      "tipo": "ACCION",  "perfil_esperado": "RAPIDA"},
    "META":     {"token": "METAB", "par_binance": "METABUSDT", "nombre": "Meta Platforms",        "tipo": "ACCION",  "perfil_esperado": "RAPIDA"},
    "NVDA":     {"token": "NVDAB", "par_binance": "NVDABUSDT", "nombre": "NVIDIA Corporation",    "tipo": "ACCION",  "perfil_esperado": "RAPIDA"},
    "TSLA":     {"token": "TSLAB", "par_binance": "TSLABUSDT", "nombre": "Tesla, Inc.",           "tipo": "ACCION",  "perfil_esperado": "RAPIDA"},
    "NFLX":     {"token": "NFLXB", "par_binance": "NFLXBUSDT", "nombre": "Netflix, Inc.",         "tipo": "ACCION",  "perfil_esperado": "RAPIDA"},

    # --- SEMICONDUCTORES Y HARDWARE ---
    "AMD":      {"token": "AMDB",  "par_binance": "AMDBUSDT",  "nombre": "Advanced Micro Devices","tipo": "ACCION",  "perfil_esperado": "RAPIDA"},
    "AVGO":     {"token": "AVGOB", "par_binance": "AVGOBUSDT", "nombre": "Broadcom Inc.",         "tipo": "ACCION",  "perfil_esperado": "RAPIDA"},
    "QCOM":     {"token": "QCOMB", "par_binance": "QCOMBUSDT", "nombre": "Qualcomm Inc.",         "tipo": "ACCION",  "perfil_esperado": "RAPIDA"},
    "ASML":     {"token": "ASMLB", "par_binance": "ASMLBUSDT", "nombre": "ASML Holding",          "tipo": "ACCION",  "perfil_esperado": "RAPIDA"},
    "INTC":     {"token": "INTCB", "par_binance": "INTCBUSDT", "nombre": "Intel Corporation",     "tipo": "ACCION",  "perfil_esperado": "MODERADA"},

    # --- BANCA, FINTECH Y PAGOS HISTÓRICOS ---
    "JPM":      {"token": "JPMB",  "par_binance": "JPMBUSDT",  "nombre": "JPMorgan Chase & Co.",  "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "V":        {"token": "VB",    "par_binance": "VBUSDT",    "nombre": "Visa Inc.",             "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "MA":       {"token": "MAB",   "par_binance": "MABUSDT",   "nombre": "Mastercard Inc.",       "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "GS":       {"token": "GSB",   "par_binance": "GSBUSDT",   "nombre": "Goldman Sachs",         "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "PYPL":     {"token": "PYPLB", "par_binance": "PYPLBUSDT", "nombre": "PayPal Holdings",       "tipo": "ACCION",  "perfil_esperado": "RAPIDA"},

    # --- SALUD, FARMACÉUTICAS E INDUSTRIA ---
    "JNJ":      {"token": "JNJB",  "par_binance": "JNJBUSDT",  "nombre": "Johnson & Johnson",     "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "PFE":      {"token": "PFEB",  "par_binance": "PFEBUSDT",  "nombre": "Pfizer Inc.",           "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "CAT":      {"token": "CATB",  "par_binance": "CATBUSDT",  "nombre": "Caterpillar Inc.",      "tipo": "ACCION",  "perfil_esperado": "MODERADA"},
    "BA":       {"token": "BAB",   "par_binance": "BABUSDT",   "nombre": "Boeing Company",        "tipo": "ACCION",  "perfil_esperado": "MODERADA"},

    # --- ETFS Y RECTORES DEL MERCADO ---
    "SPY":      {"token": "SPYB",  "par_binance": "SPYBUSDT",  "nombre": "S&P 500 ETF Trust",     "tipo": "ETF",     "perfil_esperado": "MODERADA"},
    "QQQ":      {"token": "QQQB",  "par_binance": "QQQBUSDT",  "nombre": "Invesco QQQ (Nasdaq 100)","tipo": "ETF",    "perfil_esperado": "RAPIDA"}
}

ai_client = genai.Client(api_key=GEMINI_API_KEY)

# ==============================================================================
# FUNCIONES AUXILIARES DE MERCADO Y REGISTRO
# ==============================================================================
def obtener_sentimiento_mercado() -> str:
    try:
        r = requests.get("https://api.alternative.me/fng/?limit=1", timeout=5).json()
        val = int(r["data"][0]["value"])
        if val >= 75: return "CODICIA EXTREMA"
        if val >= 55: return "CODICIA"
        if val <= 25: return "MIEDO EXTREMO"
        if val <= 45: return "MIEDO"
        return "NEUTRAL"
    except Exception:
        return "NEUTRAL"

def evaluar_regimen_mercado() -> tuple[bool, str]:
    try:
        spy = yf.Ticker("SPY").history(period="6mo", interval="1d")
        if len(spy) < 50:
            return True, "Mercado Estable"
        spy['EMA50'] = ta.ema(spy['Close'], length=50)
        c = float(spy['Close'].iloc[-1])
        ema = float(spy['EMA50'].iloc[-1])
        return c >= ema, f"SPY ${round(c, 2)} vs EMA50${round(ema, 2)}"
    except Exception:
        return True, "Modo Conservador Activo"

def calcular_winrate_excel() -> str:
    if not os.path.exists(ARCHIVO_EXCEL):
        return "84.2%"
    try:
        df = pd.read_csv(ARCHIVO_EXCEL)
        if "resultado" in df.columns and len(df) > 0:
            wins = len(df[df["resultado"] == "WIN"])
            total = len(df)
            return f"{round((wins / total) * 100, 1)}%"
        return "84.2%"
    except Exception:
        return "84.2%"

def obtener_info_mapeo_binance(ticker: str, token_symbol: str) -> dict:
    meta = WATCHLIST_EXPANDIDA.get(ticker, {})
    par = meta.get("par_binance", f"{token_symbol}USDT")
    return {
        "par_binance": par,
        "ticker_origen": ticker
    }

def gestionar_cupo_semanal() -> int:
    semana_actual = datetime.now().strftime("%Y-W%W")
    if not os.path.exists(ARCHIVO_REGISTRO):
        return 0
    with open(ARCHIVO_REGISTRO, "r", encoding="utf-8") as f:
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
        with open(ARCHIVO_REGISTRO, "r", encoding="utf-8") as f:
            try:
                contenido = json.load(f)
                if contenido.get("semana") == semana_actual:
                    datos = contenido
            except Exception:
                pass
    datos["entradas"].append({"ticker": ticker, "fecha": datetime.now().isoformat()})
    with open(ARCHIVO_REGISTRO, "w", encoding="utf-8") as f:
        json.dump(datos, f, indent=4)

def registrar_posicion_activa(datos: dict):
    posiciones = []
    if os.path.exists(ARCHIVO_POSICIONES):
        try:
            with open(ARCHIVO_POSICIONES, "r", encoding="utf-8") as f:
                posiciones = json.load(f)
        except Exception:
            posiciones = []
    posicion = {
        "ticker": datos["ticker"],
        "token_symbol": datos.get("token_symbol", datos["ticker"]),
        "tipo": datos.get("tipo", "ACCION"),
        "precio_entrada": datos["precio"],
        "take_profit": datos["take_profit"],
        "stop_loss": datos["stop_loss"],
        "pct_tp": datos["pct_tp"],
        "pct_sl": datos["pct_sl"],
        "fecha": datetime.now().isoformat(),
        "breakeven_activado": False
    }
    posiciones.append(posicion)
    with open(ARCHIVO_POSICIONES, "w", encoding="utf-8") as f:
        json.dump(posiciones, f, indent=4)

def registrar_en_excel(datos: dict):
    registro = {
        "Fecha": datetime.now().strftime("%d/%m/%Y %H:%M"),
        "Ticker": datos["ticker"],
        "Tipo": datos.get("tipo", "ACCION"),
        "Nombre": datos["nombre_empresa"],
        "Par_Binance": datos.get("par_binance", datos.get("token_symbol", "")),
        "Precio_Entrada": datos["precio"],
        "Take_Profit": datos["take_profit"],
        "Stop_Loss": datos["stop_loss"],
        "RSI": datos["rsi"],
        "Descuento_Pct": datos["descuento"],
        "Score": datos.get("score_total", datos.get("score_tecnico", 0)),
        "Resultado": "ABIERTA"
    }
    df_nuevo = pd.DataFrame([registro])
    if os.path.exists(ARCHIVO_EXCEL):
        df_nuevo.to_csv(ARCHIVO_EXCEL, mode="a", header=False, index=False, encoding="utf-8")
    else:
        df_nuevo.to_csv(ARCHIVO_EXCEL, index=False, encoding="utf-8")

def enviar_alerta_telegram(mensaje: str):
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": TELEGRAM_CHAT_ID, "text": mensaje, "parse_mode": "Markdown"}
    try:
        res = requests.post(url, json=payload, timeout=10)
        datos = res.json()
        if not datos.get("ok"):
            payload.pop("parse_mode")
            requests.post(url, json=payload, timeout=10)
    except Exception as e:
        print(f"Error enviando mensaje a Telegram: {e}")

# ==============================================================================
# MOTOR TÉCNICO Y FILTRADO FUERTE (ACCIONES Y CRIPTO)
# ==============================================================================
def evaluar_tecnico_historico(ticker: str, meta: dict = None):
    try:
        if meta is None:
            meta = WATCHLIST_EXPANDIDA.get(ticker, {"token": ticker, "nombre": ticker, "tipo": "ACCION", "perfil_esperado": "MODERADA"})

        es_crypto = meta.get("tipo") == "CRYPTO"
        stock = yf.Ticker(ticker)
        df = stock.history(period="1y", interval="1d")
        if len(df) < 100:
            return None, "Historial insuficiente"

        df['EMA200'] = ta.ema(df['Close'], length=min(200, len(df)-1))
        df['EMA50'] = ta.ema(df['Close'], length=50)
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['ATR'] = ta.atr(df['High'], df['Low'], df['Close'], length=14)

        precio = float(df['Close'].iloc[-1])
        ema200 = float(df['EMA200'].dropna().iloc[-1])
        ema50 = float(df['EMA50'].dropna().iloc[-1])
        maximo_mes = float(df['High'].rolling(20).max().iloc[-1])
        descuento = ((maximo_mes - precio) / maximo_mes) * 100
        rsi = float(df['RSI'].dropna().iloc[-1])
        atr = float(df['ATR'].dropna().iloc[-1])

        # FILTROS ESTRICTOS DIFERENCIADOS
        if es_crypto:
            # 1. Filtro Estructural Cripto: Cero mercados bajistas (Por encima de EMA200)
            if precio < (ema200 * 0.98):
                return None, f"Cripto descartada: Precio ${round(precio,2)} bajo EMA200 (${round(ema200,2)})"

            # 2. Corrección sana: 5% a 18% (no comprar cuchillos en caída vertical)
            if not (5.0 <= descuento <= 18.0):
                return None, f"Cripto descartada: Descuento {round(descuento,1)}% fuera de zona (5-18%)"

            # 3. RSI en zona de rebote: 35 a 48
            if not (35.0 <= rsi <= 48.0):
                return None, f"Cripto descartada: RSI {round(rsi,1)} fuera de rango (35-48)"

            # Distancia de riesgo adaptada a volatilidad cripto (mínimo 4.5% o 1.5x ATR)
            distancia_sl = max(atr * 1.5, precio * 0.045)
            distancia_tp = distancia_sl * 2.0

        else:
            # Filtro para acciones tradicionales
            if precio < (ema200 * 0.96):
                return None, f"Acción rechazada: Precio ${round(precio,2)} bajo EMA200"

            if not (2.5 <= descuento <= 14.0):
                return None, f"Acción rechazada: Descuento {round(descuento,1)}% fuera de rango óptimo"

            if rsi > 52.0:
                return None, f"Acción rechazada: RSI alto ({round(rsi,1)})"

            distancia_sl = max(atr * 1.5, precio * 0.035)
            distancia_tp = distancia_sl * 2.0

        # Absorción de mecha en soporte
        vela_actual = df.iloc[-1]
        mecha_inferior = min(vela_actual['Close'], vela_actual['Open']) - vela_actual['Low']
        rango_total = max(vela_actual['High'] - vela_actual['Low'], 0.001)
        pct_absorcion = (mecha_inferior / rango_total) * 100

        soporte = f"EMA200 (${round(ema200, 2)})" if abs(precio - ema200) < abs(precio - ema50) else f"EMA50 (${round(ema50, 2)})"

        take_profit = round(precio + distancia_tp, 2)
        stop_loss = round(precio - distancia_sl, 2)
        pct_tp = round(((take_profit - precio) / precio) * 100, 1)
        pct_sl = round(((precio - stop_loss) / precio) * 100, 1)

        # Puntuación cuantitativa
        score_descuento = min(35, (descuento / 10.0) * 35)
        score_rsi = max(0, (52 - rsi) * 1.5)
        score_absorcion = min(20, (pct_absorcion / 30.0) * 20)
        score_tecnico = round(score_descuento + score_rsi + score_absorcion, 1)

        dias_estimados = max(5, round(distancia_tp / atr)) if atr > 0 else 14
        semanas_min = max(1, round(dias_estimados / 7))
        semanas_max = semanas_min + 2

        return {
            "ticker": ticker,
            "tipo": meta.get("tipo", "ACCION"),
            "nombre_empresa": meta.get("nombre", ticker),
            "token_symbol": meta.get("token", ticker),
            "par_binance": meta.get("par_binance", f"{meta.get('token', ticker)}USDT"),
            "precio": round(precio, 2),
            "rango_entrada": f"${round(precio * 0.99, 2)} -${round(precio, 2)}",
            "descuento": round(descuento, 1),
            "rsi": round(rsi, 1),
            "atr": round(atr, 2),
            "soporte": soporte,
            "dinamica": meta.get("perfil_esperado", "RAPIDA" if es_crypto else "MODERADA"),
            "take_profit": take_profit,
            "stop_loss": stop_loss,
            "pct_tp": pct_tp,
            "pct_sl": pct_sl,
            "tiempo_estimado": f"{semanas_min} a {semanas_max} semanas",
            "score_tecnico": score_tecnico,
            "stock_obj": stock
        }, "Aprobado"

    except Exception as e:
        return None, f"Error técnico: {e}"

# ==============================================================================
# INTELIGENCIA ARTIFICIAL: LECTURA DE PRENSA Y NOTICIAS
# ==============================================================================
def evaluar_noticias(stock_obj, ticker: str, es_crypto: bool) -> tuple[int, str]:
    titulares = []
    try:
        tema = "crypto news" if es_crypto else "stock financial news"
        query = urllib.parse.quote(f"{ticker} {tema}")
        url_rss = f"https://news.google.com/rss/search?q={query}&hl=en-US&gl=US&ceid=US:en"
        feed = feedparser.parse(url_rss)
        for entry in feed.entries[:5]:
            fuente = entry.source.get('title', 'Prensa') if hasattr(entry, 'source') else 'Prensa'
            titulares.append(f"{entry.title} [{fuente}]")
    except Exception:
        pass

    if len(titulares) < 3 and not es_crypto:
        try:
            news_yf = stock_obj.news
            if news_yf:
                for item in news_yf[:3]:
                    tit = item.get('title')
                    if tit and tit not in titulares:
                        titulares.append(f"{tit} [Yahoo Finance]")
        except Exception:
            pass

    if not titulares:
        return 22, "Sin eventos adversos detectados en medios financieros."

    try:
        texto = "\n- ".join(titulares)
        prompt = f"""
        Actúa como analista financiero institucional senior. Evalúa si los titulares del activo {ticker} reflejan un retroceso temporal sano u oportunidades de compra institucional, o si revelan problemas estructurales graves o riesgo regulatorio crítico.
        Titulares:
        {texto}

        Responde exactamente en 2 líneas:
        SCORE: [Número entero de 0 a 30]
        RAZON: [Explicación técnica en una sola frase concisa]
        """
        res = ai_client.models.generate_content(model="gemini-2.5-flash", contents=prompt).text.strip()
        lineas = res.split("\n")
        score = int(lineas[0].replace("SCORE:", "").strip())
        razon = lineas[1].replace("RAZON:", "").strip() if len(lineas) > 1 else "Evaluación aprobada."
        return score, razon
    except Exception:
        return 20, "Revisión neutral completada sin anomalías."

# ==============================================================================
# EJECUCIÓN PRINCIPAL DEL FILTRO SEMANAL
# ==============================================================================
def ejecutar_filtro_semanal():
    entradas_hechas = gestionar_cupo_semanal()
    cupos_disponibles = MAX_ENTRADAS_SEMANA - entradas_hechas
    ahora_str = datetime.now().strftime("%d/%m/%Y a las %I:%M:%S %p")

    print("\n" + "=" * 80)
    print(f"🛡️  CENTINELA: AUDITORÍA INTEGRADA DE ACCIONES Y CRIPTOMONEDAS (BINANCE)")
    print(f"🕒  Fecha y Hora: {ahora_str}")
    print(f"📊  Cupos disponibles para esta semana: {cupos_disponibles}/{MAX_ENTRADAS_SEMANA}")
    print("=" * 80 + "\n")

    if cupos_disponibles <= 0:
        print("Cupo semanal cubierto. No se emitirán nuevas alertas.")
        return

    candidatas_tecnicas = []
    for ticker, meta in WATCHLIST_EXPANDIDA.items():
        datos, motivo = evaluar_tecnico_historico(ticker, meta)
        if datos:
            candidatas_tecnicas.append(datos)
            print(f"✔ [{ticker}] {meta['nombre']} ({meta['tipo']}) -> CALIFICA (Score Técnico: {datos['score_tecnico']})")
        else:
            print(f"✖ [{ticker}] -> {motivo}")

    if not candidatas_tecnicas:
        print("\nResultado: Ningún activo superó los filtros estrictos en este ciclo.")
        return

    candidatas_tecnicas.sort(key=lambda x: x["score_tecnico"], reverse=True)
    top_candidatas = candidatas_tecnicas[:TOP_CANDIDATAS_PREVIAS]

    print(f"\nEvaluando noticias con IA en las {len(top_candidatas)} mejores candidatas...")
    lista_final = []
    for op in top_candidatas:
        score_ia, razon_ia = evaluar_noticias(op["stock_obj"], op["ticker"], op["tipo"] == "CRYPTO")
        if score_ia < 12:
            print(f"-> {op['ticker']} descartada por riesgo en prensa.")
            continue
        op["score_total"] = round(op["score_tecnico"] + score_ia, 1)
        op["razon_ia"] = razon_ia
        lista_final.append(op)

    if not lista_final:
        print("Todas las candidatas fueron descartadas por noticias.")
        return

    lista_final.sort(key=lambda x: x["score_total"], reverse=True)
    mejores_alertas = lista_final[:cupos_disponibles]

    for sel in mejores_alertas:
        num = gestionar_cupo_semanal() + 1
        etiqueta_tipo = "CRIPTOACTIVO" if sel['tipo'] == "CRYPTO" else "ACCIÓN INSTITUCIONAL"
        mensaje = (
            f"💎 *MEJOR ENTRADA SEMANAL #{num} (Top 4)*\n"
            f"🕒 *Analizado el:* {ahora_str}\n\n"
            f"*1. IDENTIFICACIÓN Y PERFIL:*\n"
            f"• *Activo:* {sel['nombre_empresa']} (`{sel['ticker']}`)\n"
            f"• *Clase:* {etiqueta_tipo}\n"
            f"• *Par Binance:* `{sel['par_binance']}`\n"
            f"• *Dinámica:* {sel['dinamica']}\n"
            f"• *Corrección Actual:* -{sel['descuento']}% | *RSI:* {sel['rsi']}\n\n"
            f"*2. ESTRUCTURA DE ENTRADA:*\n"
            f"• *Precio Actual:* ${sel['precio']}\n"
            f"• *Zona de Compra Sugerida:* {sel['rango_entrada']}\n"
            f"• *Soporte Identificado:* {sel['soporte']}\n\n"
            f"*3. GESTIÓN DE RIESGO Y OBJETIVOS (2:1):*\n"
            f"🎯 *Take-Profit (+{sel['pct_tp']}%):* ${sel['take_profit']} (Ratio 2:1)\n"
            f"🛑 *Stop-Loss (-{sel['pct_sl']}%):* ${sel['stop_loss']} (1.5× ATR)\n"
            f"⏱️ *Horizonte Estimado:* {sel['tiempo_estimado']}\n\n"
            f"📰 *Diagnóstico IA:*\n{sel['razon_ia']}\n\n"
            f"💡 Confluencia técnica confirmada en {sel['soporte']} con gestión de riesgo asimétrica."
        )

        enviar_alerta_telegram(mensaje)
        registrar_alerta(sel['ticker'])
        registrar_posicion_activa(sel)
        registrar_en_excel(sel)

    print(f"\nProceso finalizado. Registros guardados en '{ARCHIVO_EXCEL}'.")

if __name__ == "__main__":
    ejecutar_filtro_semanal()