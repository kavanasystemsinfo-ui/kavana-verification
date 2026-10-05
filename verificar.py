#!/usr/bin/env python3
"""Verificación reproducible de los proyectos públicos de Kavana Systems.

Clona cada repositorio en un directorio temporal, ejecuta las suites de pruebas
con los comandos que usa su propia integración continua y publica la tabla de
resultados. Cualquiera puede ejecutarlo y comprobar los números.

Uso:
    python verificar.py                 # todas las suites (necesita Docker)
    python verificar.py --rapido        # solo suites sin Docker (6 de 8)
    python verificar.py --solo steelworks warehouse
    python verificar.py --json resultados.json
    python verificar.py --listar

Requisitos por SO:
    Windows: git, python 3.11+, node 20+, uv, Docker Desktop (opcional)
    macOS:   git, python 3.11+, node 20+, uv, Docker Desktop (opcional)
    Linux:   git, python 3.11+, node 20+, uv, docker (opcional)
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
from dataclasses import dataclass, field
from pathlib import Path

OWNER = "kavanasystemsinfo-ui"
GITHUB = f"https://github.com/{OWNER}"
IS_WINDOWS = platform.system() == "Windows"

# Cada suite declara el comando de instalación y el de pruebas tal y como los
# usa su pipeline. Los números que publica este script salen de ejecutarlos.
SUITES = [
    {
        "id": "manufacturing-backend",
        "proyecto": "Kavana Manufacturing",
        "parte": "backend",
        "repo": "kavana-manufacturing",
        "dir": "backend",
        "runner": "vitest",
        "instalar": ["npm", "ci", "--no-audit", "--no-fund"],
        "probar": ["npm", "test"],
        "requiere": "node+docker",
        # La suite del backend ejecuta SQL de verdad (aislamiento entre clientes
        # y producción). Sin base, 48 pruebas quedan saltadas y la cifra que se
        # publica sale más baja que la real: se levanta una base y se le aplica
        # la cadena de migraciones y el sembrado, igual que hace la integración.
        "necesita_postgres": True,
        "preparar": [["node", "database/scripts/e2e-setup.js"]],
    },
    {
        "id": "manufacturing-frontend",
        "proyecto": "Kavana Manufacturing",
        "parte": "frontend",
        "repo": "kavana-manufacturing",
        "dir": "frontend",
        "runner": "vitest",
        "instalar": ["npm", "ci", "--no-audit", "--no-fund"],
        "probar": ["npm", "test"],
        "requiere": "node",
    },
    {
        "id": "steelworks-backend",
        "proyecto": "Kavana Steelworks",
        "parte": "backend",
        "repo": "kavana-steelworks",
        "dir": "backend",
        "runner": "pytest",
        "instalar": ["uv", "sync", "--all-groups"],
        "probar": ["uv", "run", "pytest", "tests/", "-q"],
        "requiere": "uv",
    },
    {
        "id": "muebles-lab",
        "proyecto": "Laboratorio ERP (muebles)",
        "parte": "módulo y panel",
        "repo": "ODOO_CRM",
        "dir": ".",
        "runner": "pytest",
        "instalar": None,
        "probar": [
            "uv", "run", "--with", "pytest",
            "--with-requirements", "requirements-dev.txt",
            "python", "-m", "pytest", "tests",
        ],
        "requiere": "uv",
    },
    {
        "id": "busroad-backend",
        "proyecto": "Kavana BusRoad",
        "parte": "backend",
        "repo": "kavana-busroad",
        "dir": "backend",
        "runner": "pytest",
        "instalar": None,
        "probar": [
            "uv", "run", "--with-requirements", "requirements.txt",
            "--with", "pytest", "--with", "pytest-asyncio",
            "python", "-m", "pytest", "-q",
        ],
        "requiere": "uv",
    },
    {
        "id": "routeai-server",
        "proyecto": "Kavana RouteAI",
        "parte": "servidor",
        "repo": "kavana-RouteAI",
        "dir": "server",
        "runner": "node",
        "instalar": ["npm", "ci", "--no-audit", "--no-fund"],
        "probar": ["npm", "test"],
        "requiere": "node",
    },
    {
        "id": "calculadora",
        "proyecto": "Calculadora Kavana",
        "parte": "motor",
        "repo": "CalculadoraKavana",
        "dir": "tests",
        "runner": "node",
        "instalar": None,
        "probar": ["npm", "test"],
        "requiere": "node",
    },
    {
        "id": "warehouse-api",
        "proyecto": "Kavana Warehouse",
        "parte": "API",
        "repo": "Kavana-Warehouse",
        "dir": ".",
        "runner": "jest",
        "instalar": ["npm", "ci", "--no-audit", "--no-fund"],
        "probar": ["npm", "test"],
        "requiere": "node+docker",
        "necesita_postgres": True,
        "preparar": [["npx", "prisma", "generate"],
                     ["npx", "prisma", "migrate", "deploy"],
                     ["node", "prisma/seed.js"]],
    },
]

PATRONES = {
    "vitest": r"Tests\s+\d+\s+failed\s*\|\s*(\d+)\s+passed\s*\(",
    "pytest": r"(\d+)\s+passed",
    "jest": r"Tests:\s+(\d+)\s+passed",
    # El runner de Node cambia el resumen según la versión: unas veces «ℹ pass N»
    # y otras «# pass N» (formato TAP). Aceptar los dos evita dar por fallida
    # una suite que ha pasado entera, que es la peor forma de equivocarse.
    "node": r"(?:ℹ|#) pass (\d+)",
    "maven": r"Tests run:\s*(\d+),\s*Failures:\s*(\d+),\s*Errors:\s*(\d+)",
}


@dataclass
class Resultado:
    id: str
    proyecto: str
    parte: str
    repo: str
    url: str
    estado: str = "pendiente"
    pasan: int = 0
    fallan: int = 0
    segundos: float = 0.0
    detalle: str = ""
    log: list[str] = field(default_factory=list)

    def fila(self) -> str:
        verde = f"**{self.pasan}**" if self.pasan else "—"
        if self.estado == "ok":
            return f"| [{self.proyecto}]({self.url}) | {self.parte} | {verde} | 0 | {self.segundos:.0f} s |"
        if self.estado == "omitida":
            return f"| [{self.proyecto}]({self.url}) | {self.parte} | — | — | omitida: {self.detalle} |"
        return f"| [{self.proyecto}]({self.url}) | {self.parte} | {verde} | {self.fallan} | **{self.estado}** |"


def hay(comando: str) -> bool:
    return shutil.which(comando) is not None


SECRETOS = re.compile(r"(_API_KEY|_TOKEN|_SECRET|_PASSWORD|PASSWORD|CREDENTIALS)$", re.I)


def entorno_limpio(extra: dict | None = None) -> dict:
    """Entorno sin nada que venga de mi máquina.

    Fuera VIRTUAL_ENV y PYTHONPATH, porque un venv externo cuela paquetes que
    rompen la colección de pruebas de un proyecto ajeno. Y fuera claves, tokens
    y contraseñas heredados: una suite que cambia de rama según si hay una clave
    en el entorno no es reproducible, y el resultado que publica este script
    tiene que salir de la misma situación que tendrá quien lo ejecute.
    """
    env = {
        k: v for k, v in os.environ.items()
        if k not in ("VIRTUAL_ENV", "PYTHONPATH", "DATABASE_URL") and not SECRETOS.search(k)
    }
    env.setdefault("CI", "1")
    env.setdefault("NODE_ENV", "test")
    if extra:
        # Explícitas y solo para esta suite: la conexión a la base de datos de
        # pruebas se inyecta aquí, no se hereda del entorno de quien ejecuta.
        env.update(extra)
    return env


def ejecutar(cmd: list[str], cwd: Path, timeout: int,
             extra_env: dict | None = None) -> tuple[int, str]:
    """Ejecuta comando. En Windows, usa shell=True para resolver .cmd (npm, npx, etc.)."""
    kwargs = dict(
        cwd=str(cwd),
        env=entorno_limpio(extra_env),
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    # En Windows, npm/node/npx/uv son .cmd y necesitan shell=True para ejecutarse
    if IS_WINDOWS and cmd and cmd[0] in ("npm", "node", "npx", "uv", "npx.cmd", "npm.cmd", "node.exe"):
        kwargs["shell"] = True
        # Convertir lista a string para shell=True
        cmd_str = " ".join(cmd)
    else:
        cmd_str = cmd

    try:
        r = subprocess.run(cmd_str, **kwargs)
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"tiempo agotado tras {timeout} s"
    except FileNotFoundError as e:
        return 127, f"comando no encontrado: {e}"


def _directorio_unico(base: Path, repo: str) -> Path:
    """Devuelve un path único para evitar colisiones y problemas de permisos en Windows."""
    sufijo = f"{repo}-{uuid.uuid4().hex[:8]}"
    return base / sufijo


def _limpiar_windows(path: Path) -> None:
    """Limpieza robusta en Windows: reintentos + fallback a cmd rmdir."""
    if not IS_WINDOWS:
        shutil.rmtree(path, ignore_errors=True)
        return
    for intento in range(3):
        try:
            shutil.rmtree(path, ignore_errors=False)
            return
        except PermissionError:
            time.sleep(0.5 * (intento + 1))
    # Fallback: cmd rmdir /s /q
    subprocess.run(["cmd", "/c", "rmdir", "/s", "/q", str(path)], capture_output=True)


def clonar(repo: str, destino_base: Path) -> tuple[int, str, Path]:
    """Clona en un directorio único y devuelve (codigo, salida, path_real)."""
    destino = _directorio_unico(destino_base, repo)
    codigo, salida = ejecutar(
        ["git", "clone", "--depth", "1", f"{GITHUB}/{repo}.git", str(destino)],
        destino.parent, 300,
    )
    return codigo, salida, destino


def parsear(runner: str, salida: str) -> tuple[int, int]:
    if runner == "maven":
        # Maven imprime una línea por clase de prueba y luego el resumen: el
        # total es la última, no la primera.
        todas = re.findall(PATRONES["maven"], salida)
        if not todas:
            return 0, 0
        pasan, fallos, errores = todas[-1]
        return int(pasan), int(fallos) + int(errores)
    m = re.search(PATRONES[runner], salida, re.M)
    if not m:
        # Fallbacks para vitest: varios formatos de salida
        if runner == "vitest":
            # Formato con fallos: «Tests  1 failed | 211 passed (212)»
            fb = re.search(r"Tests\s+\d+\s+failed\s*\|\s*(\d+)\s+passed\s*\(", salida, re.M)
            if fb:
                return int(fb.group(1)), 0
            # Formato todo pasa: «Tests  555 passed | 50 skipped (605)»
            fb = re.search(r"Tests\s+(\d+)\s+passed\s*\|\s*\d+\s+skipped", salida, re.M)
            if fb:
                return int(fb.group(1)), 0
            # Formato solo test files: «Test Files  52 passed | 3 skipped (55)»
            fb = re.search(r"Test Files\s+(\d+)\s+passed", salida, re.M)
            if fb:
                return int(fb.group(1)), 0
        return 0, 0
    fallos = 0
    if runner == "node":
        f = re.search(r"(?:ℹ|#) fail (\d+)", salida, re.M)
        fallos = int(f.group(1)) if f else 0
    elif runner in ("jest", "vitest"):
        # vitest/jest pueden salir con formato «Tests  1 failed | 211 passed (212)»
        # o «Tests: 211 passed, 1 failed». Intentar ambos.
        f = re.search(r"Tests:?\s+(\d+)\s+failed", salida, re.M)
        if not f:
            f = re.search(r"Tests\s+\d+\s+failed\s*\|\s*(\d+)\s+passed", salida, re.M)
        fallos = int(f.group(1)) if f else 0
    elif runner == "pytest":
        f = re.search(r"(\d+)\s+failed", salida)
        fallos = int(f.group(1)) if f else 0
    return int(m.group(1)), fallos


def levantar_postgres(nombre: str) -> str | None:
    """Devuelve la URL de conexión si consigue levantar el contenedor."""
    if not hay("docker"):
        return None
    subprocess.run(["docker", "rm", "-f", nombre], capture_output=True, text=True)
    r = subprocess.run(
        ["docker", "run", "-d", "--name", nombre,
         "-e", "POSTGRES_PASSWORD=test", "-e", "POSTGRES_USER=kavana",
         "-e", "POSTGRES_DB=kavana_verify", "-p", "55433:5432", "postgres:16"],
        capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0:
        return None
    for _ in range(30):
        chk = subprocess.run(
            ["docker", "exec", nombre, "pg_isready", "-U", "kavana"],
            capture_output=True, text=True,
        )
        if "accepting" in chk.stdout:
            return "postgresql://kavana:test@127.0.0.1:55433/kavana_verify"
        time.sleep(2)
    return None


def ejecutar_suite(suite: dict, raiz: Path) -> Resultado:
    res = Resultado(
        id=suite["id"], proyecto=suite["proyecto"], parte=suite["parte"],
        repo=suite["repo"], url=f"{GITHUB}/{suite['repo']}",
    )
    faltan = []
    if "node" in suite["requiere"] and not hay("node"):
        faltan.append("node")
    if "uv" in suite["requiere"] and not hay("uv"):
        faltan.append("uv")
    if "maven" in suite["requiere"] and not (hay("mvn") and hay("java")):
        faltan.append("maven/java")
    if suite.get("necesita_postgres") and not hay("docker"):
        faltan.append("docker")
    if faltan:
        res.estado = "omitida"
        res.detalle = "falta " + ", ".join(faltan)
        return res

    arranque = time.time()
    codigo, salida, destino = clonar(suite["repo"], raiz)
    if codigo != 0:
        res.estado = "error de clonado"
        res.detalle = salida.strip().splitlines()[-1][:120] if salida.strip() else "git clone falló"
        return res

    trabajo = destino if suite["dir"] == "." else destino / suite["dir"]
    if not trabajo.exists():
        res.estado = "error"
        res.detalle = f"no existe el directorio {suite['dir']}"
        return res

    contenedor = None
    datos: dict = {}
    if suite.get("necesita_postgres"):
        url = levantar_postgres(f"verify-{suite['id']}")
        if not url:
            res.estado = "omitida"
            res.detalle = "no se pudo levantar PostgreSQL"
            return res
        contenedor = f"verify-{suite['id']}"
        datos = {"DATABASE_URL": url}

    try:
        if suite["instalar"]:
            codigo, salida = ejecutar(suite["instalar"], trabajo, 1200)
            if codigo != 0:
                res.estado = "fallo al instalar"
                res.log = salida.strip().splitlines()[-20:]
                return res
        if suite.get("preparar"):
            for paso in suite["preparar"]:
                codigo, salida = ejecutar(paso, destino, 900, extra_env=datos)
                if codigo != 0:
                    res.estado = "fallo al preparar la base de datos"
                    res.log = salida.strip().splitlines()[-20:]
                    return res
        codigo, salida = ejecutar(suite["probar"], trabajo, 1800, extra_env=datos)
        res.pasan, res.fallan = parsear(suite["runner"], salida)
        res.log = salida.strip().splitlines()[-25:]
        if codigo == 0 and res.pasan:
            res.estado = "ok"
        else:
            res.estado = "fallo"
    finally:
        if contenedor:
            subprocess.run(["docker", "rm", "-f", contenedor], capture_output=True, text=True)
    res.segundos = time.time() - arranque
    return res


def informe(resultados: list[Resultado], destino_md: Path, destino_json: Path) -> int:
    total = sum(r.pasan for r in resultados if r.estado == "ok")
    fallos = [r for r in resultados if r.estado not in ("ok", "omitida")]
    lineas = [
        "# Resultados de verificación",
        "",
        f"Ejecutado el {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())} desde un clon limpio de cada repositorio.",
        f"Suites en verde: **{sum(1 for r in resultados if r.estado == 'ok')}** de {len(resultados)}. "
        f"Pruebas contadas: **{total}**.",
        "",
        "| Proyecto | Parte | Pasan | Fallan | Estado |",
        "|---|---|---|---|---|",
    ]
    lineas += [r.fila() for r in resultados]
    lineas += ["", f"**Total: {total} pruebas en verde.**", ""]
    if fallos:
        lineas += ["## Suites que no han pasado", ""]
        for r in fallos:
            lineas.append(f"### {r.proyecto} ({r.parte}): {r.estado}")
            if r.detalle:
                lineas.append(f"{r.detalle}")
            if r.log:
                lineas += ["", "```", *r.log, "```"]
            lineas.append("")
    destino_md.write_text("\n".join(lineas), encoding="utf-8")
    destino_json.write_text(
        json.dumps(
            {
                "fecha": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "total_en_verde": total,
                "suites": [r.__dict__ for r in resultados],
            },
            ensure_ascii=False, indent=1,
        ),
        encoding="utf-8",
    )
    print("\n".join(lineas[:8]))
    print(f"\nInforme escrito en {destino_md} y {destino_json}")
    return 1 if fallos else 0


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--solo", nargs="*", help="ejecutar solo estas suites (por id o por repo)")
    ap.add_argument("--rapido", action="store_true", help="solo suites sin Docker/PostgreSQL (6 de 8)")
    ap.add_argument("--listar", action="store_true", help="listar las suites y salir")
    ap.add_argument("--json", default="resultados.json", help="ruta del informe JSON")
    ap.add_argument("--markdown", default="resultados.md", help="ruta del informe markdown")
    ap.add_argument("--mantener", action="store_true", help="no borrar los clones temporales")
    args = ap.parse_args()

    if args.listar:
        for s in SUITES:
            print(f"{s['id']:24} {s['proyecto']:22} {s['parte']:10} {s['requiere']}")
        return 0

    elegidas = SUITES
    if args.rapido:
        # Excluir las que necesitan PostgreSQL/Docker
        elegidas = [s for s in SUITES if not s.get("necesita_postgres")]
        print(f"Modo --rapido: {len(elegidas)} suites (sin Docker/PostgreSQL)\n")
    if args.solo:
        buscados = set(args.solo)
        elegidas = [s for s in SUITES if s["id"] in buscados or s["repo"] in buscados]
        if not elegidas:
            print("No hay suites que coincidan con --solo", file=sys.stderr)
            return 2

    raiz = Path(tempfile.mkdtemp(prefix="verificacion-"))
    print(f"Clones temporales en {raiz}\n")
    resultados = []
    try:
        for suite in elegidas:
            print(f"→ {suite['proyecto']} ({suite['parte']})...", flush=True)
            r = ejecutar_suite(suite, raiz)
            resultados.append(r)
            print(f"   {r.estado}: {r.pasan} pasan, {r.fallan} fallan ({r.segundos:.0f} s)"
                  + (f" [{r.detalle}]" if r.detalle else ""), flush=True)
    finally:
        if not args.mantener and raiz.exists():
            _limpiar_windows(raiz)

    return informe(resultados, Path(args.markdown), Path(args.json))


if __name__ == "__main__":
    sys.exit(main())
