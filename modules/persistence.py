"""
Módulo de Persistencia
=========================
Serializa y restaura el estado completo de un proyecto (generación,
capacidad, rutas y finanzas) en un único archivo JSON, para que el
usuario pueda guardar su trabajo y continuarlo después.
"""

import json
from dataclasses import asdict


def guardar_proyecto(ruta_archivo: str, estado: dict) -> None:
    with open(ruta_archivo, "w", encoding="utf-8") as f:
        json.dump(estado, f, ensure_ascii=False, indent=2)


def cargar_proyecto(ruta_archivo: str) -> dict:
    with open(ruta_archivo, "r", encoding="utf-8") as f:
        return json.load(f)


def dataclass_list_to_dicts(lista) -> list:
    return [asdict(obj) for obj in lista]
