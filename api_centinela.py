import os
import pandas as pd
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import centinela_semanal as bot

app = FastAPI(
    title="Centinela Trading API",
    description="Backend oficial para alimentar la app Android de Centinela",
    version="1.0.0"
)

# Permite que la app móvil se conecte sin bloqueos de red
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def estado_servidor():
    """Ruta de prueba de conexión."""
    return {
        "status": "online",
        "servicio": "Centinela Stock Engine",
        "version": "1.0.0"
    }

@app.get("/mercado")
def estado_mercado():
    """Devuelve el sentimiento de mercado y el régimen del S&P 500."""
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
    """Devuelve las mejores 4 entradas calculadas para mostrar en la app."""
    candidatas = []
    for ticker, meta in bot.WATCHLIST_EXPANDIDA.items():
        datos, motivo = bot.evaluar_tecnico_historico(ticker, meta)
        if datos:
            info_b = bot.obtener_info_mapeo_binance(ticker, meta["token"])
            datos["token_symbol"] = meta["token"]
            datos["par_binance"] = info_b.get("par_binance")
            candidatas.append(datos)

    if not candidatas:
        return {"total": 0, "entradas": []}

    candidatas.sort(key=lambda x: x["score_tecnico"], reverse=True)
    mejores_4 = candidatas[:bot.MAX_ENTRADAS_SEMANA]

    # Limpiar objetos no serializables si existieran
    for item in mejores_4:
        item.pop("stock_obj", None)

    return {
        "total": len(mejores_4),
        "entradas": mejores_4
    }

@app.get("/analizar/{ticker}")
def auditar_activo_especifico(ticker: str):
    """Permite a la app móvil auditar cualquier acción bajo demanda."""
    ticker_clean = ticker.upper().strip()
    meta = bot.WATCHLIST_EXPANDIDA.get(ticker_clean, {"nombre": ticker_clean, "token": f"{ticker_clean}B", "perfil_esperado": "RAPIDA"})
    
    datos, motivo = bot.evaluar_tecnico_historico(ticker_clean, meta)
    if not datos:
        return {
            "aprobada": False,
            "ticker": ticker_clean,
            "motivo_descarte": motivo
        }

    datos.pop("stock_obj", None)
    return {
        "aprobada": True,
        "detalles": datos
    }

@app.get("/historial")
def ver_historial_operaciones():
    """Lee el archivo CSV/Excel y devuelve las operaciones registradas a la app."""
    if not os.path.exists(bot.ARCHIVO_EXCEL):
        return {"operaciones": []}
    try:
        df = pd.read_csv(bot.ARCHIVO_EXCEL)
        df = df.fillna("")
        return {"operaciones": df.to_dict(orient="records")}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))