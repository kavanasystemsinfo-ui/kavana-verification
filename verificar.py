#!/usr/bin/env python3
"""Verificación reproducible de los proyectos públicos de Kavana Systems.

Clona cada repositorio en un directorio temporal, ejecuta las suites de pruebas
con los comandos que usa su propia integración continua y publica la tabla de
resultados. Cualquiera puede ejecutarlo y comprobar los números.

Uso:
    python verificar.py                 # todas las suites
    python verificar.py --solo steelworks warehouse
    python verificar.py --json resultados.json
    python verificar.py --listar
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path

OWNER = "kavanasystemsinfo-ui"
GITHUB = f"https://github.com/{OWNER}"

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
        "requiere": "node",
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
        "id": "mecania",
        "proyecto": "Mecania",
        "parte": "aplicación",
        "repo": "mecania",
        "dir": ".",
        "runner": "maven",
        "instalar": None,
        "probar": ["mvn", "--batch-mode", "--no-transfer-progress", "verify"],
        "requiere": "java+maven",
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
    },
]

PATRONES = {
    "vitest": r"Tests\s+(\d+)\s+passed",
    "pytest": r"(\d+)\s+passed",
    "jest": r"Tests:\s+(\d+)\s+passed",
    "node": r"^ℹ pass (\d+)",
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
    try:
        r = subprocess.run(
            cmd, cwd=str(cwd), env=entorno_limpio(extra_env), capture_output=True,
            text=True, timeout=timeout,
        )
        return r.returncode, (r.stdout or "") + (r.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, f"tiempo agotado tras {timeout} s"
    except FileNotFoundError as e:
        return 127, f"comando no encontrado: {e}"


def clonar(repo: str, destino: Path) -> tuple[int, str]:
    if destino.exists():
        shutil.rmtree(destino)
    return ejecutar(
        ["git", "clone", "--depth", "1", f"{GITHUB}/{repo}.git", str(destino)],
        destino.parent, 300,
    )


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
        return 0, 0
    fallos = 0
    if runner == "node":
        f = re.search(r"^ℹ fail (\d+)", salida, re.M)
        fallos = int(f.group(1)) if f else 0
    elif runner in ("jest", "vitest"):
        f = re.search(r"Tests:\s+(\d+)\s+failed", salida)
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
    destino = raiz / suite["repo"]
    codigo, salida = clonar(suite["repo"], destino)
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
        if suite.get("necesita_postgres"):
            for paso in (["npx", "prisma", "generate"],
                         ["npx", "prisma", "migrate", "deploy"],
                         ["node", "prisma/seed.js"]):
                codigo, salida = ejecutar(paso, trabajo, 600, extra_env=datos)
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
            shutil.rmtree(raiz, ignore_errors=True)

    return informe(resultados, Path(args.markdown), Path(args.json))


if __name__ == "__main__":
    sys.exit(main())
