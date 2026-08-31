import asyncio
import datetime
import os
import random
import subprocess
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

# URLs de la música de fondo (URL canónica + espejo directo)
BG_MUSIC_URLS = [
    "https://archive.org/download/maitino-rec-master-1788189527411/MAITINO_REC_MASTER_1788189527411.webm",
    "https://ia800403.us.archive.org/18/items/maitino-rec-master-1788189527411/MAITINO_REC_MASTER_1788189527411.webm"
]

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

        prefijo = f"[{fecha.day:02d}]"

        for linea in text.splitlines():
            linea_str = linea.strip()
            if linea_str.startswith(prefijo):
                cuerpo = linea_str[len(prefijo):].strip()

                # Limitar a ~500 caracteres para asegurar que la locución dure ~35s
                # y sumados los 6s de intro musical + 4s de cierre no supere 1m 15s.
                if len(cuerpo) > 500:
                    sub_c = cuerpo[:500]
                    if '.' in sub_c:
                        cuerpo = sub_c.rsplit('.', 1)[0] + '.'
                    else:
                        cuerpo = sub_c.rsplit(' ', 1)[0] + '.'
                return cuerpo

        print(f"No se encontró la línea con el prefijo {prefijo}")

    except Exception as e:
        print(f"Error procesando el santoral: {e}")

    return "Hoy honramos y recordamos la memoria de los santos de esta jornada."

async def generar_audio_voz(texto, archivo_salida="voice_temp.mp3"):
    try:
        communicate = edge_tts.Communicate(texto, "es-ES-AlvaroNeural")
        await communicate.save(archivo_salida)
        print("Voz TTS generada correctamente.")
    except Exception as e:
        print(f"Error en voz Edge-TTS: {e}")

def descargar_musica_fondo(archivo_destino="bg_music.webm"):
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
    for url in BG_MUSIC_URLS:
        try:
            print(f"Intentando descargar música desde: {url}")
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code == 200 and len(resp.content) > 1000:
                with open(archivo_destino, "wb") as f:
                    f.write(resp.content)
                print("Música de fondo descargada con éxito.")
                return True
        except Exception as e:
            print(f"Fallo descarga desde {url}: {e}")
    return False

def mezclar_audio_con_musica(archivo_voz="voice_temp.mp3", archivo_salida="santoral-hoy.mp3"):
    bg_file = "bg_music.webm"
    
    if not descargar_musica_fondo(bg_file):
        print("No se pudo obtener la música de fondo. Se deja solo el audio de voz.")
        if os.path.exists(archivo_voz):
            if os.path.exists(archivo_salida):
                os.remove(archivo_salida)
            os.rename(archivo_voz, archivo_salida)
        return

    # 1. Obtener la duración exacta de la voz
    duracion_voz = 40.0
    try:
        cmd_probe = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprintwrappers=1:nokey=1", archivo_voz]
        res = subprocess.run(cmd_probe, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, check=True)
        duracion_voz = float(res.stdout.strip())
        print(f"Duración real de la voz: {duracion_voz:.2f} segundos.")
    except Exception as e:
        print(f"Error obteniendo duración de voz: {e}")

    # Entrada de voz a los 6s + duración voz + 4s de cola de música
    duracion_calculada = 6.0 + duracion_voz + 4.0
    # Límite máximo estricto: 75 segundos (1 minuto 15 segundos)
    duracion_total = min(duracion_calculada, 75.0)
    inicio_fade = max(duracion_total - 4.0, 6.0 + duracion_voz)

    print(f"Duración final del boletín: {duracion_total:.2f}s (Fade out a los {inicio_fade:.2f}s)")

    # 2. Mezcla profesional con FFmpeg
    filter_complex = (
        f"[0:a]volume=1.2,adelay=6000|6000[voz];"
        f"[1:a]volume=0.18[musica];"
        f"[voz][musica]amix=inputs=2:duration=longest:dropout_transition=2:normalize=0,"
        f"atrim=0:{duracion_total:.2f},"
        f"afade=t=out:st={inicio_fade:.2f}:d=4[outa]"
    )

    try:
        cmd_ffmpeg = [
            "ffmpeg", "-y",
            "-i", archivo_voz,
            "-i", bg_file,
            "-filter_complex", filter_complex,
            "-map", "[outa]",
            "-c:a", "libmp3lame",
            "-b:a", "192k",
            archivo_salida
        ]
        res = subprocess.run(cmd_ffmpeg, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if res.returncode != 0:
            print(f"Error en FFmpeg: {res.stderr}")
            raise Exception("FFmpeg devolvió error")
            
        print(f"¡Audio procesado y mezclado con éxito!: {archivo_salida}")
    except Exception as e:
        print(f"Error durante la mezcla: {e}. Se aplica fallback de voz directa.")
        if os.path.exists(archivo_voz):
            if os.path.exists(archivo_salida):
                os.remove(archivo_salida)
            os.rename(archivo_voz, archivo_salida)
    finally:
        if os.path.exists(bg_file):
            os.remove(bg_file)
        if os.path.exists(archivo_voz):
            os.remove(archivo_voz)

def main():
    hoy = datetime.date.today()
    dia_nom = DIAS[hoy.weekday()]
    mes_nom = MESES[hoy.month - 1]

    intro = random.choice(INTROS).format(dia_nombre=dia_nom, dia_num=hoy.day, mes_nombre=mes_nom, anio=hoy.year)
    cierre = random.choice(CIERRES)
    cuerpo = obtener_texto_dia(hoy)

    texto_audio = f"{intro} {cuerpo} {cierre}"
    
    archivo_temp_voz = "voice_temp.mp3"
    asyncio.run(generar_audio_voz(texto_audio, archivo_temp_voz))
    mezclar_audio_con_musica(archivo_temp_voz, "santoral-hoy.mp3")

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
    print("index.html generado correctamente.")

if __name__ == "__main__":
    main()
