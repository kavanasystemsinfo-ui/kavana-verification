# Resultados de verificación

Ejecutado el 2026-10-05 14:36 UTC desde un clon limpio de cada repositorio.
Suites en verde: **7** de 8. Pruebas contadas: **625**.

| Proyecto | Parte | Pasan | Fallan | Estado |
|---|---|---|---|---|
| [Kavana Manufacturing](https://github.com/kavanasystemsinfo-ui/kavana-manufacturing) | backend | **55** | 0 | 65 s |
| [Kavana Manufacturing](https://github.com/kavanasystemsinfo-ui/kavana-manufacturing) | frontend | **211** | 1 | **fallo** |
| [Kavana Steelworks](https://github.com/kavanasystemsinfo-ui/kavana-steelworks) | backend | **251** | 0 | 154 s |
| [Laboratorio ERP (muebles)](https://github.com/kavanasystemsinfo-ui/ODOO_CRM) | módulo y panel | **85** | 0 | 3 s |
| [Kavana BusRoad](https://github.com/kavanasystemsinfo-ui/kavana-busroad) | backend | **37** | 0 | 6 s |
| [Kavana RouteAI](https://github.com/kavanasystemsinfo-ui/kavana-RouteAI) | servidor | **102** | 0 | 23 s |
| [Calculadora Kavana](https://github.com/kavanasystemsinfo-ui/CalculadoraKavana) | motor | **34** | 0 | 2 s |
| [Kavana Warehouse](https://github.com/kavanasystemsinfo-ui/Kavana-Warehouse) | API | **61** | 0 | 40 s |

**Total: 625 pruebas en verde.**

## Suites que no han pasado

### Kavana Manufacturing (frontend): fallo

```
+ Received

- [
-   "pending",
-   "in_progress",
- ]
+ []

 ❯ src/utils/order-filters.spec.ts:47:42
     45| describe('presets de estado', () => {
     46|   it('el preset por defecto mira las órdenes vivas, no el histórico', …
     47|     expect(DEFAULT_ORDER_FILTERS.status).toEqual(['pending', 'in_progr…
       |                                          ^
     48|   });
     49|

⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯⎯[1/1]⎯

npm error Lifecycle script `test` failed with error:
npm error code 1
npm error path /root/.hermes/profiles/kavana/cache/scratch/verificacion-1t70pncr/kavana-manufacturing-7d21b058/frontend
npm error workspace @kavana-manufacturing/frontend@1.0.0
npm error location /root/.hermes/profiles/kavana/cache/scratch/verificacion-1t70pncr/kavana-manufacturing-7d21b058/frontend
npm error command failed
npm error command sh -c vitest run
```
