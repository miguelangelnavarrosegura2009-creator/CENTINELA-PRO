import os
import json
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import centinela_semanal as bot

app = FastAPI(
    title="Centinela Trading API",
    description="Backend oficial con soporte de historial y auditoría técnica",
    version="1.2.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

HISTORIAL_PERSISTENTE = "historial_entradas_app.json"

def cargar_historial():
    if os.path.exists(HISTORIAL_PERSISTENTE):
        try:
            with open(HISTORIAL_PERSISTENTE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []

def guardar_historial(lista):
    with open(HISTORIAL_PERSISTENTE, "w", encoding="utf-8") as f:
        json.dump(lista, f, indent=4, ensure_ascii=False)

@app.get("/")
def estado_servidor():
    return {
        "status": "online",
        "servicio": "Centinela Stock Engine",
        "version": "1.2.0"
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
    Escanea el mercado. Si encuentra nuevas entradas aprobadas, las agrega
    al historial persistente para que nunca se pierdan ni se repitan.
    """
    historial = cargar_historial()
    tickers_registrados = {item["ticker"] for item in historial}

    candidatas = []
    for ticker, meta in bot.WATCHLIST_EXPANDIDA.items():
        datos, motivo = bot.evaluar_tecnico_historico(ticker, meta)
        if datos:
            info_b = bot.obtener_info_mapeo_binance(ticker, meta.get("token", ticker))
            datos["token_symbol"] = meta.get("token", ticker)
            datos["par_binance"] = info_b.get("par_binance")
            datos["fecha_deteccion"] = datetime.now().strftime("%d/%m/%Y %I:%M %p")
            datos.pop("stock_obj", None)
            candidatas.append(datos)

    if candidatas:
        candidatas.sort(key=lambda x: x.get("score_tecnico", 0), reverse=True)
        # Añadir al historial solo las nuevas que no estuvieran ya registradas
        for nueva in candidatas[:bot.MAX_ENTRADAS_SEMANA]:
            if nueva["ticker"] not in tickers_registrados:
                historial.insert(0, nueva)
                tickers_registrados.add(nueva["ticker"])
        
        # Mantener las últimas 50 entradas históricas
        historial = historial[:50]
        guardar_historial(historial)

    return {
        "total": len(historial),
        "entradas": historial
    }

@app.get("/historial")
def ver_historial_operaciones():
    """Devuelve el historial del archivo CSV/Excel de operaciones."""
    if not os.path.exists(bot.ARCHIVO_EXCEL):
        return {"operaciones": []}
    try:
        df = pd.read_csv(bot.ARCHIVO_EXCEL)
        df = df.fillna("")
        return {"operaciones": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))