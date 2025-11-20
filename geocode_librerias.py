import time
import json
import requests
import pandas as pd
from tqdm import tqdm  # solo para ver barra de progreso

# === CONFIGURACIÓN ===
EXCEL_PATH = "Librerias_Azuay_SRI_RUC.xlsx"   # nombre del archivo excel
SHEET_NAME = 0  # 0 = primera hoja; cámbialo si tu hoja tiene otro nombre
OUTPUT_JSON = "librerias_azuay_geocoded.json"

# Coordenadas de respaldo por cantón (por si falla la geocodificación)
CANTON_COORDS = {
    "CUENCA": (-2.9001, -79.0059),
    "SAN FERNANDO": (-3.2167, -79.3500),
    "GUALACEO": (-2.8925, -78.7789),
    "CHORDELEG": (-2.8700, -78.7500),
    "GIRON": (-3.1589, -79.1467),
    "SIGSIG": (-3.0700, -78.8167),
    "SANTA ISABEL": (-3.2667, -79.1000),
    "NABON": (-3.3333, -79.0833),
    "OÑA": (-3.3333, -79.1333),
}

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
HEADERS = {
    # IMPORTANTE: pon tu correo en el User-Agent para respetar la política de Nominatim
    "User-Agent": "ProyectoLibreriasAzuay/1.0 (tu_correo@ejemplo.com)"
}


def normalizar_canton(x: str) -> str:
    if not isinstance(x, str):
        return ""
    x2 = x.strip().upper()
    if "OÃ" in x2 or "O�" in x2:  # por si viene roto el texto de OÑA
        return "OÑA"
    return x2


def geocode(nombre, canton):
    """
    Devuelve (lat, lng) usando Nominatim.
    Si no encuentra nada, retorna (None, None)
    """
    query = f"{nombre}, {canton}, Azuay, Ecuador"
    params = {
        "q": query,
        "format": "json",
        "limit": 1,
        "addressdetails": 0
    }

    try:
        resp = requests.get(NOMINATIM_URL, params=params, headers=HEADERS, timeout=15)
        if resp.status_code != 200:
            return None, None

        data = resp.json()
        if not data:
            return None, None

        lat = float(data[0]["lat"])
        lng = float(data[0]["lon"])
        return lat, lng

    except Exception as e:
        print("Error geocodificando:", e)
        return None, None


def main():
    df = pd.read_excel(EXCEL_PATH, sheet_name=SHEET_NAME)

    df["CANTON_NORM"] = df["DESCRIPCION_CANTON_EST"].apply(normalizar_canton)

    resultados = []
    ok_geo = 0
    ok_fallback = 0
    fail = 0

    for _, row in tqdm(df.iterrows(), total=len(df), desc="Geocodificando"):
        ruc = str(row.get("NUMERO_RUC", ""))
        razon = str(row.get("RAZON_SOCIAL", ""))
        canton = row.get("CANTON_NORM", "")
        actividad = str(row.get("ACTIVIDAD_ECONOMICA", ""))

        lat, lng = geocode(razon, canton)

        if lat is not None and lng is not None:
            ok_geo += 1
        else:
            # si falla, usar coordenada central del cantón (fallback)
            if canton in CANTON_COORDS:
                lat, lng = CANTON_COORDS[canton]
                ok_fallback += 1
            else:
                fail += 1
                lat, lng = None, None

        resultados.append({
            "ruc": ruc,
            "razon_social": razon,
            "canton": canton,
            "actividad": actividad,
            "lat": lat,
            "lng": lng
        })

        # MUY IMPORTANTE: Nominatim recomienda 1 seg entre peticiones
        time.sleep(1)

    print(f"\nGeocodificados con Nominatim: {ok_geo}")
    print(f"Con coordenada de respaldo (centro de cantón): {ok_fallback}")
    print(f"Sin coordenadas: {fail}")

    # Filtrar solo filas con coordenadas válidas
    resultados_validos = [
        r for r in resultados if r["lat"] is not None and r["lng"] is not None
    ]

    with open(OUTPUT_JSON, "w", encoding="utf-8") as f:
        json.dump(resultados_validos, f, ensure_ascii=False, indent=2)

    print(f"\nJSON guardado en: {OUTPUT_JSON}")
    print(f"Registros con coords: {len(resultados_validos)}")


if __name__ == "__main__":
    main()
