"""
colorize.py
-----------

Génère une image colorisée UNIQUEMENT à des fins de visualisation.

Sens de la transformation : température -> couleur (jamais l'inverse).
Cette image ne doit servir à aucun calcul de température ; elle n'est
qu'une représentation visuelle de la matrice de températures déjà
calculée par converter.py.
"""

from __future__ import annotations

from typing import Optional

import numpy as np
import matplotlib.pyplot as plt
import matplotlib.cm as cm
import matplotlib.colors as mcolors


def colorize_temperature(
    temperature_c: np.ndarray,
    vmin: Optional[float] = None,
    vmax: Optional[float] = None,
    cmap_name: str = "inferno",
) -> np.ndarray:
    """Convertit une matrice de températures en image RGB 8-bit (H, W, 3).

    Paramètres
    ----------
    temperature_c : matrice de températures (H, W), en degrés C.
    vmin, vmax : bornes de normalisation. Si None, utilise le min/max réel
        de l'image (mode "auto-contraste"), pratique pour repérer les
        points chauds relatifs à chaque image.
    cmap_name : nom d'une colormap matplotlib ("inferno", "jet", "gray"...).

    Retour
    ------
    np.ndarray uint8 de forme (H, W, 3), prêt pour affichage / export PNG.
    """
    vmin = float(np.min(temperature_c)) if vmin is None else vmin
    vmax = float(np.max(temperature_c)) if vmax is None else vmax

    norm = mcolors.Normalize(vmin=vmin, vmax=vmax)
    try:
        cmap = cm.get_cmap(cmap_name)  # matplotlib < 3.9
    except AttributeError:
        cmap = plt.get_cmap(cmap_name)  # matplotlib >= 3.9

    rgba = cmap(norm(temperature_c))  # (H, W, 4) float in [0, 1]
    rgb_uint8 = (rgba[:, :, :3] * 255).astype(np.uint8)
    return rgb_uint8