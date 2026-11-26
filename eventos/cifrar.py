"""Cifra la app de Eventos para GitHub Pages (el repositorio es público).

Uso (lo hace Claude al subir una versión nueva):
  EVENTOS_CLAVE=<patrón> python3 eventos/cifrar.py fuente.html [historico.json] [carpeta_pdfs]

- fuente.html: la página en claro (la del artifact, con const DATA = {...};).
- Escribe eventos/index.html con los datos cifrados (AES-GCM, clave = PBKDF2 del patrón).
- historico.json (opcional): lo cifra en eventos/historico.enc.
- carpeta_pdfs (opcional): copia cifrados todos los PDF que haya dentro a eventos/beos/ (misma ruta relativa).
La página pide el patrón una vez por dispositivo y lo recuerda.
También sirve para leer los datos: descifrar_data() lo usa generar_ics.py."""
import base64, json, os, pathlib, re, sys
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

BASE = pathlib.Path(__file__).resolve().parent
ITER = 250000
SALT_FILE = BASE / "cifrado-sal.txt"


def sal():
    if not SALT_FILE.exists():
        SALT_FILE.write_text(os.urandom(16).hex())
    return bytes.fromhex(SALT_FILE.read_text().strip())


def clave():
    p = os.environ.get("EVENTOS_CLAVE", "").strip()
    if not p:
        sys.exit("Falta EVENTOS_CLAVE")
    return PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=sal(), iterations=ITER).derive(p.encode())


def cif(b, k):
    iv = os.urandom(12)
    return iv + AESGCM(k).encrypt(iv, b, None)


def des(b, k):
    return AESGCM(k).decrypt(b[:12], b[12:], None)


def descifrar_data(html):
    m = re.search(r'ENC="([^"]+)"', html)
    return json.loads(des(base64.b64decode(m.group(1)), clave()))


GATE = r"""<div id="gate" hidden><div class="gbox"><span id="gmsg">Dibuja el patrón</span>
<svg id="gpad" viewBox="0 0 300 300" role="img" aria-label="Patrón de desbloqueo"><polyline id="gline" points="" fill="none" stroke-width="10" stroke-linecap="round" stroke-linejoin="round"/></svg></div></div>
<style>
#gate{position:fixed;inset:0;z-index:100;background:var(--bg);display:grid;place-items:center;padding:max(16px,env(safe-area-inset-left,0px))}
#gate .gbox{display:grid;justify-items:center;gap:10px;text-align:center}
#gate b{font-family:var(--f-display);font-size:30px}
#gmsg{color:var(--muted);min-height:1.5em}
#gate.bad #gmsg{color:#C2412D}
#gpad{width:min(300px,80vw);height:auto;touch-action:none;user-select:none;-webkit-user-select:none}
#gpad circle{fill:var(--line)}#gpad circle.on{fill:var(--sea)}
#gline{stroke:var(--sea);opacity:.55}
#gate.bad #gline{stroke:#C2412D}
#gout{font-size:12px;padding:3px 9px}
</style>
<script>
(function(){
const SALT="__SALT__",ENC="__ENC__",ITER=__ITER__;
const b64=s=>Uint8Array.from(atob(s),c=>c.charCodeAt(0));
const hex=h=>new Uint8Array(h.match(/../g).map(x=>parseInt(x,16)));
const ls=(k,v)=>{try{if(v===undefined)return localStorage.getItem(k);if(v===null)localStorage.removeItem(k);else localStorage.setItem(k,v)}catch(e){return null}};
let KEY=null;
const imp=raw=>crypto.subtle.importKey("raw",raw,"AES-GCM",false,["decrypt"]);
async function derive(p){const k=await crypto.subtle.importKey("raw",new TextEncoder().encode(p),"PBKDF2",false,["deriveBits"]);
  return new Uint8Array(await crypto.subtle.deriveBits({name:"PBKDF2",salt:hex(SALT),iterations:ITER,hash:"SHA-256"},k,256));}
const dec=(buf,k)=>{buf=new Uint8Array(buf);return crypto.subtle.decrypt({name:"AES-GCM",iv:buf.slice(0,12)},k||KEY,buf.slice(12));};
window.DEC=b=>dec(b);
window.HON=ls("beo-hist")==="1";
async function start(raw){
  const k=await imp(raw);
  const d=JSON.parse(new TextDecoder().decode(await dec(b64(ENC),k)));
  KEY=k;
  if(window.HON){try{const r=await fetch("historico.enc");window.HIST=JSON.parse(new TextDecoder().decode(await dec(await r.arrayBuffer())));}catch(e){window.HIST=null}}
  window.__D=d;
  document.getElementById("gate").hidden=true;
  const s=document.createElement("script");s.textContent=document.getElementById("appsrc").textContent;document.body.appendChild(s);
  const t=document.querySelector(".titlerow");if(t){const b=document.createElement("button");b.type="button";b.className="chip";b.id="gout";b.title="Olvidar el patrón en este dispositivo";b.textContent="🔒 Salir";
    b.onclick=()=>{ls("beo-k",null);location.reload();};t.appendChild(b);}
}
const g=document.getElementById("gate"),pad=document.getElementById("gpad"),line=document.getElementById("gline"),msg=document.getElementById("gmsg");
const P=[];for(let i=0;i<9;i++){const c=document.createElementNS("http://www.w3.org/2000/svg","circle");const x=50+100*(i%3),y=50+100*Math.floor(i/3);
  c.setAttribute("cx",x);c.setAttribute("cy",y);c.setAttribute("r",14);pad.appendChild(c);P.push([x,y,c]);}
let seq=[],down=false,busy=false;
const pt=e=>{const r=pad.getBoundingClientRect();return[(e.clientX-r.left)*300/r.width,(e.clientY-r.top)*300/r.height]};
const draw=(extra)=>line.setAttribute("points",seq.map(i=>P[i][0]+","+P[i][1]).concat(extra?[extra.join(",")]:[]).join(" "));
function hit(e){const[x,y]=pt(e);P.forEach((p,i)=>{if(!seq.includes(i)&&Math.hypot(p[0]-x,p[1]-y)<38){seq.push(i);p[2].classList.add("on")}});draw([x,y]);}
function reset(){seq=[];P.forEach(p=>p[2].classList.remove("on"));draw();}
pad.addEventListener("pointerdown",e=>{if(busy)return;g.classList.remove("bad");reset();down=true;pad.setPointerCapture(e.pointerId);hit(e);});
pad.addEventListener("pointermove",e=>{if(down)hit(e)});
pad.addEventListener("pointerup",async()=>{if(!down)return;down=false;draw();if(seq.length<2){reset();return}
  busy=true;msg.textContent="Comprobando…";const raw=await derive(seq.map(i=>i+1).join(""));
  try{await start(raw);ls("beo-k",btoa(String.fromCharCode(...raw)));}
  catch(e){g.classList.add("bad");msg.textContent="Patrón incorrecto";setTimeout(()=>{reset();g.classList.remove("bad");msg.textContent="Dibuja el patrón"},900);}
  busy=false;});
(async()=>{const s=ls("beo-k");if(s){try{await start(b64(s));return}catch(e){ls("beo-k",null)}}g.hidden=false;})();
})();
</script>
"""


def main():
    k = clave()
    src = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8")
    m = re.search(r"<script>\nconst DATA = (\{.*?\});\n", src, re.S)
    data = json.loads(m.group(1))
    h = src[:m.start()] + '<script type="text/plain" id="appsrc">\nconst DATA = window.__D;\n' + src[m.end():]
    h = re.sub(r'<script>window\.HON=.*?</script>\n', "", h)
    old = "new Uint8Array(await r.arrayBuffer())"
    assert h.count(old) == 1
    h = h.replace(old, "new Uint8Array(await DEC(await r.arrayBuffer()))")
    h = h.replace("BEOs Palau y Palma Bay", "Eventos Palau y Palma Bay")
    enc = base64.b64encode(cif(json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode(), k)).decode()
    gate = GATE.replace("__SALT__", sal().hex()).replace("__ENC__", enc).replace("__ITER__", str(ITER))
    i = h.rindex("</script>") + len("</script>")
    h = h[:i] + "\n" + gate + h[i:]
    (BASE / "index.html").write_text(h, encoding="utf-8")
    print("index.html cifrado:", len(data["servicios"]), "servicios")
    if len(sys.argv) > 2 and sys.argv[2] != "-":
        hj = pathlib.Path(sys.argv[2]).read_text(encoding="utf-8")
        if hj.startswith("window.HIST="):
            hj = hj[len("window.HIST="):].rstrip().rstrip(";")
        (BASE / "historico.enc").write_bytes(cif(hj.encode(), k))
        print("historico.enc cifrado")
    if len(sys.argv) > 3:
        root = pathlib.Path(sys.argv[3])
        n = 0
        for p in root.rglob("*"):
            if p.suffix.lower() == ".pdf":
                b = p.read_bytes()
                if not b.startswith(b"%PDF"):
                    continue
                out = BASE / "beos" / p.relative_to(root)
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_bytes(cif(b, k))
                n += 1
        print(n, "PDF cifrados")


if __name__ == "__main__":
    main()
