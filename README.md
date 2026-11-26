# eventos-palau
## Eventos cifrado
La página `eventos/` va cifrada (el repositorio es público). Se abre con un patrón que se pide una vez por dispositivo.
Para subir una versión nueva: `EVENTOS_CLAVE=<patrón> python3 eventos/cifrar.py pagina-en-claro.html [historico.json] [carpeta-con-pdfs]` y después `python3 eventos/generar_ics.py` con la misma variable.
Para que el calendario se regenere solo cada día hace falta el secreto `EVENTOS_CLAVE` en GitHub (Settings → Secrets → Actions); sin él se deja como está.
