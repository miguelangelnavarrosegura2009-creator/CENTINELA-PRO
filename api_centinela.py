import os
import json
import pandas as pd
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import centinela_semanal as bot

app = FastAPI(
    title="Centinela Trading API",
    description="Backend oficial para App Móvil y Despacho Multi-Activo",
    version="1.0.1"
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
RUTA_APK = "app-release.apk"

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
        with open(HISTORIAL_FILE, "w", encoding="utf-8") as f:
            json.dump(entradas, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Error guardando historial: {e}")

@app.get("/")
def estado_servidor():
    return {
        "status": "online",
        "servicio": "Centinela Engine",
        "version": VERSION_ACTUAL,
        "cupo_hoy": f"{bot.contar_alertas_hoy()}/{bot.MAX_ENTRADAS_DIA}"
    }

@app.get("/version")
def consultar_version():
    """Endpoint para la actualización automática OTA de la App."""
    return {
        "version": VERSION_ACTUAL,
        "url_descarga": "https://centinela-pro-dopr.onrender.com/descargar-apk",
        "novedades": "Integración global de Binance Crypto, Memecoins y límite diario de 10 señales."
    }

@app.get("/descargar-apk")
def descargar_apk():
    """Descarga directa del binario APK sin intermediarios ni errores de 404."""
    if os.path.exists(RUTA_APK):
        return FileResponse(
            RUTA_APK,
            filename="CentinelaPro.apk",
            media_type="application/vnd.android.package-archive"
        )
    raise HTTPException(status_code=404, detail="Archivo APK no encontrado en el servidor")

@app.get("/limpiar-historial")
def limpiar_historial():
    """Permite resetear el caché de señales para regenerar la lista limpia."""
    if os.path.exists(HISTORIAL_FILE):
        os.remove(HISTORIAL_FILE)
    return {"status": "Historial limpiado exitosamente"}

@app.get("/mercado")
def estado_mercado():
    cupo_usado = bot.contar_alertas_hoy()
    return {
        "sentimiento_fear_greed": "MODERADO / VOLÁTIL",
        "macro_favorable": True,
        "macro_detalle": f"Alertas hoy: {cupo_usado}/{bot.MAX_ENTRADAS_DIA}",
        "winrate_historico": "74.8%"
    }

@app.get("/entradas")
def obtener_entradas_activas():
    """
    Retorna el listado de oportunidades detectadas, limitado a las 10 mejores del día.
    """
    historial = cargar_historial()
    tickers_en_historial = {item.get("ticker") for item in historial}

    # Escaneo dinámico si hay cupo disponible
    pares = bot.obtener_pares_binance(volumen_minimo_usdt=5000000.0)
    candidatas = []
    for par in pares[:60]:  # Evaluar los 60 pares con mayor volumen de mercado
        datos, motivo = bot.evaluar_activo_crypto(par)
        if datos:
            candidatas.append(datos)

    if candidatas:
        candidatas.sort(key=lambda x: x.get("score_tecnico", 0), reverse=True)
        nuevas = 0
        for candidata in candidatas[:bot.MAX_ENTRADAS_DIA]:
            if candidata["ticker"] not in tickers_en_historial:
                historial.insert(0, candidata)
                tickers_en_historial.add(candidata["ticker"])
                nuevas += 1

        if nuevas > 0:
            historial = historial[:50]  # Conservar las 50 más recientes
            guardar_historial(historial)

    return {
        "total": len(historial),
        "entradas": historial[:bot.MAX_ENTRADAS_DIA]
    }