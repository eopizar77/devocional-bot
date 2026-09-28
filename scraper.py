import os
import re
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from google import genai
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def a_emojis_numeros(num):
    mapa = {
        '0': '0️⃣', '1': '1️⃣', '2': '2️⃣', '3': '3️⃣', '4': '4️⃣',
        '5': '5️⃣', '6': '6️⃣', '7': '7️⃣', '8': '8️⃣', '9': '9️⃣'
    }
    return ''.join(mapa.get(d, d) for d in str(num))

def obtener_devocional_y_imagen():
    url = "https://soyict.org/devocional/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    response = requests.get(url, headers=headers, verify=False)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    content = soup.find('div', class_='entry-content') or soup.find('article') or soup.find('body')
    
    textos = []
    if content:
        for p in content.find_all(['p', 'h1', 'h2', 'h3']):
            t = p.get_text().strip()
            if t and "Ver Devocional" not in t and "Guía" not in t:
                textos.append(t)
    
    img_url = None
    for a in soup.find_all('a'):
        if a.text and 'Guía del mes' in a.text:
            img_url = a.get('href')
            break
            
    return textos, img_url

def parsear_contenido_web(textos):
    titulo = "EN LA PRESENCIA DE DIOS"
    biblico = ""
    complementario = ""
    devocional_raw = ""
    oracion = ""
    
    for t in textos:
        t_clean = t.strip()
        if not t_clean or t_clean.startswith("Fecha:"):
            continue
        elif t_clean.startswith("Bíblico:"):
            biblico = t_clean.replace("Bíblico:", "").strip()
        elif t_clean.startswith("Complementario:"):
            complementario = t_clean.replace("Complementario:", "").strip()
        elif t_clean.startswith("Devocional:"):
            devocional_raw = t_clean.replace("Devocional:", "").strip()
        elif t_clean.startswith("Oremos:"):
            oracion = t_clean.replace("Oremos:", "").strip()
        else:
            if not biblico and not devocional_raw:
                titulo = t_clean

    return titulo, biblico, complementario, devocional_raw, oracion

def formatear_parrafos_con_ia_o_fallback(texto_devocional, api_key):
    """
    Formatea cada párrafo con un emoji temático al inicio y al final.
    Intenta primero con Gemini; si está ocupado (503), usa un fallback inteligente.
    """
    if not texto_devocional:
        return ""
        
    if api_key:
        try:
            client = genai.Client(api_key=api_key)
            prompt = f"""Actúa como un editor devocional para WhatsApp.
Toma el siguiente texto devocional y realiza lo siguiente:
1. Mantén TODO el contenido 100% completo, sin resumir ni omitir ideas o detalles.
2. Divide el texto en 3 a 5 párrafos bien estructurados.
3. Para CADA párrafo, colócale al inicio un emoji temático y contextual, luego abre con asterisco (*), coloca el texto completo del párrafo, cierra con asterisco (*) y coloca al final otro emoji temático y contextual.
Ejemplo:
👑*Texto del párrafo...*🔥

Texto:
{texto_devocional}

Devuelve ÚNICAMENTE los párrafos formateados, separados por doble salto de línea:"""

            for modelo in ['gemini-3.1-flash-lite', 'gemini-3.8-flash']:
                try:
                    res = client.models.generate_content(model=modelo, contents=prompt)
                    if res and res.text:
                        return res.text.strip()
                except Exception:
                    continue
        except Exception as e:
            print("Gemini ocupado para formatear texto, aplicando fallback:", e)

    # Fallback inteligente en Python (siempre garantiza texto completo con emojis temáticos)
    oraciones = re.split(r'(?<=[.!?])\s+', texto_devocional)
    tam_parrafo = 3
    grupos = [oraciones[i:i + tam_parrafo] for i in range(0, len(oraciones), tam_parrafo)]
    
    pares_emojis = [
        ("👑", "🔥"),
        ("✝️", "⚰️"),
        ("📖", "🕯️"),
        ("🙏", "✋"),
        ("🕊️", "✨"),
        ("🌿", "🏪")
    ]
    
    parrafos_formateados = []
    for idx, grupo in enumerate(grupos):
        parrafo_texto = " ".join(grupo).strip()
        if not parrafo_texto:
            continue
        emoji_ini, emoji_fin = pares_emojis[idx % len(pares_emojis)]
        parrafos_formateados.append(f"{emoji_ini}*{parrafo_texto}*{emoji_fin}")
        
    return "\n\n".join(parrafos_formateados)

def extraer_porciones_con_ia(img_url, fecha_hoy_texto, api_key):
    if not img_url:
        return "Guía bíblica disponible en el canal."
        
    if api_key:
        try:
            img_data = requests.get(img_url, verify=False).content
            from google.genai import types
            
            client = genai.Client(api_key=api_key)
            prompt = f"Busca en esta imagen la fecha de {fecha_hoy_texto}. Extrae la lectura o lecturas bíblicas correspondientes a este día y devuélvelas exactamente con este formato:\n📖 [Lectura 1]\n✍🏽 [Lectura 2]\n🛐  [Lectura 3]"
            
            for modelo in ['gemini-3.1-flash-lite', 'gemini-3.8-flash']:
                try:
                    response = client.models.generate_content(
                        model=modelo,
                        contents=[
                            prompt,
                            types.Part.from_bytes(data=img_data, mime_type='image/jpeg')
                        ]
                    )
                    if response and response.text:
                        return response.text.strip()
                except Exception:
                    continue
        except Exception as e:
            print("Error al leer imagen con Gemini:", e)
            
    return f"📖 Guía del mes: {img_url}"

def obtener_ultimo_video(youtube_api_key):
    try:
        if youtube_api_key:
            channel_id = "UC023hX0ppaxW8GflnfvNcTg" # @SoyICT
            url_vids = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={channel_id}&order=date&type=video&maxResults=1&key={youtube_api_key}"
            r = requests.get(url_vids)
            data = r.json()
            if 'items' in data and len(data['items']) > 0:
                vid_id = data['items'][0]['id']['videoId']
                titulo = data['items'][0]['snippet']['title']
                return titulo, f"https://youtu.be/{vid_id}"
    except Exception as e:
        print("Error obteniendo video de YouTube:", e)
        
    return "Teoterapia y Meditación", "https://www.youtube.com/@SoyICT"

def enviar_whatsapp(mensaje):
    id_instance = os.environ.get('GREEN_INSTANCE')
    api_token = os.environ.get('GREEN_TOKEN')
    group_id = "573142306674@c.us"
    
    url = f"https://api.green-api.com/waInstance{id_instance}/sendMessage/{api_token}"
    payload = {
        "chatId": group_id,
        "message": mensaje
    }
    r = requests.post(url, json=payload)
    print("Estado del envío a WhatsApp:", r.status_code, r.text)

def main():
    gemini_key = os.environ.get("GEMINI_API_KEY")
    youtube_key = os.environ.get("YOUTUBE_API_KEY")
    
    # 1. Obtener datos de la web
    textos, img_url = obtener_devocional_y_imagen()
    titulo_web, biblico, complementario, devocional_raw, oracion = parsear_contenido_web(textos)
    
    # 2. Formatear la reflexión completa con emojis al inicio y al final de cada párrafo
    reflexion_formateada = formatear_parrafos_con_ia_o_fallback(devocional_raw, gemini_key)
    
    # 3. Fechas dinámicas
    meses = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']
    dias_semana = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    
    hoy = datetime.now()
    mes_nombre = meses[hoy.month - 1]
    dia_emojis = a_emojis_numeros(hoy.day)
    dia_semana_nombre = dias_semana[hoy.weekday()]
    
    fecha_encabezado = f"{dia_emojis} DE {mes_nombre}. {hoy.year}"
    fecha_texto_plano = f"{hoy.day} de {mes_nombre.lower()} {hoy.year}"
    
    # 4. Obtener video de YouTube
    titulo_video, url_video = obtener_ultimo_video(youtube_key)
    
    # 5. Obtener porciones bíblicas de la imagen con IA
    porciones_biblicas = extraer_porciones_con_ia(img_url, f"{hoy.day} de {mes_nombre.lower()}", gemini_key)
    
    # 6. Ensamblaje del mensaje completo
    mensaje_final = f"""😇 *{fecha_encabezado}, EL AÑO DE LA INTELIGENCIA ESPIRITUAL* 🙏🏽

📖 {titulo_web}. Mañana 5️⃣ am hr 🇨🇴 aprenderemos cómo *Dios nos guía y bendice*.
{url_video}

👳🏾 *{titulo_web.upper()}* 🗣️

📕 *Pasaje bíblico:*

🛣️🏪 *“{biblico}”*

📘 *Pasajes complementarios:* {complementario}

{reflexion_formateada}

🙇🏾 *Oremos*😇

🙇🏾😇 *"{oracion}"*

📘 *TOMADO DEL LIBRO DEVOCIONAL EN CASA CON DIOS, DEL DR. JIMMY CHAMORRO CRUZ*🧑🏾💼

🎧 {url_video}

😍 *Por Amor a Israel y a Jerusalén* 🇮🇱🕌

🌿🇮🇱 *Paz sea a Israel, y pedid por la paz de Jerusalén.*
🙏🏽🌿🏪 *Mas os gozaréis y os alegraréis para siempre en las cosas que yo he creado; porque he aquí que yo traigo a Jerusalén alegría, y a su pueblo gozo. Y me alegraré con Jerusalén, y me gozaré con mi pueblo; y nunca más se oirán en ella voz de lloro, ni voz de clamor.* Isaias 65:18-19

🤓 *{fecha_texto_plano}* 📖
*La Provisión Bíblica Diaria.*

{porciones_biblicas}

🎧 {url_video}

👋🏽 *Saludos de Gratitud* 🙏🏽

😇👍🏽 *El Señor te guarde y bendiga en este hermoso día y su presencia te acompañe en todo momento y veas su gloria en todo lo que emprendas.*
🥰🤝🏼 *Un afectuoso abrazo para una persona a quien aprecio mucho; te deseo un feliz {dia_semana_nombre}*.👍🏽🌇"""

    print("--- MENSAJE FINAL COMPLETO GENERADO ---")
    enviar_whatsapp(mensaje_final)

if __name__ == "__main__":
    main()
