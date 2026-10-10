import os
import json
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
import centinela_semanal as bot

app = FastAPI(
    title="Centinela Trading API",
    description="Backend oficial con soporte de historial, actualización OTA y fichas de Telegram",
    version="1.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HISTORIAL_FILE = "historial_entradas_app.json"
VERSION_ACTUAL = "1.0.1"
URL_DESCARGA_DIRECTA = "https://github.com/miguelangelnavarrosegura2009-creator/CENTINELA-PRO/releases/latest"

def cargar_historial():
    if os.path.exists(HISTORIAL_FILE):
        try:
            with open(HISTORIAL_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def guardar_historial(entradas):
    try:
        with open(HIST/versionORIAL_FILE, "w", encoding="utf-8") as f:
            json.dump(entradas, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error guardando historial: {e}")

@app.get("/")
def estado_servidor():
    return {
        "status": "online",
        "servicio": "Centinela Stock Engine",
        "version": VERSION_ACTUAL
    }

@app.get("/descargar-apk")
def descargar_apk():
    ruta_apk = "app-release.apk"
    if os.path.exists(ruta_apk):
        return FileResponse(
            ruta_apk,
            filename="CentinelaPro.apk",
            media_type="application/vnd.android.package-archive"
        )
    raise HTTPException(status_code=404, detail="Archivo APK no encontrado en el servidor")

@app.get("/version")
def consultar_version():
    return {
        "version": "1.0.2",
        "url_descarga": "https://centinela-pro-dopr.onrender.com/descargar-apk",
        "novedades": "Fichas tecnicas completas e historial persistente."
    }

@app.get("/mercado")
def estado_mercado():
    sentimiento = bot.obtener_sentimiento_mercado()
    macro_ok, detalle_macro = bot.evaluar_regimen_mercado()
    winrate = bot.calcular_winrate_excel()

    return {
        "sentimiento_fear_greed": sentimiento,
        "macro_favorable": macro_ok,
        "macro_detalle": detalle_macro,
        "winrate_historico": winrate
    }

@app.get("/entradas")
def obtener_entradas_activas():
    """
    Escanea la watchlist, genera la ficha completa tipo Telegram y
    almacena en historial persistente sin duplicar tickers.
    """
    historial = cargar_historial()
    tickers_en_historial = {item.get("ticker") for item in historial}

    candidatas = []
    for ticker, meta in bot.WATCHLIST_EXPANDIDA.items():
        try:
            datos, motivo = bot.evaluar_tecnico_historico(ticker, meta)
            if datos:
                info_b = bot.obtener_info_mapeo_binance(ticker, meta.get("token", ticker))
                datos["token_symbol"] = meta.get("token", ticker)
                datos["par_binance"] = info_b.get("par_binance")
                datos["fecha_deteccion"] = datetime.now().strftime("%d/%m/%Y %I:%M %p")
                datos.pop("stock_obj", None)
                candidatas.append(datos)
        except Exception as e:
            print(f"Error analizando {ticker}: {e}")

    # Ordenar y agregar las mejores al historial evitando duplicados
    if candidatas:
        candidatas.sort(key=lambda x: x.get("score_tecnico", 0), reverse=True)
        nuevas = 0
        for candidata in candidatas[:bot.MAX_ENTRADAS_SEMANA]:
            if candidata["ticker"] not in tickers_en_historial:
                historial.insert(0, candidata)
                tickers_en_historial.add(candidata["ticker"])
                nuevas += 1
        
        if nuevas > 0:
            historial = historial[:50]  # Conservar las últimas 50
            guardar_historial(historial)

    return {
        "total": len(historial),
        "entradas": historial
    }

@app.get("/historial")
def ver_historial_operaciones():
    if not os.path.exists(bot.ARCHIVO_EXCEL):
        return {"operaciones": []}
    try:
        df = pd.read_csv(bot.ARCHIVO_EXCEL)
        df = df.fillna("")
        return {"operaciones": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))