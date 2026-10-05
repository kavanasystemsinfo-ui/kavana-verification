# Verificación reproducible — Kavana Systems

Cada afirmación sobre pruebas en mis proyectos tiene que poder comprobarse, no
creerse. Este repositorio contiene el script que clona cada repositorio público,
ejecuta su suite con el mismo comando que usa su integración continua y publica
la tabla de resultados.

Los números salen de ejecutar las suites. Ninguno se copia de un README ni se
cuenta con un buscador de texto.

## Cómo se ejecuta

### Opción rápida (recomendada para reclutadores — **no necesita Docker**)

```bash
git clone https://github.com/kavanasystemsinfo-ui/kavana-verification.git
cd kavana-verification
python verificar.py --rapido
```

Ejecuta **6 de 8 suites** (todas las que no necesitan PostgreSQL) en ~3-4 minutos.
Cubre: Steelworks, Laboratorio ERP (muebles), BusRoad, RouteAI, Calculadora, Manufacturing frontend.

### Opción completa (necesita Docker Desktop)

```bash
python verificar.py
```

Ejecuta **todas las 8 suites** (incluye Manufacturing backend + Warehouse API con PostgreSQL real).
Tarda ~12-16 minutos. Requiere Docker Desktop corriendo.

### Otras opciones útiles

```bash
python verificar.py --listar                 # ver qué suites existen
python verificar.py --solo steelworks-backend warehouse-api
python verificar.py --mantener               # conservar los clones temporales
python verificar.py --json resultados.json   # salida JSON en vez de markdown
```

## Qué necesita en su máquina

| Herramienta | Windows | macOS | Linux | Para qué sirve |
|-------------|---------|-------|-------|----------------|
| `git` | ✅ | ✅ | ✅ | Clonar repos |
| `python` 3.11+ | ✅ | ✅ | ✅ | Ejecutar el script |
| `node` 20+ | ✅ | ✅ | ✅ | Suites JS/TS (npm test) |
| `uv` | ✅ | ✅ | ✅ | Suites Python (pytest) |
| `docker` | Docker Desktop | Docker Desktop | docker engine | **Solo** para Manufacturing backend y Warehouse API |

> **Sin Docker**: el script omite las 2 suites que necesitan PostgreSQL y lo dice explícitamente.
> **Con Docker**: levanta PostgreSQL 16 en el puerto 55433, ejecuta migraciones y seed, y tira el contenedor al terminar.

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

Si no quiere ejecutarlo todo, `--solo` permite lanzar una o dos suites y bajar
mucho el consumo: `python verificar.py --solo calculadora muebles-lab`.

Queda en disco solo lo que reutilizan otras ejecuciones: las cachés de `npm` y
`uv`, y la imagen de PostgreSQL si se usa Docker. En una máquina con Node y uv
ya instalados, el coste real es el de esas cachés.

## Qué comprueba

| Proyecto | Parte | Suite | ¿Necesita Docker? |
|---|---|---|---|
| Kavana Manufacturing | backend | Vitest, con PostgreSQL 16 y la cadena de migraciones aplicada | **Sí** |
| Kavana Manufacturing | frontend | Vitest | No |
| Kavana Steelworks | backend | pytest | No |
| Laboratorio ERP (muebles) | módulo y panel | pytest | No |
| Kavana BusRoad | backend | pytest | No |
| Kavana RouteAI | servidor | node:test | No |
| Calculadora Kavana | motor | node:test | No |
| Kavana Warehouse | API | Jest con PostgreSQL 16 | **Sí** |

El informe final está en [resultados.md](resultados.md), con la fecha de la
última ejecución y el número de pruebas que pasan en cada suite. Última
ejecución publicada: **625 pruebas en verde en 7 de 8 suites**.

## Nota de honestidad

La tabla cubre solo repositorios públicos. Hay trabajo cuyo código no se puede
publicar y que por eso no aparece aquí: si no se puede reproducir, no se cuenta,
y un trabajo con pruebas en verde no engorda el titular de esta página si nadie
puede ejecutarlas.

Este repositorio ejecuta lo que hay: ni una prueba de más, ni una de menos.

## Licencia

MIT.
