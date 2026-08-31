import asyncio
import datetime
import random
import re
import requests
import edge_tts

MONTH_URLS = {
    1: "https://ia600400.us.archive.org/2/items/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20ENERO.txt",
    2: "https://ia600400.us.archive.org/2/items/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20FEBRERO.txt",
    3: "https://ia600400.us.archive.org/2/items/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20MARZO.txt",
    4: "https://ia600400.us.archive.org/2/items/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20ABRIL.txt",
    5: "https://ia600400.us.archive.org/2/items/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20MAYO.txt",
    6: "https://ia600400.us.archive.org/2/items/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20JUNIO.txt",
    7: "https://ia600400.us.archive.org/2/items/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20JULIO.txt",
    8: "https://ia600400.us.archive.org/2/items/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20AGOSTO.txt",
    9: "https://ia600400.us.archive.org/2/items/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20SEPTIEMBRE.txt",
    10: "https://ia600400.us.archive.org/2/items/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20OCTUBRE.txt",
    11: "https://ia600400.us.archive.org/2/items/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20NOVIEMBRE.txt",
    12: "https://ia600400.us.archive.org/2/items/santoral-diciembre/SANTORALES%20TEXTO/SANTORAL%20DICIEMBRE.txt",
}

INTROS = [
    "Saludos a todos. Hoy es {dia_nombre}, {dia_num} de {mes_nombre} de {anio}, y comenzamos nuestro boletín diario repasando el santoral de la jornada.",
    "Muy buenos días. En este {dia_nombre}, {dia_num} de {mes_nombre} del año {anio}, abrimos el espacio dedicado a la memoria de los santos que la Iglesia honra hoy."
]

CIERRES = [
    "Con esto cerramos nuestro boletín del santoral de hoy. Que tengan una bendecida jornada y nos escuchamos mañana.",
    "Hasta aquí el repaso de las vidas ejemplares de esta jornada. Les deseamos un feliz día y nos reencontramos en la próxima emisión."
]

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]

def obtener_texto_dia(fecha):
    url = MONTH_URLS[fecha.month]
    resp = requests.get(url)
    resp.encoding = 'utf-8'
    text = resp.text
    
    patron_dia = rf"(?:DÍA\s+{fecha.day}\b|\b{fecha.day}\s+DE\s+{MESES[fecha.month-1].upper()})"
    patron_sig = rf"(?:DÍA\s+{fecha.day+1}\b|\b{fecha.day+1}\s+DE\s+{MESES[fecha.month-1].upper()})"
    
    m_inc = re.search(patron_dia, text, re.IGNORECASE)
    if not m_inc:
        return "Lectura del santoral no disponible para hoy."
    
    inc = m_inc.end()
    m_sig = re.search(patron_sig, text[inc:], re.IGNORECASE)
    return text[inc:inc+m_sig.start()].strip() if m_sig else text[inc:].strip()

async def generar_audio(texto, archivo_salida="santoral-hoy.mp3"):
    communicate = edge_tts.Communicate(texto, "es-ES-AlvaroNeural")
    await communicate.save(archivo_salida)

def main():
    hoy = datetime.date.today()
    dia_nom = DIAS[hoy.weekday()]
    mes_nom = MESES[hoy.month - 1]

    intro = random.choice(INTROS).format(dia_nombre=dia_nom, dia_num=hoy.day, mes_nombre=mes_nom, anio=hoy.year)
    cierre = random.choice(CIERRES)
    cuerpo = obtener_texto_dia(hoy)

    asyncio.run(generar_audio(f"{intro} {cuerpo} {cierre}", "santoral-hoy.mp3"))

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
  <meta charset="UTF-8">
  <title>Santoral del Día</title>
  <style>
    body {{ font-family: system-ui, sans-serif; background: #f1f5f9; padding: 20px; display: flex; justify-content: center; }}
    .card {{ background: white; padding: 24px; border-radius: 12px; max-width: 600px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
    audio {{ width: 100%; margin: 15px 0; }}
  </style>
</head>
<body>
  <div class="card">
    <h1>Santoral - {dia_nom.capitalize()}, {hoy.day} de {mes_nom}</h1>
    <audio controls autoplay src="santoral-hoy.mp3?v={int(datetime.datetime.now().timestamp())}"></audio>
    <p><strong>{intro}</strong></p>
    <p>{cuerpo}</p>
    <p><em>{cierre}</em></p>
  </div>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)

if __name__ == "__main__":
    main()
