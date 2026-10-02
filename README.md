# Verificación reproducible — Kavana Systems

Cada afirmación sobre pruebas en mis proyectos tiene que poder comprobarse, no
creerse. Este repositorio contiene el script que clona cada repositorio público,
ejecuta su suite con el mismo comando que usa su integración continua y publica
la tabla de resultados.

Los números salen de ejecutar las suites. Ninguno se copia de un README ni se
cuenta con un buscador de texto.

## Cómo se ejecuta

```bash
git clone https://github.com/kavanasystemsinfo-ui/kavana-verification.git
cd kavana-verification
python verificar.py
```

Tarda unos 7 minutos porque instala dependencias y ejecuta las suites completas. Deja el informe en `resultados.md` y `resultados.json`.

Opciones útiles:

```bash
python verificar.py --listar                 # ver qué suites existen
python verificar.py --solo steelworks-backend warehouse-api
python verificar.py --mantener               # conservar los clones temporales
```

## Qué necesita

- `git` y `python` 3.11 o superior.
- `node` 20 o superior para las suites de JavaScript y TypeScript.
- `uv` para las suites de Python.
- `docker` solo para la suite que levanta PostgreSQL. Sin docker esa suite se
  omite y lo dice, no la salta en silencio.

## Cuánto ocupa

El repositorio pesa 252 KB al clonarlo. Una ejecución completa escribe unas 800
MB en un directorio temporal que se borra al terminar, la mayor parte
dependencias instaladas:

| Proyecto | Ocupa durante la ejecución | Qué lo ocupa |
|---|---|---|
| Kavana Warehouse | 298 MB | sus `node_modules` |
| Kavana Manufacturing | 284 MB | sus `node_modules` (raíz y frontend) |
| Kavana Steelworks | 125 MB | su entorno de Python |
| Kavana RouteAI | 65 MB | sus `node_modules` |
| Laboratorio ERP (muebles) | 14 MB | casi todo el repositorio |
| Kavana BusRoad | ~30 MB | entorno de Python efímero |
| Calculadora Kavana | 1 MB | solo el repositorio |

Si no quieres ejecutarlo todo, `--solo` permite lanzar una o dos suites y bajar
mucho el consumo: `python verificar.py --solo calculadora muebles-lab`.

Queda en disco solo lo que reutilizan otras ejecuciones: las cachés de `npm` y
`uv`, y la imagen de PostgreSQL si se usa Docker. En una máquina con Node y uv
ya instalados, el coste real es el de esas cachés.

## Qué comprueba

| Proyecto | Parte | Suite |
|---|---|---|
| Kavana Manufacturing | backend | Vitest, con PostgreSQL 16 y la cadena de migraciones aplicada |
| Kavana Manufacturing | frontend | Vitest |
| Kavana Steelworks | backend | pytest |
| Laboratorio ERP (muebles) | módulo y panel | pytest |
| Kavana BusRoad | backend | pytest |
| Kavana RouteAI | servidor | node:test |
| Calculadora Kavana | motor | node:test |
| Kavana Warehouse | API | Jest con PostgreSQL 16 |

El informe final está en [resultados.md](resultados.md), con la fecha de la
última ejecución y el número de pruebas que pasan en cada suite. Última
ejecución publicada: **1.387 pruebas en verde en las 8 suites**.

## Nota de honestidad

La tabla cubre solo repositorios públicos. Hay trabajo cuyo código no se puede
publicar y que por eso no aparece aquí: si no se puede reproducir, no se cuenta,
y un trabajo con pruebas en verde no engorda el titular de esta página si nadie
puede ejecutarlas.

Este repositorio ejecuta lo que hay: ni una prueba de más, ni una de menos.

## Licencia

MIT.
