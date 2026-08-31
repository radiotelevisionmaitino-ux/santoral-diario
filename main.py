import asyncio
import datetime
import random
import re
import unicodedata
import requests
import edge_tts

MONTH_URLS = {
    1: "https://archive.org/download/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20ENERO.txt",
    2: "https://archive.org/download/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20FEBRERO.txt",
    3: "https://archive.org/download/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20MARZO.txt",
    4: "https://archive.org/download/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20ABRIL.txt",
    5: "https://archive.org/download/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20MAYO.txt",
    6: "https://archive.org/download/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20JUNIO.txt",
    7: "https://archive.org/download/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20JULIO.txt",
    8: "https://archive.org/download/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20AGOSTO.txt",
    9: "https://archive.org/download/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20SEPTIEMBRE.txt",
    10: "https://archive.org/download/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20OCTUBRE.txt",
    11: "https://archive.org/download/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20NOVIEMBRE.txt",
    12: "https://archive.org/download/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20DICIEMBRE.txt",
}

INTROS = [
    "Saludos a todos. Hoy es {dia_nombre}, {dia_num} de {mes_nombre} de {anio}, y comenzamos nuestro boletín diario repasando el santoral de la jornada.",
    "Muy buenos días. En este {dia_nombre}, {dia_num} de {mes_nombre} del año {anio}, abrimos el espacio dedicado a la memoria de los santos que la Iglesia honra hoy.",
    "Bienvenidos a la edición de hoy. Estamos a {dia_nombre}, {dia_num} de {mes_nombre} de {anio}, momento perfecto para repasar las festividades de nuestra fe."
]

CIERRES = [
    "Con esto cerramos nuestro boletín del santoral de hoy. Que tengan una bendecida jornada y nos escuchamos mañana.",
    "Hasta aquí el repaso de las vidas ejemplares de esta jornada. Les deseamos un feliz día y nos reencontramos en la próxima emisión.",
    "Así concluimos el boletín de hoy. Que el testimonio de los santos les acompañe en sus actividades. ¡Hasta mañana!"
]

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

def normalizar_texto(texto):
    """Elimina tildes, caracteres raros y convierte a minúsculas para comparaciones precisas."""
    return ''.join(c for c in unicodedata.normalize('NFD', texto) if unicodedata.category(c) != 'Mn').lower()

def obtener_texto_dia(fecha):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        url = MONTH_URLS[fecha.month]
        resp = requests.get(url, headers=headers, timeout=20)
        
        content = resp.content
        text = ""
        for enc in ['utf-8', 'latin-1', 'cp1252']:
            try:
                text = content.decode(enc)
                break
            except UnicodeDecodeError:
                continue

        if not text:
            text = content.decode('utf-8', errors='ignore')

        dia_actual = fecha.day
        dia_siguiente = dia_actual + 1
        mes_nombre = MESES[fecha.month - 1]

        lineas = text.splitlines()
        capturando = False
        lineas_extraidas = []

        for linea in lineas:
            linea_str = linea.strip()
            if not linea_str:
                continue
            
            norm = normalizar_texto(linea_str)

            # Detecta marcas como "DIA 31", "31 DE AGOSTO", "31.", "31.-"
            es_hoy = (
                f"dia {dia_actual}" in norm or 
                f"{dia_actual} de {mes_nombre}" in norm or 
                re.search(rf"\b{dia_actual}\s*[\.\-\:]", norm) or
                norm.startswith(f"{dia_actual} ")
            )

            # Detecta el inicio del día siguiente para detener la lectura
            es_siguiente = (
                f"dia {dia_siguiente}" in norm or 
                f"{dia_siguiente} de {mes_nombre}" in norm or 
                re.search(rf"\b{dia_siguiente}\s*[\.\-\:]", norm) or
                norm.startswith(f"{dia_siguiente} ")
            )

            if capturando:
                if es_siguiente:
                    break
                lineas_extraidas.append(linea_str)
            else:
                if es_hoy:
                    capturando = True
                    # Extrae el texto tras el número si el titular incluye contenido
                    sub_linea = re.sub(rf"^(?:D[ÍI]A\s+)?{dia_actual}(?:[A-Z\s]+)?[\.\-\:\s]+", "", linea_str, flags=re.IGNORECASE).strip()
                    if len(sub_linea) > 10 and not sub_linea.lower().startswith("de "):
                        lineas_extraidas.append(sub_linea)

        resultado = " ".join(lineas_extraidas).strip()
        resultado = re.sub(r'\s+', ' ', resultado)

        if len(resultado) > 30:
            if len(resultado) > 950:
                resultado = resultado[:950].rsplit('.', 1)[0] + '.'
            return resultado

        # Fallback de escaneo global si la lectura por líneas no encuentra separadores estándar
        norm_full = normalizar_texto(text)
        pat_start = rf"(?:dia\s+{dia_actual}\b|\b{dia_actual}\s+de\s+{mes_nombre}|\b{dia_actual}\s*[\.\-])"
        m_start = re.search(pat_start, norm_full)
        if m_start:
            idx_start = m_start.end()
            pat_end = rf"(?:dia\s+{dia_siguiente}\b|\b{dia_siguiente}\s+de\s+{mes_nombre}|\b{dia_siguiente}\s*[\.\-])"
            m_end = re.search(pat_end, norm_full[idx_start:])
            
            bloque = text[idx_start : idx_start + m_end.start()] if m_end else text[idx_start : idx_start + 1200]
            bloque = re.sub(r'\s+', ' ', bloque).strip()
            
            if len(bloque) > 30:
                if len(bloque) > 950:
                    bloque = bloque[:950].rsplit('.', 1)[0] + '.'
                return bloque

    except Exception as e:
        print(f"Error procesando el santoral: {e}")

    return f"En este día honramos y recordamos la memoria de los santos y bienaventurados correspondientes a esta jornada."

async def generar_audio(texto, archivo_salida="santoral-hoy.mp3"):
    try:
        communicate = edge_tts.Communicate(texto, "es-ES-AlvaroNeural")
        await communicate.save(archivo_salida)
        print("Audio MP3 generado con éxito.")
    except Exception as e:
        print(f"Error en voz Edge-TTS: {e}")

def main():
    hoy = datetime.date.today()
    dia_nom = DIAS[hoy.weekday()]
    mes_nom = MESES[hoy.month - 1]

    intro = random.choice(INTROS).format(dia_nombre=dia_nom, dia_num=hoy.day, mes_nombre=mes_nom, anio=hoy.year)
    cierre = random.choice(CIERRES)
    cuerpo = obtener_texto_dia(hoy)

    texto_audio = f"{intro} {cuerpo} {cierre}"
    
    asyncio.run(generar_audio(texto_audio, "santoral-hoy.mp3"))

    ts = int(datetime.datetime.now().timestamp())

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Santoral Diario - {dia_nom.capitalize()} {hoy.day} de {mes_nom}</title>
  <style>
    :root {{
      --primary: #1e293b;
      --accent: #d97706;
      --bg: #f1f5f9;
      --card-bg: #ffffff;
      --text: #334155;
      --border: #e2e8f0;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: system-ui, -apple-system, sans-serif;
      background-color: var(--bg);
      color: var(--text);
      line-height: 1.7;
      padding: 40px 20px;
      display: flex;
      justify-content: center;
      align-items: center;
      min-height: 100vh;
    }}
    .card {{
      background: var(--card-bg);
      max-width: 650px;
      width: 100%;
      border-radius: 16px;
      box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.05);
      padding: 32px;
      border: 1px solid var(--border);
    }}
    h1 {{ color: var(--primary); font-size: 1.6rem; margin-bottom: 4px; }}
    .fecha {{ font-size: 0.9rem; color: #64748b; margin-bottom: 20px; text-transform: capitalize; }}
    audio {{ width: 100%; margin: 16px 0 24px 0; border-radius: 8px; outline: none; }}
    .intro {{ font-weight: 600; color: var(--primary); margin-bottom: 16px; font-size: 1.05rem; }}
    .cuerpo {{ margin-bottom: 20px; font-size: 1rem; color: var(--text); }}
    .cierre {{ font-style: italic; color: var(--accent); font-weight: 500; margin-top: 16px; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Santoral del Día</h1>
    <div class="fecha">{dia_nom}, {hoy.day} de {mes_nom} de {hoy.year}</div>
    <audio controls autoplay src="santoral-hoy.mp3?v={ts}"></audio>
    <p class="intro">{intro}</p>
    <p class="cuerpo">{cuerpo}</p>
    <p class="cierre">{cierre}</p>
  </div>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print("index.html actualizado.")

if __name__ == "__main__":
    main()
