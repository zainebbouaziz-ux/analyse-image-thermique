"""
metadata.py
-----------

Lecture des métadonnées radiométriques et de géoréférencement embarquées
dans un fichier thermique DJI (R-JPEG), via exiftool.

Ces métadonnées sont nécessaires au moteur de conversion raw -> température
(DJI Thermal SDK / thermal_parser) : émissivité, distance à la cible,
humidité relative, température réfléchie apparente, température
atmosphérique. Elles sont enregistrées par défaut par la caméra au moment
de la prise de vue et peuvent être surchargées si les conditions réelles
de mesure sont mieux connues (ex: relevé terrain lors d'une inspection PV).

Nécessite le binaire `exiftool` installé sur le système
(https://exiftool.org) et le paquet python `PyExifTool`.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Optional


def _parse_number(value) -> float:
    """Extrait un nombre flottant d'une valeur exiftool, quel que soit son format.

    exiftool renvoie souvent des valeurs avec unité ou symbole collés au
    nombre, ex: "5 m", "50 %", "23.0 C", "70%". Cette fonction extrait le
    premier nombre (signe + décimales incluses) trouvé dans la chaîne.
    """
    if isinstance(value, (int, float)):
        return float(value)
    match = re.search(r"[-+]?\d+(?:\.\d+)?", str(value))
    if not match:
        raise ValueError(f"Impossible d'extraire un nombre depuis: {value!r}")
    return float(match.group())


@dataclass
class RadiometricParams:
    """Paramètres radiométriques nécessaires à la correction raw -> température.

    Ces valeurs correspondent exactement aux entrées attendues par le
    DJI Thermal SDK (fonction de mesure). Elles peuvent être lues depuis
    l'EXIF de l'image (valeurs saisies sur le drone/la télécommande avant
    le vol) ou surchargées manuellement si l'opérateur dispose de mesures
    terrain plus précises (recommandé pour une inspection PV rigoureuse).
    """

    emissivity: float = 0.95          # émissivité de la cible (ex: ~0.9-0.95 pour un module PV)
    object_distance_m: float = 5.0    # distance caméra -> cible, en mètres
    relative_humidity_pct: float = 70.0   # humidité relative de l'air, en %
    reflected_temperature_c: float = 23.0  # température apparente réfléchie, en degrés C
    atmospheric_temperature_c: Optional[float] = None  # si None -> égale à reflected_temperature_c
    ir_window_transmission: float = 1.0     # transmission d'une éventuelle fenêtre IR (1.0 = aucune)
    ir_window_temperature_c: Optional[float] = None

    def with_overrides(self, **kwargs) -> "RadiometricParams":
        """Retourne une copie avec certains champs surchargés.

        Exemple:
            params = read_dji_metadata(path).with_overrides(
                emissivity=0.92, relative_humidity_pct=55.0
            )
        """
        return replace(self, **kwargs)


def _run_exiftool_json(image_path: Path) -> dict:
    """
    Exécute ExifTool et retourne les métadonnées au format JSON.
    Cherche d'abord ExifTool dans le PATH, sinon utilise exiftool.exe
    situé à la racine du projet.
    """

    exiftool = shutil.which("exiftool")

    if exiftool is None:
        # ...\thermal_pv\thermal_reader\metadata.py
        project_root = Path(__file__).resolve().parent.parent
        exiftool_path = project_root / "exiftool.exe"

        if exiftool_path.exists():
            exiftool = str(exiftool_path)
        else:
            raise RuntimeError(
                f"ExifTool introuvable.\n"
                f"Attendu dans : {exiftool_path}"
            )

    result = subprocess.run(
        [exiftool, "-j", "-G", str(image_path)],
        capture_output=True,
        text=True,
        check=True,
    )

    data = json.loads(result.stdout)
    return data[0] if data else {}


def read_dji_metadata(image_path: str | Path) -> RadiometricParams:
    """Lit les paramètres radiométriques par défaut embarqués par la caméra DJI.

    Les noms de tags EXIF DJI usuels (peuvent varier légèrement selon le
    modèle de caméra / version firmware) :
        Emissivity, ObjectDistance, RelativeHumidity,
        ReflectedApparentTemperature, AtmosphericTemperature

    Si un tag est absent, la valeur par défaut de RadiometricParams est
    conservée et un avertissement est affiché.
    """
    image_path = Path(image_path)
    tags = _run_exiftool_json(image_path)

    def _get(*candidates, default=None):
        for c in candidates:
            for key in tags:
                if key.split(":")[-1] == c:
                    return tags[key]
        return default

    params = RadiometricParams()

    emissivity = _get("Emissivity")
    distance = _get("ObjectDistance")
    humidity = _get("RelativeHumidity")
    reflected = _get("ReflectedApparentTemperature")
    atmospheric = _get("AtmosphericTemperature")

    missing = []
    if emissivity is not None:
        params.emissivity = _parse_number(emissivity)
    else:
        missing.append("Emissivity")

    if distance is not None:
        params.object_distance_m = _parse_number(distance)
    else:
        missing.append("ObjectDistance")

    if humidity is not None:
        params.relative_humidity_pct = _parse_number(humidity)
    else:
        missing.append("RelativeHumidity")

    if reflected is not None:
        params.reflected_temperature_c = _parse_number(reflected)
    else:
        missing.append("ReflectedApparentTemperature")

    if atmospheric is not None:
        params.atmospheric_temperature_c = _parse_number(atmospheric)
    else:
        params.atmospheric_temperature_c = params.reflected_temperature_c

    if missing:
        print(
            f"[metadata] Attention: tags EXIF absents pour {image_path.name}: "
            f"{', '.join(missing)}. Valeurs par défaut utilisées pour ces champs. "
            "Pour une mesure précise, vérifiez/renseignez-les manuellement via "
            "RadiometricParams.with_overrides(...)."
        )

    return params


def read_image_resolution(image_path: str | Path) -> tuple[int, int]:
    """Retourne (width, height) de l'image, lus via exiftool.

    Nécessaire pour reconstituer la forme (H, W) d'une matrice de
    températures brutes exportée par l'outil CLI officiel `dji_irp`, qui
    ne produit qu'un flux de données plat (raw), sans en-tête de forme.
    """
    image_path = Path(image_path)
    tags = _run_exiftool_json(image_path)

    def _get(*candidates):
        for c in candidates:
            for key in tags:
                if key.split(":")[-1] == c:
                    return tags[key]
        return None

    width = _get("ImageWidth", "ExifImageWidth")
    height = _get("ImageHeight", "ExifImageHeight")
    if width is None or height is None:
        raise RuntimeError(
            f"Impossible de déterminer la résolution de {image_path.name} via exiftool."
        )
    return int(_parse_number(width)), int(_parse_number(height))


def read_gps(image_path: str | Path) -> Optional[dict]:
    """Lit les informations GPS (pour géoréférencement / export GeoTIFF).

    Retourne None si l'image n'est pas géolocalisée.
    """
    image_path = Path(image_path)
    tags = _run_exiftool_json(image_path)

    lat = tags.get("Composite:GPSLatitude") or tags.get("EXIF:GPSLatitude")
    lon = tags.get("Composite:GPSLongitude") or tags.get("EXIF:GPSLongitude")
    alt = tags.get("Composite:GPSAltitude") or tags.get("EXIF:GPSAltitude")

    if lat is None or lon is None:
        return None

    return {
        "latitude": float(lat),
        "longitude": float(lon),
        "altitude_m": _parse_number(alt) if alt is not None else None,
    }