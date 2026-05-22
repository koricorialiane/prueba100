# Protocolo Titan

Repositorio limpio con solo lo necesario para:

- abrir la pagina web HTML del proyecto;
- conservar el codigo Python de calculos;
- volver a generar la web si hace falta.

## Contenido

- `index.html`: acceso rapido a la web.
- `docs/index.html`: dashboard estatico listo para abrir o publicar en GitHub Pages.
- `docs/assets/figures/`: figuras usadas por la web.
- `src/protocolo_titan/`: codigo fuente de calculos, graficas y generacion del sitio.
- `tests/`: pruebas automaticas.

## Abrir la web

Abre directamente:

- `index.html`

o:

- `docs/index.html`

## Ejecutar el codigo Python

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

pip install -r requirements.txt
set PYTHONPATH=src
python -m protocolo_titan.main
```

## Publicar en GitHub Pages

Usa la carpeta `docs/` como origen de GitHub Pages.
