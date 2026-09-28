import os
import requests
from bs4 import BeautifulSoup
from datetime import datetime
from google import genai
import json
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def obtener_devocional_y_imagen():
    url = "https://soyict.org/devocional/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    # Bypassing SSL just in case
    response = requests.get(url, headers=headers, verify=False)
    soup = BeautifulSoup(response.text, 'html.parser')
    
    content = soup.find('div', class_='entry-content') or soup.find('article') or soup.find('body')
    
    # Extraer textos principales (título, versículos base, devocional, oración)
    textos = []
    if content:
        for p in content.find_all(['p', 'h1', 'h2', 'h3']):
            text = p.get_text().strip()
            if text and "Ver Devocional" not in text and "Guía" not in text:
                textos.append(text)
    
    # Extraer el link de la imagen de la Guía del Mes
    img_url = None
    for a in soup.find_all('a'):
        if a.text and 'Guía del mes' in a.text:
            img_url = a.get('href')
            break
            
    return textos, img_url

def extraer_porciones_con_ia(img_url, fecha_hoy_texto):
    """
    Usa la IA de Gemini para leer la imagen y extraer los versículos del día.
    """
    if not img_url:
        return "No se encontró la imagen de la guía del mes."
        
    try:
        # Descargamos la imagen temporalmente
        img_data = requests.get(img_url, verify=False).content
        
        # En el nuevo SDK genai, usamos types.Part.from_bytes para enviar la imagen sin guardarla
        from google.genai import types
        
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        
        prompt = f"Busca en esta imagen la fecha de {fecha_hoy_texto}. Extrae la lectura o lecturas bíblicas correspondientes a este día y devuélvelas exactamente con este formato (usa los mismos emojis si los hay, o estos por defecto):\n📖 [Lectura 1]\n✍🏽 [Lectura 2]\n🛐 [Lectura 3]\n\nSi no encuentras lecturas para el día de hoy, indica 'Lectura del día no encontrada'."
        
        response = client.models.generate_content(
            model='gemini-3.8-flash',
            contents=[
                prompt,
                types.Part.from_bytes(
                    data=img_data,
                    mime_type='image/jpeg',
                )
            ]
        )
        return response.text
    except Exception as e:
        print("Error al usar Gemini:", e)
        return f"Guía del mes: {img_url}" # Si falla la IA, devolvemos el link de la imagen

def obtener_ultimo_video():
    try:
        api_key = os.environ.get("YOUTUBE_API_KEY")
        channel_id = "UC023hX0ppaxW8GflnfvNcTg" # ID de @SoyICT
        url_vids = f"https://www.googleapis.com/youtube/v3/search?part=snippet&channelId={channel_id}&order=date&type=video&maxResults=1&key={api_key}"
        r = requests.get(url_vids)
        data = r.json()
        if 'items' in data and len(data['items']) > 0:
            vid_id = data['items'][0]['id']['videoId']
            titulo = data['items'][0]['snippet']['title']
            return f"{titulo}\nhttps://youtu.be/{vid_id}"
    except Exception as e:
        print("Error obteniendo video de YouTube:", e)
    return "Visita nuestro canal para ver la enseñanza de hoy: https://www.youtube.com/@SoyICT"

def enviar_whatsapp(mensaje):
    """
    Envía el mensaje al grupo de WhatsApp usando GreenAPI.
    """
    id_instance = os.environ.get('GREEN_INSTANCE')
    api_token = os.environ.get('GREEN_TOKEN')
    group_id = "573142306674-1607440499@g.us"
    
    url = f"https://api.green-api.com/waInstance{id_instance}/sendMessage/{api_token}"
    
    payload = {
        "chatId": group_id,
        "message": mensaje
    }
    r = requests.post(url, json=payload)
    print("Estado del envío a WhatsApp:", r.status_code, r.text)

def main():
    # 1. Obtenemos devocional y url de la imagen
    textos, img_url = obtener_devocional_y_imagen()
    
    # Parseamos los textos web (adaptándolo al formato que pasaste de ejemplo)
    titulo_tema = textos[0] if len(textos) > 0 else "Tema del día"
    biblico = textos[1] if len(textos) > 1 else ""
    complementario = textos[2] if len(textos) > 2 else ""
    reflexion = "\n\n".join(textos[3:-1]) if len(textos) > 4 else ""
    oracion = textos[-1] if len(textos) > 3 else ""

    # 2. Obtenemos el último video
    video_texto = obtener_ultimo_video()
    
    # 3. Leemos la imagen con Inteligencia Artificial
    meses = ['ENERO', 'FEBRERO', 'MARZO', 'ABRIL', 'MAYO', 'JUNIO', 'JULIO', 'AGOSTO', 'SEPTIEMBRE', 'OCTUBRE', 'NOVIEMBRE', 'DICIEMBRE']
    hoy = datetime.now()
    mes_nombre = meses[hoy.month - 1]
    fecha_hoy = f"{hoy.day} DE {mes_nombre}. {hoy.year}"
    fecha_busqueda_ia = f"{hoy.day} de {mes_nombre.lower()}"
    
    porciones = extraer_porciones_con_ia(img_url, fecha_busqueda_ia)
    
    # 4. Armamos el mensaje final
    mensaje_final = f"""😇 *{fecha_hoy}, EL AÑO DE LA INTELIGENCIA ESPIRITUAL* 🙏🏽

📖 {titulo_tema}
Mañana 5️⃣ am hr 🇨🇴 acompáñanos en nuestro devocional:
{video_texto}

👳🏾 *EN LA PRESENCIA DE DIOS* 🗣️

📕 *Pasaje bíblico:*
🛣️🏪 *{biblico.replace('Bíblico: ', '')}*

📘 *Pasajes complementarios:* {complementario.replace('Complementario: ', '')}

👑 *{reflexion[:800]}...* (continúa leyendo en nuestro corazón)

🙇🏾 *Oremos*😇
🙇🏾😇 *{oracion.replace('Oremos: ', '')}*

📘 *TOMADO DEL DEVOCIONAL EN CASA CON DIOS*🧑🏾💼

😍 *Por Amor a Israel y a Jerusalén* 🇮🇱🕌
🌿🇮🇱 *Paz sea a Israel, y pedid por la paz de Jerusalén.*
🙏🏽🌿🏪 Mas os gozaréis y os alegraréis para siempre en las cosas que yo he creado... Isaias 65:18-19

🤓 *{hoy.day} de {mes_nombre.lower()} {hoy.year}* 📖
*La Provisión Bíblica Diaria.*

{porciones}

👋🏽 *Saludos de Gratitud* 🙏🏽
😇👍🏽 *El Señor te guarde y bendiga en este hermoso día y su presencia te acompañe en todo momento y veas su gloria en todo lo que emprendas.*
🥰🤝🏼 *Un afectuoso abrazo.*👍🏽🌇"""
    
    print("--- MENSAJE GENERADO ---")
    print(mensaje_final)
    
    # 5. Enviar a WhatsApp
    enviar_whatsapp(mensaje_final)

if __name__ == "__main__":
    main()
