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

Tarda entre 10 y 15 minutos porque instala dependencias y ejecuta las suites
completas. Deja el informe en `resultados.md` y `resultados.json`.

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
- Java 21 y Maven para la suite de Java.
- `docker` solo para la suite que levanta PostgreSQL. Sin docker esa suite se
  omite y lo dice, no la salta en silencio.

## Qué comprueba

| Proyecto | Parte | Suite |
|---|---|---|
| Kavana Manufacturing | backend | Vitest |
| Kavana Manufacturing | frontend | Vitest |
| Kavana Steelworks | backend | pytest |
| Mecania | aplicación | JUnit y Failsafe con Maven |
| Kavana BusRoad | backend | pytest |
| Kavana RouteAI | servidor | node:test |
| Calculadora Kavana | motor | node:test |
| Kavana Warehouse | API | Jest con PostgreSQL 16 |

El informe final está en [resultados.md](resultados.md), con la fecha de la
última ejecución y el número de pruebas que pasan en cada suite. Última
ejecución publicada: **1.263 pruebas en verde en las 8 suites**.

## Nota de honestidad

Hay un proyecto que no aparece aquí: un laboratorio de ERP sobre Odoo Community
(scoring de leads, OCR local de facturas, impuestos españoles, catálogo) cuya
suite tiene 452 pruebas en verde. Su repositorio es privado, así que cualquiera
que lo lea no puede reproducirlo y por eso queda fuera de la tabla y del total.
Si algún día ese trabajo se publica, entra en el script como una suite más.

## Licencia

MIT.
