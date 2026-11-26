/* Lee los datos de la página de Eventos (cifrados con el patrón).
   Usa la clave que ya guardó Eventos en este dispositivo; si no hay, pinta el patrón en `caja` y espera.
   cargarDatosEventos(caja) → Promise<DATA> */
(function () {
  const ls = (k, v) => { try { if (v === undefined) return localStorage.getItem(k); if (v === null) localStorage.removeItem(k); else localStorage.setItem(k, v); } catch (e) { return null; } };
  const b64 = s => Uint8Array.from(atob(s), c => c.charCodeAt(0));
  const hex = h => new Uint8Array(h.match(/../g).map(x => parseInt(x, 16)));
  async function descifrar(enc, raw) {
    const k = await crypto.subtle.importKey('raw', raw, 'AES-GCM', false, ['decrypt']);
    const b = b64(enc);
    const t = await crypto.subtle.decrypt({ name: 'AES-GCM', iv: b.slice(0, 12) }, k, b.slice(12));
    return JSON.parse(new TextDecoder().decode(t));
  }
  async function derivar(p, salt, iter) {
    const k = await crypto.subtle.importKey('raw', new TextEncoder().encode(p), 'PBKDF2', false, ['deriveBits']);
    return new Uint8Array(await crypto.subtle.deriveBits({ name: 'PBKDF2', salt: hex(salt), iterations: iter, hash: 'SHA-256' }, k, 256));
  }
  function patron(caja, alTerminar) {
    caja.innerHTML = `<div style="display:grid;justify-items:center;gap:8px;padding:18px 0;text-align:center">
      <div style="font-weight:700">Dibuja el patrón de Eventos</div><div class="pmsg" style="color:#6B7280;font-size:14px;min-height:1.4em">Solo la primera vez en este móvil</div>
      <svg viewBox="0 0 300 300" style="width:min(260px,75vw);touch-action:none;user-select:none"><polyline fill="none" stroke="#2E5597" stroke-width="10" stroke-linecap="round" stroke-linejoin="round" opacity=".55" points=""/></svg></div>`;
    const pad = caja.querySelector('svg'), line = pad.querySelector('polyline'), msg = caja.querySelector('.pmsg');
    const P = [];
    for (let i = 0; i < 9; i++) {
      const c = document.createElementNS('http://www.w3.org/2000/svg', 'circle');
      const x = 50 + 100 * (i % 3), y = 50 + 100 * Math.floor(i / 3);
      c.setAttribute('cx', x); c.setAttribute('cy', y); c.setAttribute('r', 14); c.setAttribute('fill', '#D6DCE6');
      pad.appendChild(c); P.push([x, y, c]);
    }
    let seq = [], down = false, busy = false;
    const pt = e => { const r = pad.getBoundingClientRect(); return [(e.clientX - r.left) * 300 / r.width, (e.clientY - r.top) * 300 / r.height]; };
    const draw = ex => line.setAttribute('points', seq.map(i => P[i][0] + ',' + P[i][1]).concat(ex ? [ex.join(',')] : []).join(' '));
    const reset = () => { seq = []; P.forEach(p => p[2].setAttribute('fill', '#D6DCE6')); draw(); };
    const hit = e => { const [x, y] = pt(e); P.forEach((p, i) => { if (!seq.includes(i) && Math.hypot(p[0] - x, p[1] - y) < 38) { seq.push(i); p[2].setAttribute('fill', '#2E5597'); } }); draw([x, y]); };
    pad.addEventListener('pointerdown', e => { if (busy) return; reset(); down = true; pad.setPointerCapture(e.pointerId); hit(e); });
    pad.addEventListener('pointermove', e => { if (down) hit(e); });
    pad.addEventListener('pointerup', async () => {
      if (!down) return; down = false; draw(); if (seq.length < 2) { reset(); return; }
      busy = true; msg.textContent = 'Comprobando…';
      const ok = await alTerminar(seq.map(i => i + 1).join(''));
      busy = false;
      if (!ok) { msg.textContent = 'Patrón incorrecto'; msg.style.color = '#C2412D'; setTimeout(() => { reset(); msg.textContent = 'Dibuja el patrón de Eventos'; msg.style.color = '#6B7280'; }, 900); }
    });
  }
  window.cargarDatosEventos = async function (caja) {
    const r = await fetch('../eventos/index.html', { cache: 'no-store' });
    const t = await r.text();
    const claro = t.match(/const DATA = (\{[\s\S]*?\});\n/);
    if (claro) return JSON.parse(claro[1]);
    const m = t.match(/SALT="([0-9a-f]+)",ENC="([^"]+)",ITER=(\d+)/);
    if (!m) throw new Error('sin datos');
    const [, salt, enc, iter] = m;
    const guardada = ls('beo-k');
    if (guardada) { try { return await descifrar(enc, b64(guardada)); } catch (e) { ls('beo-k', null); } }
    if (!caja) throw new Error('bloqueado');
    return new Promise(res => patron(caja, async p => {
      const raw = await derivar(p, salt, +iter);
      try { const d = await descifrar(enc, raw); ls('beo-k', btoa(String.fromCharCode(...raw))); caja.innerHTML = ''; res(d); return true; }
      catch (e) { return false; }
    }));
  };
})();
