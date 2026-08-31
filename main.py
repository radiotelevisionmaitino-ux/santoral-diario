import asyncio
import datetime
import random
import re
import requests
import edge_tts

# URLs directas canónicas (sin nodos de servidor caducos)
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

def obtener_texto_dia(fecha):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    try:
        url = MONTH_URLS[fecha.month]
        resp = requests.get(url, headers=headers, timeout=20)
        resp.raise_for_status()
        
        # Detectar codificación correcta para evitar caracteres extraños
        resp.encoding = resp.apparent_encoding if resp.apparent_encoding else 'latin-1'
        text = resp.text

        dia = fecha.day
        mes_nombre = MESES[fecha.month - 1]

        # Expresiones regulares adaptadas a las variantes del archivo de texto
        patrones_dia = [
            rf"D[ÍI]A\s+{dia}\b",
            rf"\b{dia}\s+DE\s+{mes_nombre}\b",
            rf"\b{dia}\s*\.\s*-",
            rf"\b{dia}\s*\.",
            rf"^\s*{dia}\b"
        ]

        inc = None
        for pat in patrones_dia:
            m = re.search(pat, text, re.IGNORECASE | re.MULTILINE)
            if m:
                inc = m.end()
                break

        if inc is None:
            print(f"No se encontró la marca del día {dia} en el texto.")
            return f"Hoy celebramos las festividades de los santos correspondientes a este día {dia} de {mes_nombre}."

        # Buscar el inicio del día siguiente (si no es fin de mes)
        fin = None
        sig_dia = dia + 1
        patrones_sig = [
            rf"D[ÍI]A\s+{sig_dia}\b",
            rf"\b{sig_dia}\s+DE\s+{mes_nombre}\b",
            rf"\b{sig_dia}\s*\.\s*-",
            rf"\b{sig_dia}\s*\.",
            rf"^\s*{sig_dia}\b"
        ]

        for pat in patrones_sig:
            m_sig = re.search(pat, text[inc:], re.IGNORECASE | re.MULTILINE)
            if m_sig:
                fin = inc + m_sig.start()
                break

        cuerpo = text[inc:fin].strip() if fin else text[inc:].strip()
        cuerpo = re.sub(r'\s+', ' ', cuerpo)

        # Ajuste de longitud para radio si el bloque es muy extenso
        if len(cuerpo) > 1000:
            cuerpo = cuerpo[:1000].rsplit('.', 1)[0] + '.'

        return cuerpo if len(cuerpo) > 20 else f"Hoy honramos la memoria de los santos y bienaventurados del día."

    except Exception as e:
        print(f"Error descargando o procesando el santoral: {e}")
        return "Hoy honramos y recordamos la memoria de los santos de esta jornada."

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
