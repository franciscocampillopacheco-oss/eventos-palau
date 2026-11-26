"""Genera eventos/eventos.ics (calendario suscribible) a partir de eventos/index.html.
Solo servicios con F&B y con hora real, con aviso 30 min antes. Lo ejecuta GitHub Actions."""
import re, json, hashlib, datetime, pathlib, sys

base = pathlib.Path(__file__).resolve().parent
html = (base / "index.html").read_text(encoding="utf-8")
m = re.search(r"const DATA = (\{.*?\});\n", html, re.S)
if m:
    data = json.loads(m.group(1))
else:  # página cifrada: hace falta la clave (secreto EVENTOS_CLAVE de GitHub o la pone Claude al subir)
    import os
    if not os.environ.get("EVENTOS_CLAVE"):
        print("Página cifrada y sin EVENTOS_CLAVE: dejo el calendario como está"); sys.exit(0)
    sys.path.insert(0, str(base)); from cifrar import descifrar_data
    data = descifrar_data(html)
NOFB = {"reu", "expo", "mont"}
TIPOS = {"des":"Desayuno","cafe":"Café permanente","beb":"Bebidas","cb":"Coffee break","alm":"Almuerzo",
         "cena":"Cena","coctel":"Cóctel","bar":"Open bar","fruta":"Fruta","otro":"Servicio"}
grupos = {g["id"]: g for g in data["grupos"]}
sinhora = re.compile(r"sin (horario|indicar)|franja", re.I)
hoy = datetime.date.today()

def esc(t):
    BS = chr(92)
    return str(t).replace(BS, BS + BS).replace(";", BS + ";").replace(",", BS + ",").replace(chr(10), BS + "n")

def fold(line):
    b = line.encode("utf-8"); out = []
    while len(b) > 75:
        cut = 75
        while (b[cut] & 0xC0) == 0x80: cut -= 1
        out.append(b[:cut].decode()); b = b" " + b[cut:]
    out.append(b.decode()); return "\r\n".join(out)

def dt(fecha, h):
    d = datetime.datetime.strptime(fecha, "%Y-%m-%d") + datetime.timedelta(minutes=round(h * 60))
    return d.strftime("%Y%m%dT%H%M%S")

L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Eventos Palau y Palma Bay//ES", "CALSCALE:GREGORIAN",
     "METHOD:PUBLISH", "X-WR-CALNAME:Eventos F&B", "X-WR-TIMEZONE:Europe/Madrid",
     "REFRESH-INTERVAL;VALUE=DURATION:PT1H", "X-PUBLISHED-TTL:PT1H",
     "BEGIN:VTIMEZONE", "TZID:Europe/Madrid",
     "BEGIN:DAYLIGHT", "TZOFFSETFROM:+0100", "TZOFFSETTO:+0200", "TZNAME:CEST", "DTSTART:19700329T020000",
     "RRULE:FREQ=YEARLY;BYMONTH=3;BYDAY=-1SU", "END:DAYLIGHT",
     "BEGIN:STANDARD", "TZOFFSETFROM:+0200", "TZOFFSETTO:+0100", "TZNAME:CET", "DTSTART:19701025T030000",
     "RRULE:FREQ=YEARLY;BYMONTH=10;BYDAY=-1SU", "END:STANDARD", "END:VTIMEZONE"]
stamp = hoy.strftime("%Y%m%dT000000Z")  # fijo durante el día: así no hay cambios (ni commits) cada 20 min
vistos = {}; n = 0
for s in data["servicios"]:
    if s.get("t") in NOFB or sinhora.search(s.get("time") or ""): continue
    if datetime.date.fromisoformat(s["fecha"]) < hoy - datetime.timedelta(days=14): continue
    g = grupos.get(s["g"], {"n": s["g"]})
    clave = f'{s["g"]}|{s["fecha"]}|{s["title"]}'
    vistos[clave] = vistos.get(clave, 0) + 1
    uid = hashlib.sha1(f"{clave}|{vistos[clave]}".encode()).hexdigest()[:20] + "@eventos-palau"
    pax = s.get("pax") if isinstance(s.get("pax"), (int, float)) else None
    pax_txt = f"{pax} pax" if pax else (f'{s.get("paxLabel","")} {s.get("paxNote","")}'.strip())
    salas = ", ".join(s.get("salas") or [s.get("place", "")])
    titulo = f'{g["n"]} · {s["title"]}' + (f" ({pax_txt})" if pax_txt and pax_txt != "—" else "")
    desc = [f'{TIPOS.get(s["t"], "Servicio")} · {s.get("time","")}', f"Pax: {pax_txt or '—'}", f"Sala: {s.get('place','')}"]
    if g.get("cm"): desc.append(f'Catering manager: {g["cm"]}')
    facts = [f for f in (s.get("facts") or []) if f not in ("Hotel", "Palau")]
    if facts: desc.append(" · ".join(facts))
    if s.get("alert"): desc.append("⚠ " + s["alert"])
    L += ["BEGIN:VEVENT", f"UID:{uid}", f"DTSTAMP:{stamp}",
          f"DTSTART;TZID=Europe/Madrid:{dt(s['fecha'], s['start'])}",
          f"DTEND;TZID=Europe/Madrid:{dt(s['fecha'], s['end'])}",
          f"SUMMARY:{esc(titulo)}", f"LOCATION:{esc(salas)}", f"DESCRIPTION:{esc(chr(10).join(desc))}",
          "BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{esc(titulo)}", "TRIGGER:-PT30M", "END:VALARM",
          "END:VEVENT"]
    n += 1
L.append("END:VCALENDAR")
(base / "eventos.ics").write_text("\r\n".join(fold(x) for x in L) + "\r\n", encoding="utf-8")
print(f"eventos.ics: {n} servicios")
