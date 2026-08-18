"""
export.py
---------

Export de la matrice de températures vers différents formats exploitables
en aval (traitement, IA, SIG) :

    - .npy    : matrice NumPy Float32 brute (le plus fidèle, recommandé
                pour tout traitement Python ultérieur / IA)
    - .csv    : températures ligne par ligne (pratique pour inspection
                manuelle / tableur, mais fichiers volumineux pour de
                grandes images)

"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import numpy as np

from .converter import ThermalImage


def export_npy(thermal_image: ThermalImage, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    np.save(output_path, thermal_image.temperature_c)
    return output_path


def export_csv(thermal_image: ThermalImage, output_path: str | Path) -> Path:
    output_path = Path(output_path)
    np.savetxt(output_path, thermal_image.temperature_c, delimiter=",", fmt="%.2f")
    return output_path


