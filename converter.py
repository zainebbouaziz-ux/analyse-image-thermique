"""
converter.py
------------

Cœur du pipeline : transforme une image thermique radiométrique DJI
(R-JPEG) en une matrice NumPy Float32 de températures réelles (en degrés Celsius),
de dimensions (H, W), où chaque élément correspond à la température
physique du pixel correspondant.

Moteur de conversion utilisé :
    **`dji_irp` (CLI officiel DJI, RECOMMANDÉ)** — l'exécutable officiel
    fourni dans le DJI Thermal SDK téléchargé depuis dji.com. 
    C'est le moteur le plus fiable : binaire officiel, il supporte 
    nativement la surcharge de tous les paramètres radiométriques. 
    Nécessite de définir la variable d'environnement `DJI_IRP_EXE_PATH` 
    avec le chemin complet vers `dji_irp.exe`.

Pourquoi passer par un SDK officiel et non réimplémenter la formule soi-même :
    DJI ne publie pas les constantes de calibration capteur ni la formule
    exacte de correction radiométrique (contrairement à FLIR). Le SDK officiel est la seule source scientifiquement
    fiable pour ce calcul.
"""

from __future__ import annotations

import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

import numpy as np

from .metadata import RadiometricParams, read_dji_metadata, read_gps, read_image_resolution


@dataclass
class ThermalImage:
    """Conteneur pour une image thermique convertie en températures."""

    temperature_c: np.ndarray      # Matrice (H, W) float32, en degrés Celsius
    params: RadiometricParams      # Paramètres radiométriques utilisés pour la conversion
    source_path: Path
    gps: Optional[dict] = None     # Latitude / longitude / altitude si disponibles

    @property
    def shape(self) -> tuple[int, int]:
        return self.temperature_c.shape

    def temperature_at(self, x: int, y: int) -> float:
        """Retourne la température (en degrés Celsius) au pixel (x, y).

        Convention : x = colonne (largeur), y = ligne (hauteur),
        origine (0, 0) en haut à gauche, comme pour une image classique.
        """
        h, w = self.temperature_c.shape
        if not (0 <= x < w and 0 <= y < h):
            raise IndexError(
                f"Pixel ({x}, {y}) hors de l'image ({w}x{h})."
            )
        return float(self.temperature_c[y, x])

    def stats(self) -> dict:
        """Calcule et retourne les statistiques basiques de température."""
        t = self.temperature_c
        return {
            "min_c": float(np.min(t)),
            "max_c": float(np.max(t)),
            "mean_c": float(np.mean(t)),
            "std_c": float(np.std(t)),
        }

    def hotspots(self, threshold_c: float) -> np.ndarray:
        """Retourne un masque booléen (H, W) des pixels au-dessus du seuil.

        Utile en amont d'une détection d'anomalies sur des modules PV
        (points chauds = défauts potentiels : cellules cassées, PID,
        bypass diode active, ombrage partiel, etc.).
        """
        return self.temperature_c >= threshold_c


def _convert_with_dji_irp(
    image_path: Path, params: Optional[RadiometricParams]
) -> Optional[np.ndarray]:
    """Utilise l'exécutable officiel `dji_irp` (DJI Thermal SDK) en CLI.

    C'est le moteur le plus fiable : il s'agit du binaire officiel de DJI,
    identique à celui utilisé par leurs propres outils d'analyse.

    Nécessite la variable d'environnement `DJI_IRP_EXE_PATH` pointant vers
    le chemin complet de dji_irp.exe. Retourne None si cette variable n'est 
    pas définie ou si l'exécutable échoue.
    """
    exe_path = os.environ.get("DJI_IRP_EXE_PATH")
    if not exe_path or not Path(exe_path).exists():
        print("[converter] Erreur : La variable d'environnement DJI_IRP_EXE_PATH n'est pas définie ou le chemin est invalide.")
        return None

    width, height = read_image_resolution(image_path)

    with tempfile.TemporaryDirectory() as tmpdir:
        raw_out = Path(tmpdir) / "measure.raw"
        cmd = [
            exe_path,
            "-s", str(image_path),
            "-a", "measure",
            "--measurefmt", "float32",
            "-o", str(raw_out),
        ]
        
        if params is not None:
            cmd += [
                "--distance", str(params.object_distance_m),
                "--humidity", str(params.relative_humidity_pct),
                "--emissivity", str(params.emissivity),
                "--reflection", str(params.reflected_temperature_c),
            ]

        result = subprocess.run(cmd, capture_output=True, text=True)
        
        if result.returncode != 0:
            print(
                f"[converter] dji_irp a échoué (code {result.returncode}): "
                f"{result.stderr or result.stdout}"
            )
            return None

        raw_bytes = raw_out.read_bytes()

    temperature = np.frombuffer(raw_bytes, dtype=np.float32)
    expected = width * height
    
    if temperature.size != expected:
        print(
            f"[converter] Taille inattendue : {temperature.size} valeurs lues, "
            f"{expected} attendues ({width}x{height}). Vérifiez la résolution de l'image."
        )
        return None

    return temperature.reshape(height, width).copy()


def load_thermal_image(
    image_path: str | Path,
    params: Optional[RadiometricParams] = None,
    read_params_from_exif: bool = True,
) -> ThermalImage:
    """Charge une image thermique radiométrique DJI et retourne un objet ThermalImage.

    Paramètres
    ----------
    image_path : chemin vers le fichier R-JPEG (ou TIFF radiométrique déjà
        converti par le DJI Thermal SDK / dji_irp).
    params : paramètres radiométriques à utiliser pour la conversion. Si
        None et read_params_from_exif=True, ils sont lus automatiquement
        depuis l'EXIF de l'image.
    read_params_from_exif : si True et params=None, lit les paramètres
        embarqués (émissivité, distance, humidité, T réfléchie) via
        exiftool avant conversion.

    Retour
    ------
    ThermalImage contenant la matrice de températures (H, W) float32.
    """
    image_path = Path(image_path)
    if not image_path.exists():
        raise FileNotFoundError(f"Le fichier spécifié est introuvable : {image_path}")

    # Complète automatiquement les paramètres depuis l'EXIF si non fournis
    if params is None and read_params_from_exif:
        params = read_dji_metadata(image_path)

    # Conversion avec dji_irp (CLI officiel DJI)
    temperature_c = _convert_with_dji_irp(image_path, params)
    
    if temperature_c is None:
        raise RuntimeError("La conversion de l'image thermique a échoué.")

    # Géoréférencement optionnel (ne bloque pas le traitement en cas d'échec)
    try:
        gps = read_gps(image_path)
    except Exception:
        gps = None

    return ThermalImage(
        temperature_c=temperature_c,
        params=params if params is not None else RadiometricParams(),
        source_path=image_path,
        gps=gps,
    )