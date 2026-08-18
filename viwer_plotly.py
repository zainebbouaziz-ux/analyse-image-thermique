import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from metadata import read_dji_metadata

# ================================
# Charger la matrice température
# ================================
temp = np.load(
    r"C:\Users\msi\Desktop\stage2026\thermal_pv\resultats_1\DJI_20260318103735_0012_T_temperature.npy"
)

# ================================
# Statistiques
# ================================
height, width = temp.shape

temp_min = np.nanmin(temp)
temp_max = np.nanmax(temp)
temp_mean = np.nanmean(temp)
temp_std = np.nanstd(temp)

# ================================
# Paramètres radiométriques
# ================================
params = read_dji_metadata(
    r"C:\Users\msi\Desktop\stage2026\photogrammetry_pipeline\data\images_thermique\DJI_20260318103735_0012_T.JPG"
)

# ================================
# Figure
# ================================
fig = make_subplots(
    rows=1,
    cols=2,
    column_widths=[0.72, 0.28],
    specs=[[{"type": "heatmap"}, {"type": "table"}]],
    horizontal_spacing=0.04
)

# ================================
# Heatmap
# ================================
fig.add_trace(
    go.Heatmap(
        z=temp,
        colorscale="Inferno",
        colorbar=dict(title="°C"),
        hovertemplate=
        "Pixel X : %{x}<br>"
        "Pixel Y : %{y}<br>"
        "Température : %{z:.2f} °C"
        "<extra></extra>"
    ),
    row=1,
    col=1
)

# ================================
# Tableau informations
# ================================
# -------------------------------
# Tableau 1 : Statistiques
# -------------------------------
table_stats = go.Table(
    domain=dict(x=[0.73, 1.00], y=[0.52, 1.00]),
    header=dict(
        values=["<b>Statistiques</b>", "<b>Valeur</b>"],
        align="left"
    ),
    cells=dict(
        values=[
            [
                "Dimensions",
                "Température minimale",
                "Température maximale",
                "Température moyenne",
                "Écart-type"
            ],
            [
                f"{width} × {height} pixels",
                f"{temp_min:.2f} °C",
                f"{temp_max:.2f} °C",
                f"{temp_mean:.2f} °C",
                f"{temp_std:.2f} °C"
            ]
        ],
        align="left"
    )
)

# -------------------------------
# Tableau 2 : Paramètres radiométriques
# -------------------------------
table_params = go.Table(
    domain=dict(x=[0.73, 1.00], y=[0.00, 0.46]),
    header=dict(
        values=["<b>Paramètres radiométriques</b>", "<b>Valeur</b>"],
        align="left"
    ),
    cells=dict(
        values=[
            [
                "Émissivité",
                "Distance objet",
                "Humidité relative",
                "Température réfléchie",
                "Température atmosphérique",
                "Transmission fenêtre IR"
            ],
            [
                f"{params.emissivity:.2f}",
                f"{params.object_distance_m:.1f} m",
                f"{params.relative_humidity_pct:.1f} %",
                f"{params.reflected_temperature_c:.1f} °C",
                f"{params.atmospheric_temperature_c:.1f} °C",
                f"{params.ir_window_transmission:.2f}"
            ]
        ],
        align="left"
    )
)

fig.add_trace(table_stats)
fig.add_trace(table_params)
# ================================
# Mise en page
# ================================
fig.update_layout(
    title="Image thermique radiométrique DJI",
    width=1350,
    height=700
)

fig.update_yaxes(
    autorange="reversed",
    title="Pixel Y",
    row=1,
    col=1
)

fig.update_xaxes(
    title="Pixel X",
    row=1,
    col=1
)

# ================================
# Affichage
# ================================
fig.show()

# ================================
# Sauvegarde
# ================================
fig.write_html(
    r"C:\Users\msi\Desktop\stage2026\thermal_pv\resultats_1\image_thermique_interactive.html"
)