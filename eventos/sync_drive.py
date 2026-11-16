"""Trae a GitHub la página de Eventos (y los PDF de BEO nuevos) que la tarea programada deja en Google Drive.
La hoja «Eventos Palau – puntero web» (pública con enlace) dice qué archivo de Drive es el último:
  fila html: ruta eventos/index.html, id = id del archivo en Drive
  filas pdf: ruta beos/x.pdf, id = id del PDF en Drive
Lo ejecuta GitHub Actions cada 20 minutos."""
import csv, io, json, pathlib, re, sys, urllib.request

SHEET = "14GNW0QuAh1iblnjpfhZREZpeZ7Ey0J9ldvXH7xCql38"
base = pathlib.Path(__file__).resolve().parent
estado_p = base / ".drive-sync.json"
estado = json.loads(estado_p.read_text()) if estado_p.exists() else {"html": "", "pdfs": {}}


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url), timeout=60) as r:
        return r.read()


def drive(fid):
    return get(f"https://drive.google.com/uc?export=download&id={fid}")


filas = list(csv.reader(io.StringIO(get(f"https://docs.google.com/spreadsheets/d/{SHEET}/gviz/tq?tqx=out:csv").decode("utf-8"))))
cambios = []
for f in filas[1:]:
    if len(f) < 3 or not f[2].strip():
        continue
    tipo, ruta, fid = f[0].strip().lower(), f[1].strip(), f[2].strip()
    if tipo == "html" and fid != estado.get("html"):
        h = drive(fid).decode("utf-8")
        m = re.search(r"const DATA = (\{.*?\});\n", h, re.S)
        if not m:
            sys.exit(f"El HTML {fid} no trae const DATA: no lo publico")
        d = json.loads(m.group(1))
        if not d.get("servicios") or not d.get("grupos"):
            sys.exit("DATA vacío: no lo publico")
        h = h.replace("BEOs Palau y Palma Bay", "Eventos Palau y Palma Bay")
        (base / "index.html").write_text(h, encoding="utf-8")
        estado["html"] = fid
        cambios.append(f"index.html ({len(d['servicios'])} servicios)")
    elif tipo == "pdf" and re.fullmatch(r"beos/[A-Za-z0-9._-]+\.pdf", ruta) and estado["pdfs"].get(ruta) != fid:
        b = drive(fid)
        if not b.startswith(b"%PDF"):
            print(f"aviso: {ruta} ({fid}) no es un PDF, lo salto")
            continue
        (base / ruta).write_bytes(b)
        estado["pdfs"][ruta] = fid
        cambios.append(ruta)
estado_p.write_text(json.dumps(estado, indent=1))
print("Cambios:", ", ".join(cambios) if cambios else "ninguno")
