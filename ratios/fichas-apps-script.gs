/**
 * Fichas de plato · guarda lo que rellenan los cocineros en la hoja «Ratios cocina».
 * Va pegado a la hoja (Extensiones → Apps Script) e implementado como aplicación web:
 *   Ejecutar como: yo · Quién tiene acceso: cualquier usuario.
 * La página ratios/fichas.html lee con GET y guarda con POST.
 */
const HOJA_FICHAS = 'FICHAS';
const COLS_NUEVAS = ['MERMA %', 'MENAJE (pieza:por pax | …)', 'FOTO', 'ESTADO'];
const MENAJE_INICIAL = ['Plato llano', 'Plato hondo', 'Plato postre', 'Plato pizarra', 'Bol pequeño', 'Bol grande',
  'Vasito de cristal', 'Vasito desechable', 'Cucharita degustación', 'Mini cazuelita', 'Tabla de madera',
  'Bandeja espejo', 'Bandeja melamina', 'Fuente de cristal', 'Cesta de pan', 'Jarra', 'Palillo / brocheta'];
const RECIPIENTES_INICIAL = ['GN 1/1', 'GN 1/2', 'GN 1/3', 'GN 1/4', 'GN 1/6', 'GN 1/9', 'Bandeja horno 60×40',
  'Bandeja pastelería', 'Olla / marmita', 'Cubeta', 'Táper'];

function preparar_() {
  const ss = SpreadsheetApp.openById('1-GO7YcM6SICnqdsl-Vph-_7fMe2QWso-zmfqXgwgMWk');
  const f = ss.getSheetByName(HOJA_FICHAS);
  const cab = f.getRange(1, 1, 1, f.getLastColumn()).getValues()[0];
  COLS_NUEVAS.forEach(c => {
    if (cab.indexOf(c) < 0) {
      const col = f.getLastColumn() + 1;
      if (col > f.getMaxColumns()) f.insertColumnAfter(f.getMaxColumns());
      const src = f.getRange(1, 1);
      f.getRange(1, col).setValue(c);
      src.copyTo(f.getRange(1, col), SpreadsheetApp.CopyPasteType.PASTE_FORMAT, false);
      cab.push(c);
    }
  });
  lista_('MENAJE', 'PIEZA DE MENAJE', MENAJE_INICIAL);
  lista_('RECIPIENTES', 'RECIPIENTE DE COCINA', RECIPIENTES_INICIAL);
  if (!ss.getSheetByName('RESPUESTAS')) {
    const r = ss.insertSheet('RESPUESTAS');
    r.appendRow(['FECHA', 'COCINERO', 'PLATO', 'CANTIDAD POR PAX', 'UNIDAD', 'MERMA %', 'MENAJE', 'RECIPIENTE', 'CABE', 'NOTAS', 'FOTO']);
    r.setFrozenRows(1); r.getRange(1, 1, 1, 11).setFontWeight('bold');
  }
  return cab;
}

function lista_(nombre, titulo, valores) {
  const ss = SpreadsheetApp.openById('1-GO7YcM6SICnqdsl-Vph-_7fMe2QWso-zmfqXgwgMWk');
  let h = ss.getSheetByName(nombre);
  if (!h) {
    h = ss.insertSheet(nombre);
    h.getRange(1, 1, valores.length + 1, 1).setValues([[titulo]].concat(valores.map(v => [v])));
    h.setFrozenRows(1); h.getRange(1, 1).setFontWeight('bold'); h.setColumnWidth(1, 260);
  }
  return h.getRange(2, 1, Math.max(1, h.getLastRow() - 1), 1).getValues().map(r => String(r[0]).trim()).filter(String);
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}

function doGet() {
  const cab = preparar_();
  const f = SpreadsheetApp.openById('1-GO7YcM6SICnqdsl-Vph-_7fMe2QWso-zmfqXgwgMWk').getSheetByName(HOJA_FICHAS);
  const filas = f.getRange(2, 1, Math.max(1, f.getLastRow() - 1), cab.length).getDisplayValues()
    .filter(r => String(r[0]).trim());
  return json_({ cab: cab, filas: filas, menaje: lista_('MENAJE', '', []), recipientes: lista_('RECIPIENTES', '', []) });
}

function doPost(e) {
  const lock = LockService.getScriptLock();
  lock.waitLock(20000);
  try {
    const d = JSON.parse(e.postData.contents);
    const cab = preparar_();
    const ss = SpreadsheetApp.openById('1-GO7YcM6SICnqdsl-Vph-_7fMe2QWso-zmfqXgwgMWk');
    if (d.accion === 'pieza') {
      const hoja = d.tipo === 'recipiente' ? 'RECIPIENTES' : 'MENAJE';
      const ya = lista_(hoja, '', []).map(x => x.toLowerCase());
      const n = String(d.nombre || '').trim().slice(0, 60);
      if (n && ya.indexOf(n.toLowerCase()) < 0) ss.getSheetByName(hoja).appendRow([n]);
      return json_({ ok: true });
    }
    if (d.accion !== 'ficha') return json_({ ok: false, error: 'acción desconocida' });
    const f = ss.getSheetByName(HOJA_FICHAS);
    const c = n => cab.indexOf(n) + 1;
    const plato = String(d.plato || '').trim();
    if (!plato) return json_({ ok: false, error: 'falta el plato' });
    const nombres = f.getRange(2, 1, Math.max(1, f.getLastRow() - 1), 1).getValues().map(r => String(r[0]).trim());
    let fila = nombres.indexOf(plato) + 2;
    if (fila < 2) {
      fila = f.getLastRow() + 1;
      f.getRange(fila, 1).setValue(plato);
      if (d.grupo) f.getRange(fila, c('GRUPO')).setValue(d.grupo);
    }
    let foto = '';
    if (d.foto && /^data:image\//.test(d.foto)) {
      const it = DriveApp.getFoldersByName('Fichas de platos · fotos');
      const carpeta = it.hasNext() ? it.next() : DriveApp.createFolder('Fichas de platos · fotos');
      const b = Utilities.newBlob(Utilities.base64Decode(d.foto.split(',')[1]), 'image/jpeg',
        plato.replace(/[\\/:*?"<>|]/g, '') + ' · ' + Utilities.formatDate(new Date(), 'Europe/Madrid', 'yyyy-MM-dd HH-mm') + '.jpg');
      const arch = carpeta.createFile(b);
      arch.setSharing(DriveApp.Access.ANYONE_WITH_LINK, DriveApp.Permission.VIEW);
      foto = 'https://drive.google.com/file/d/' + arch.getId() + '/view';
    }
    const fecha = Utilities.formatDate(new Date(), 'Europe/Madrid', 'dd/MM/yyyy HH:mm');
    const poner = (n, v) => { if (c(n) > 0 && v !== undefined && v !== null) f.getRange(fila, c(n)).setValue(v); };
    poner('CANTIDAD POR PAX', d.cantidad === '' ? '' : d.cantidad);
    poner('UNIDAD', d.unidad);
    poner('MERMA %', d.merma === '' ? '' : d.merma);
    poner('MENAJE (pieza:por pax | …)', d.menaje);
    poner('RECIPIENTE COCINA', d.recipiente);
    poner('CUÁNTO CABE POR RECIPIENTE', d.cabe === '' ? '' : d.cabe);
    poner('NOTAS', d.notas);
    poner('RELLENADO POR', d.cocinero);
    poner('FECHA', fecha);
    if (foto) poner('FOTO', foto);
    poner('ESTADO', 'Por revisar');
    ss.getSheetByName('RESPUESTAS').appendRow([fecha, d.cocinero, plato, d.cantidad, d.unidad, d.merma, d.menaje,
      d.recipiente, d.cabe, d.notas, foto]);
    return json_({ ok: true, foto: foto, fecha: fecha });
  } catch (err) {
    return json_({ ok: false, error: String(err) });
  } finally {
    lock.releaseLock();
  }
}

/** Ejecutar una vez a mano desde el editor para dar permisos y crear las pestañas. */
function prueba() { preparar_(); DriveApp.getRootFolder(); }
