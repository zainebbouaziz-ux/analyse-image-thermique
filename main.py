#!/usr/bin/env python3
"""
main.py
-------

CLI pour traiter une image thermique radiométrique DJI unique et en
extraire une matrice de températures réelles, pixel par pixel.

Exemples
--------
    # Conversion + export npy/csv, paramètres lus depuis l'EXIF de l'image
    python main.py DJI_0001_R.JPG --export npy csv --outdir resultats/


    # Visualisation interactive (clic pixel -> température)
    python main.py DJI_0001_R.JPG --show

    # Détection de points chauds au-dessus d'un seuil (ex: modules PV)
    python main.py DJI_0001_R.JPG --hotspot-threshold 45
"""

from __future__ import annotations

import argparse
from pathlib import Path

from thermal_reader import RadiometricParams, load_thermal_image
from thermal_reader.export import export_csv, export_npy
from thermal_reader.viewer import show_interactive


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("image", type=str, help="Chemin vers l'image thermique DJI (R-JPEG)")

    override_group = parser.add_argument_group("Surcharge des paramètres radiométriques")
    override_group.add_argument("--emissivity", type=float, default=None)
    override_group.add_argument("--distance", type=float, default=None, help="Distance à la cible, en mètres")
    override_group.add_argument("--humidity", type=float, default=None, help="Humidité relative, en %%")
    override_group.add_argument("--reflected-temp", type=float, default=None, help="Température réfléchie, en °C")

    parser.add_argument("--pixel", type=int, nargs=2, metavar=("X", "Y"),
                         help="Affiche la température d'un pixel précis (x y)")
    parser.add_argument("--show", action="store_true", help="Ouvre la visualisation interactive")
    parser.add_argument("--hotspot-threshold", type=float, default=None,
                         help="Affiche le nombre de pixels au-dessus de ce seuil (°C)")
    parser.add_argument("--export", nargs="+", choices=["npy", "csv", "geotiff"], default=[],
                         help="Formats d'export souhaités")
    parser.add_argument("--outdir", type=str, default=".", help="Dossier de sortie pour les exports")
    parser.add_argument("--pixel-size-m", type=float, default=None,
                         help="Taille au sol d'un pixel en mètres (requis pour --export geotiff)")

    return parser


def main() -> None:
    args = build_arg_parser().parse_args()
    image_path = Path(args.image)

    overrides = {}
    if args.emissivity is not None:
        overrides["emissivity"] = args.emissivity
    if args.distance is not None:
        overrides["object_distance_m"] = args.distance
    if args.humidity is not None:
        overrides["relative_humidity_pct"] = args.humidity
    if args.reflected_temp is not None:
        overrides["reflected_temperature_c"] = args.reflected_temp

    params = None
    if overrides:
        from thermal_reader.metadata import read_dji_metadata
        base = read_dji_metadata(image_path)
        params = base.with_overrides(**overrides)

    print(f"Chargement de {image_path} ...")
    thermal_image = load_thermal_image(image_path, params=params)

    h, w = thermal_image.shape
    stats = thermal_image.stats()
    print(f"Image chargée : {w}x{h} px")
    print(f"Paramètres radiométriques utilisés : {thermal_image.params}")
    print(
        f"Température — min: {stats['min_c']:.2f}°C  "
        f"max: {stats['max_c']:.2f}°C  moyenne: {stats['mean_c']:.2f}°C  "
        f"écart-type: {stats['std_c']:.2f}°C"
    )

    if args.pixel is not None:
        x, y = args.pixel
        temp = thermal_image.temperature_at(x, y)
        print(f"Température au pixel ({x}, {y}) : {temp:.2f} °C")

    if args.hotspot_threshold is not None:
        mask = thermal_image.hotspots(args.hotspot_threshold)
        print(
            f"Pixels >= {args.hotspot_threshold:.1f}°C : {int(mask.sum())} "
            f"({100 * mask.mean():.2f}% de l'image)"
        )

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    stem = image_path.stem

    for fmt in args.export:
        if fmt == "npy":
            path = export_npy(thermal_image, outdir / f"{stem}_temperature.npy")
            print(f"Export NPY -> {path}")
        elif fmt == "csv":
            path = export_csv(thermal_image, outdir / f"{stem}_temperature.csv")
            print(f"Export CSV -> {path}")
        
    if args.show:
        show_interactive(thermal_image)


if __name__ == "__main__":
    main()