# Resultados de verificación

Ejecutado el 2026-10-01 17:02 UTC desde un clon limpio de cada repositorio.
Suites en verde: **7** de 8. Pruebas contadas: **1129**.

| Proyecto | Parte | Pasan | Fallan | Estado |
|---|---|---|---|---|
| [Kavana Manufacturing](https://github.com/kavanasystemsinfo-ui/kavana-manufacturing) | backend | **534** | 0 | 77 s |
| [Kavana Manufacturing](https://github.com/kavanasystemsinfo-ui/kavana-manufacturing) | frontend | **207** | 0 | 55 s |
| [Kavana Steelworks](https://github.com/kavanasystemsinfo-ui/kavana-steelworks) | backend | **251** | 0 | 170 s |
| [Mecania](https://github.com/kavanasystemsinfo-ui/mecania) | aplicación | **5** | 0 | 214 s |
| [Kavana BusRoad](https://github.com/kavanasystemsinfo-ui/kavana-busroad) | backend | **37** | 0 | 14 s |
| [Kavana RouteAI](https://github.com/kavanasystemsinfo-ui/kavana-RouteAI) | servidor | **101** | 0 | **fallo** |
| [Calculadora Kavana](https://github.com/kavanasystemsinfo-ui/CalculadoraKavana) | motor | **34** | 0 | 2 s |
| [Kavana Warehouse](https://github.com/kavanasystemsinfo-ui/Kavana-Warehouse) | API | **61** | 0 | 55 s |

**Total: 1129 pruebas en verde.**

## Suites que no han pasado

### Kavana RouteAI (servidor): fallo

```
ℹ tests 102
ℹ suites 0
ℹ pass 101
ℹ fail 1
ℹ cancelled 0
ℹ skipped 0
ℹ todo 0
ℹ duration_ms 47911.927229

✖ failing tests:

test at tests/api.test.js:379:1
✖ POST /assistant sin OPENROUTER_API_KEY no inventa respuestas (20934.345222ms)
  AssertionError [ERR_ASSERTION]: con clave, respuesta RAG válida
      at TestContext.<anonymous> (file:///tmp/verificacion-dk_r4456/kavana-RouteAI/server/tests/api.test.js:391:14)
      at process.processTicksAndRejections (node:internal/process/task_queues:104:5)
      at async Test.run (node:internal/test_runner/test:1409:7)
      at async Test.processPendingSubtests (node:internal/test_runner/test:974:7) {
    generatedMessage: false,
    code: 'ERR_ASSERTION',
    actual: false,
    expected: true,
    operator: '==',
    diff: 'simple'
  }
```
