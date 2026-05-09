from flask import Flask, request, jsonify, send_file, render_template_string
import requests
import os
from gtts import gTTS
import tempfile

app = Flask(__name__)

WMO_CODES = {
    0: "Despejado", 1: "Mayormente despejado", 2: "Parcialmente nublado",
    3: "Nublado", 45: "Neblina", 48: "Neblina con escarcha",
    51: "Llovizna ligera", 53: "Llovizna moderada", 55: "Llovizna intensa",
    61: "Lluvia ligera", 63: "Lluvia moderada", 65: "Lluvia intensa",
    71: "Nevada ligera", 73: "Nevada moderada", 75: "Nevada intensa",
    80: "Chubascos ligeros", 81: "Chubascos moderados", 82: "Chubascos intensos",
    95: "Tormenta eléctrica", 99: "Tormenta con granizo",
}


def get_weather(city):
    geo_url = (
        "https://geocoding-api.open-meteo.com/v1/search"
        f"?name={requests.utils.quote(city)}&count=1&language=es&format=json"
    )
    try:
        geo_data = requests.get(geo_url, timeout=10).json()
    except Exception as e:
        return {"ok": False, "error": f"Error buscando la ciudad: {e}"}

    if not geo_data.get("results"):
        return {"ok": False, "error": f"Ciudad '{city}' no encontrada."}

    place = geo_data["results"][0]
    lat, lon = place["latitude"], place["longitude"]
    city_name = place["name"]
    country = place.get("country", "")
    admin = place.get("admin1", "")

    weather_url = (
        "https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        "&current=temperature_2m,apparent_temperature,relative_humidity_2m,"
        "wind_speed_10m,weather_code&timezone=auto"
    )
    try:
        current = requests.get(weather_url, timeout=10).json()["current"]
    except Exception as e:
        return {"ok": False, "error": f"Error obteniendo el clima: {e}"}

    temp = current["temperature_2m"]
    feels = current["apparent_temperature"]
    humidity = current["relative_humidity_2m"]
    wind = current["wind_speed_10m"]
    condition = WMO_CODES.get(current["weather_code"], "Desconocido")
    location = f"{city_name}, {admin}, {country}".replace(", ,", ",").strip(", ")

    weather_text = (
        f"🌍 {location}\n"
        f"🌡️ Temperatura: {temp}°C (sensación: {feels}°C)\n"
        f"⛅ Condición: {condition}\n"
        f"💧 Humedad: {humidity}%\n"
        f"💨 Viento: {wind} km/h"
    )
    voice_text = (
        f"Clima en {location}. "
        f"Temperatura de {temp} grados, sensación térmica de {feels} grados. "
        f"Condición: {condition}. "
        f"Humedad del {humidity} por ciento. "
        f"Viento a {wind} kilómetros por hora."
    )
    return {"ok": True, "text": weather_text, "voice": voice_text}


def text_to_speech(text, lang="es"):
    tts = gTTS(text=text, lang=lang, slow=False)
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3", dir=tempfile.gettempdir())
    tts.save(tmp.name)
    tmp.close()
    return tmp.name


HTML = r"""<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>WeatherBot</title>
<link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;700&family=Syne:wght@400;700;800&display=swap" rel="stylesheet">
<style>
  :root {
    --bg: #080b12; --panel: #0f1422; --border: #1a2035;
    --accent: #00e5ff; --accent2: #6d28d9;
    --text: #dde6f0; --muted: #4a5568;
    --bot-bg: #111827; --user-bg: #160d2e;
    --green: #10d9a0;
  }
  *, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }
  html, body { height: 100%; }
  body {
    background: var(--bg); color: var(--text);
    font-family: 'Syne', sans-serif;
    display: flex; align-items: center; justify-content: center;
    min-height: 100vh; overflow: hidden; position: relative;
  }
  body::before {
    content: ''; position: fixed; inset: 0;
    background:
      linear-gradient(rgba(0,229,255,.025) 1px, transparent 1px),
      linear-gradient(90deg, rgba(0,229,255,.025) 1px, transparent 1px);
    background-size: 44px 44px; pointer-events: none;
  }
  body::after {
    content: ''; position: fixed; top: -30%; right: -15%;
    width: 600px; height: 600px;
    background: radial-gradient(circle, rgba(109,40,217,.14) 0%, transparent 65%);
    pointer-events: none;
  }
  .app {
    width: min(680px, 100vw); height: 100vh;
    display: flex; flex-direction: column;
    position: relative; z-index: 1; padding: 12px;
  }
  .header {
    background: var(--panel); border: 1px solid var(--border);
    border-bottom: none; border-radius: 16px 16px 0 0;
    padding: 14px 18px; display: flex; align-items: center; gap: 12px;
  }
  .logo {
    width: 46px; height: 46px;
    background: linear-gradient(135deg, var(--accent2), var(--accent));
    border-radius: 12px; display: flex; align-items: center;
    justify-content: center; font-size: 24px; flex-shrink: 0;
    box-shadow: 0 0 24px rgba(0,229,255,.2);
  }
  .header-info h1 { font-size: 18px; font-weight: 800; letter-spacing: -.3px; }
  .online {
    display: flex; align-items: center; gap: 6px;
    font-family: 'JetBrains Mono', monospace;
    font-size: 11px; color: var(--green); margin-top: 2px;
  }
  .dot {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--green); animation: blink 2s ease-in-out infinite;
  }
  @keyframes blink { 0%,100%{opacity:1} 50%{opacity:.3} }
  .chat {
    flex: 1; overflow-y: auto; background: var(--panel);
    border: 1px solid var(--border); border-top: none; border-bottom: none;
    padding: 18px 16px; display: flex; flex-direction: column;
    gap: 14px; scroll-behavior: smooth;
  }
  .chat::-webkit-scrollbar { width: 3px; }
  .chat::-webkit-scrollbar-thumb { background: var(--border); border-radius: 99px; }
  .row { display: flex; gap: 9px; max-width: 88%; animation: fadeUp .3s ease; }
  @keyframes fadeUp { from{opacity:0;transform:translateY(6px)} to{opacity:1;transform:none} }
  .row.bot  { align-self: flex-start; }
  .row.user { align-self: flex-end; flex-direction: row-reverse; }
  .av {
    width: 30px; height: 30px; border-radius: 8px;
    display: flex; align-items: center; justify-content: center;
    font-size: 15px; flex-shrink: 0; margin-top: 3px;
  }
  .row.bot  .av { background: linear-gradient(135deg, var(--accent2), var(--accent)); }
  .row.user .av { background: var(--user-bg); border: 1px solid var(--border); }
  .bubble {
    padding: 10px 13px; font-size: 14px; line-height: 1.65;
    white-space: pre-wrap; border-radius: 11px;
  }
  .row.bot  .bubble { background: var(--bot-bg); border: 1px solid var(--border); border-top-left-radius: 3px; }
  .row.user .bubble { background: var(--user-bg); border: 1px solid rgba(109,40,217,.35); border-top-right-radius: 3px; }
  .chips { display: flex; flex-wrap: wrap; gap: 5px; margin-top: 8px; }
  .chip {
    padding: 4px 10px; background: rgba(0,229,255,.07);
    border: 1px solid rgba(0,229,255,.2); border-radius: 99px;
    font-size: 12px; font-family: 'JetBrains Mono', monospace;
    color: var(--accent); cursor: pointer; transition: background .15s, transform .15s;
  }
  .chip:hover { background: rgba(0,229,255,.14); transform: translateY(-1px); }
  .audio-box {
    margin-top: 9px; padding: 8px 11px;
    background: rgba(0,229,255,.05); border: 1px solid rgba(0,229,255,.18);
    border-radius: 8px; display: flex; align-items: center; gap: 8px;
  }
  .audio-box label { font-size: 11px; font-family: 'JetBrains Mono', monospace; color: var(--accent); white-space: nowrap; }
  audio { flex: 1; height: 26px; }
  .typing-row { display: flex; gap: 9px; }
  .typing-bubble {
    padding: 12px 14px; background: var(--bot-bg);
    border: 1px solid var(--border); border-radius: 11px; border-top-left-radius: 3px;
    display: flex; gap: 5px; align-items: center;
  }
  .typing-bubble span {
    width: 7px; height: 7px; border-radius: 50%;
    background: var(--accent); animation: bounce 1.1s infinite;
  }
  .typing-bubble span:nth-child(2){animation-delay:.18s}
  .typing-bubble span:nth-child(3){animation-delay:.36s}
  @keyframes bounce { 0%,60%,100%{transform:translateY(0);opacity:.4} 30%{transform:translateY(-6px);opacity:1} }
  .input-bar {
    background: var(--panel); border: 1px solid var(--border);
    border-radius: 0 0 16px 16px; padding: 12px 14px;
    display: flex; gap: 9px;
  }
  #inp {
    flex: 1; background: var(--bg); border: 1px solid var(--border);
    border-radius: 9px; padding: 9px 13px; color: var(--text);
    font-family: 'JetBrains Mono', monospace; font-size: 13px;
    outline: none; transition: border-color .2s;
  }
  #inp:focus { border-color: var(--accent); }
  #inp::placeholder { color: var(--muted); }
  #btn {
    padding: 9px 18px;
    background: linear-gradient(135deg, var(--accent2), var(--accent));
    border: none; border-radius: 9px; color: #fff;
    font-family: 'Syne', sans-serif; font-weight: 700;
    font-size: 14px; cursor: pointer; transition: transform .15s, box-shadow .15s;
  }
  #btn:hover { transform: translateY(-1px); box-shadow: 0 4px 18px rgba(0,229,255,.28); }
  #btn:disabled { opacity: .45; pointer-events: none; }
</style>
</head>
<body>
<div class="app">
  <div class="header">
    <div class="logo">🤖</div>
    <div class="header-info">
      <h1>WeatherBot</h1>
      <div class="online"><div class="dot"></div>en línea · Open-Meteo API</div>
    </div>
  </div>
  <div class="chat" id="chat">
    <div class="row bot">
      <div class="av">🤖</div>
      <div>
        <div class="bubble">¡Hola! Soy <strong>WeatherBot</strong> 🌦️

Puedo decirte el clima de cualquier ciudad y leerlo en voz alta.

Usa los botones de abajo para empezar:</div>
        <div class="chips">
          <span class="chip" onclick="fill('!start')">!start</span>
          <span class="chip" onclick="fill('!weather San José')">!weather San José</span>
          <span class="chip" onclick="fill('!weather Madrid')">!weather Madrid</span>
          <span class="chip" onclick="fill('!weather Tokio')">!weather Tokio</span>
          <span class="chip" onclick="fill('!help')">!help</span>
        </div>
      </div>
    </div>
  </div>
  <div class="input-bar">
    <input id="inp" placeholder="Escribe un comando: !weather <ciudad>" autocomplete="off" />
    <button id="btn" onclick="send()">Enviar ➤</button>
  </div>
</div>
<script>
const chat = document.getElementById('chat');
const inp  = document.getElementById('inp');
const btn  = document.getElementById('btn');

function fill(cmd) { inp.value = cmd; inp.focus(); }

function addMsg(role, text, audioUrl = null) {
  const row = document.createElement('div');
  row.className = `row ${role}`;
  const av = document.createElement('div');
  av.className = 'av';
  av.textContent = role === 'bot' ? '🤖' : '🧑';
  const body = document.createElement('div');
  const bubble = document.createElement('div');
  bubble.className = 'bubble';
  bubble.textContent = text;
  body.appendChild(bubble);
  if (audioUrl) {
    const box = document.createElement('div');
    box.className = 'audio-box';
    box.innerHTML = `<label>🔊 voz</label><audio controls autoplay src="${audioUrl}"></audio>`;
    body.appendChild(box);
  }
  row.appendChild(av);
  row.appendChild(body);
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
}

function showTyping() {
  const row = document.createElement('div');
  row.className = 'typing-row'; row.id = 'typing';
  const av = document.createElement('div');
  av.className = 'av'; av.textContent = '🤖';
  const b = document.createElement('div');
  b.className = 'typing-bubble';
  b.innerHTML = '<span></span><span></span><span></span>';
  row.appendChild(av); row.appendChild(b);
  chat.appendChild(row);
  chat.scrollTop = chat.scrollHeight;
}

function hideTyping() {
  const t = document.getElementById('typing');
  if (t) t.remove();
}

async function send() {
  const cmd = inp.value.trim();
  if (!cmd) return;
  addMsg('user', cmd);
  inp.value = '';
  btn.disabled = true;
  showTyping();
  try {
    const res  = await fetch('/command', {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({ command: cmd })
    });
    const data = await res.json();
    hideTyping();
    addMsg('bot', data.text, data.audio_url || null);
  } catch {
    hideTyping();
    addMsg('bot', '❌ No pude conectar con el servidor.');
  } finally {
    btn.disabled = false;
    inp.focus();
  }
}

inp.addEventListener('keydown', e => { if (e.key === 'Enter') send(); });
</script>
</body>
</html>"""


@app.route("/")
def index():
    return render_template_string(HTML)


@app.route("/command", methods=["POST"])
def command():
    data = request.get_json(force=True)
    cmd  = (data.get("command") or "").strip()

    if cmd.lower() == "!start":
        return jsonify({
            "text": (
                "✅ ¡Bot iniciado!\n\n"
                "Bienvenido a WeatherBot. Estoy listo.\n\n"
                "Escribe !weather <ciudad> para consultar el clima 🌍"
            )
        })

    if cmd.lower() == "!help":
        return jsonify({
            "text": (
                "📖 Comandos disponibles:\n\n"
                "  !start              → Saludo de bienvenida\n"
                "  !weather <ciudad>   → Clima + voz de la ciudad\n"
                "  !help               → Esta ayuda\n\n"
                "Ejemplo: !weather Buenos Aires"
            )
        })

    if cmd.lower().startswith("!weather"):
        parts = cmd.split(None, 1)
        if len(parts) < 2 or not parts[1].strip():
            return jsonify({"text": "⚠️ Falta la ciudad. Ejemplo: !weather Lima"})

        result = get_weather(parts[1].strip())
        if not result["ok"]:
            return jsonify({"text": f"❌ {result['error']}"})

        audio_url = None
        try:
            path = text_to_speech(result["voice"])
            audio_url = f"/audio/{os.path.basename(path)}"
        except Exception as e:
            print(f"gTTS error: {e}")

        return jsonify({"text": result["text"], "audio_url": audio_url})

    return jsonify({"text": f'❓ Comando desconocido: "{cmd}"\n\nEscribe !help para ver los comandos.'})


@app.route("/audio/<filename>")
def serve_audio(filename):
    path = os.path.join(tempfile.gettempdir(), filename)
    if os.path.isfile(path):
        return send_file(path, mimetype="audio/mpeg")
    return "Not found", 404


if __name__ == "__main__":
    print("\n🤖 WeatherBot en http://localhost:5000\n")
    app.run(debug=True, host="0.0.0.0", port=5000)
