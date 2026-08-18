# thermal_pv — Extraction de températures réelles depuis une image thermique DJI

## Description

`thermal_pv` est un pipeline Python permettant de traiter une **image thermique
radiométrique DJI unique** (R-JPEG) afin d'extraire la **température réelle de
chaque pixel**.

Le projet est destiné à l'analyse thermographique des modules photovoltaïques
(PV) :

- extraction de température pixel par pixel ;
- analyse thermique quantitative ;
- détection de zones chaudes (hotspots) ;
- export des données thermiques pour analyse ultérieure.

Le pipeline traite une image individuelle.

Il ne réalise pas :

- génération d'orthophoto ;
- assemblage multi-images ;
- mosaïque thermique ;
- reconstruction 3D.

---

# 1. Fonctionnement des images thermiques DJI

Une image thermique DJI :

```
DJI_xxxx_T.JPG
```

contient deux types d'informations.

---

## 1.1 Image JPEG visible

Lorsqu'une image thermique est ouverte avec une visionneuse classique,
elle apparaît sous forme colorée.

Cette représentation correspond à :

- une palette thermique appliquée par la caméra ;
- une image RGB 8 bits ;
- une visualisation destinée à l'utilisateur.

Exemples de palettes :

- Iron Red ;
- Rainbow ;
- White Hot ;
- Black Hot.

Cette image :

- ne contient pas directement la température ;
- ne permet pas de retrouver la température exacte ;
- ne doit pas être utilisée pour une analyse scientifique.

---

## 1.2 Données radiométriques DJI

Le fichier DJI contient également un bloc radiométrique propriétaire.

Ce bloc contient les informations nécessaires pour retrouver la température
physique associée à chaque pixel.

La conversion doit être effectuée avec le moteur officiel DJI.

---

# 2. Conversion radiométrique utilisée

DJI ne publie pas publiquement :

- la formule complète de conversion thermique ;
- les constantes internes de calibration ;
- les paramètres capteur propriétaires.

Une conversion développée manuellement serait donc une approximation.

Ce projet utilise :

```
DJI Thermal SDK officiel
```

avec l'outil :

```
dji_irp.exe
```

---

# 3. Rôle de dji_irp.exe

`dji_irp.exe` est le moteur officiel DJI utilisé pour convertir les images
thermiques radiométriques.

Il réalise :

- décodage des données thermiques DJI ;
- application de la calibration capteur ;
- correction radiométrique ;
- conversion en température Celsius.

Entrée :

```
DJI_xxxx_T.JPG
```

Sortie :

```
Matrice Float32 (H,W)
```

où :

```
temperature[y,x] = température réelle du pixel en °C
```

---

# 4. Paramètres radiométriques

La conversion utilise les paramètres physiques :

| Paramètre | Description |
|---|---|
| Émissivité | capacité d'émission thermique de la surface |
| Distance objet | distance caméra-cible |
| Humidité relative | correction atmosphérique |
| Température réfléchie | rayonnement environnemental réfléchi |
| Température atmosphérique | température de l'air |

Ces paramètres sont récupérés depuis les métadonnées DJI avec :

```
ExifTool
```

---

# 5. Pipeline général

```
Image thermique DJI M3T

DJI_xxxx_T.JPG

        |
        v

metadata.py

Lecture :
- EXIF DJI
- paramètres radiométriques
- GPS

        |
        v

converter.py

        |
        v

dji_irp.exe

DJI Thermal SDK officiel

        |
        v

Matrice température Float32

(H,W) en °C

        |
        +----------------+
        |                |
        v                v

viewer.py          export.py

clic pixel         NPY / CSV
température        


        |
        v

colorize.py

température → couleur

visualisation uniquement
```

---

# 6. Image colorisée vs température réelle

Principe utilisé :

```
Température  --->  Couleur
```

et jamais :

```
Couleur ---> Température
```

Le module :

```
colorize.py
```

sert uniquement à créer une image thermique colorée.

Il ne modifie pas les données thermiques.

La source de vérité reste :

```
temperature.npy
```

qui contient les valeurs réelles en °C.

---

# 7. Architecture du projet

```
thermal_pv/

├── requirements.txt
├── README.md
├── main.py
│
├── thermal_reader/
│
│   ├── metadata.py
│   │      Lecture paramètres DJI :
│   │      - emissivité
│   │      - distance
│   │      - humidité
│   │      - température réfléchie
│   │      - GPS
│
│   ├── converter.py
│   │      Conversion :
│   │      R-JPEG DJI
│   │          ↓
│   │      température Float32
│
│   ├── colorize.py
│   │      température → couleur
│   │      visualisation uniquement
│
│   ├── viewer.py
│   │      affichage interactif
│   │      clic pixel → température
│
│   └── export.py
│          Export :
│          - NPY
│          - CSV
│          
│
└── resultats/
```

---

# 8. Installation

## 8.1 Création environnement Python

```powershell
cd "C:\chemin\vers\thermal_pv"

python -m venv venv

venv\Scripts\activate
```

---

## 8.2 Installation bibliothèques

```powershell
pip install --upgrade pip

pip install -r requirements.txt
```

---

# 9. Installation des dépendances externes

## 9.1 ExifTool

Installer ExifTool :

```
https://exiftool.org
```

Tester :

```powershell
exiftool -ver
```

Si un numéro de version apparaît :

```
13.xx
```

ExifTool fonctionne correctement.

---

## 9.2 DJI Thermal SDK

Installer le DJI Thermal SDK officiel.

Placer :

```
dji_irp.exe
```

dans un dossier accessible.

Exemple :

```
C:\DJI_Thermal_SDK\dji_irp.exe
```

Définir la variable :

```powershell
$env:DJI_IRP_EXE_PATH="C:\DJI_Thermal_SDK\dji_irp.exe"
```

Tester :

```powershell
dji_irp.exe -h
```

Si l'aide apparaît :

```
DJI Thermal SDK opérationnel
```

---

# 10. Utilisation

## Conversion température + export

```powershell
python main.py DJI_0001_T.JPG --export npy csv --outdir resultats
```

Résultats :

```
resultats/

├── DJI_0001_T_temperature.npy
└── DJI_0001_T_temperature.csv
```

---

## Statistiques thermiques

```powershell
python main.py DJI_0001_T.JPG --export npy csv --outdir resultats
```

Informations obtenues :

- température minimale ;
- température maximale ;
- température moyenne ;
- écart-type.

---

## Température d'un pixel

Exemple :

```powershell
python main.py DJI_0001_T.JPG --pixel 320 256
```

Résultat :

```
Pixel (320,256)

Température : XX °C
```

---

## Visualisation interactive

```powershell
python main.py DJI_0001_T.JPG --show
```

Fonctions :

- affichage image thermique ;
- clic sur un pixel ;
- affichage température correspondante.

---

## Détection hotspot PV

Exemple seuil 45°C :

```powershell
python main.py DJI_0001_T.JPG --hotspot-threshold 45
```

Permet de détecter :

- zones anormalement chaudes ;
- défauts potentiels sur modules PV.

---

# 11. Sorties du pipeline

## Fichier NPY

Contient :

```
Matrice Float32 H × W
```

Chaque valeur représente :

```
Température réelle en °C
```

---

## Fichier CSV

Contient :

```
X pixel
Y pixel
Température °C
```

---

## Image colorisée

Utilisée uniquement pour :

- rapports ;
- visualisation ;
- interprétation rapide.

Elle n'est jamais utilisée pour les calculs.

---

# 12. Limitations

- Traitement d'une image thermique unique uniquement.
- Pas d'orthomosaïque.
- Pas de reconstruction photogrammétrique.
- Conversion dépendante du DJI Thermal SDK officiel.
- La précision dépend des paramètres radiométriques.

Pour les panneaux photovoltaïques, l'émissivité doit être correctement choisie
car une mauvaise valeur peut provoquer une erreur de plusieurs degrés Celsius.

---

# 13. Objectif final

Le pipeline produit une donnée thermique exploitable :

```
Image DJI M3T radiométrique

        ↓

Température réelle par pixel

        ↓

Analyse thermique PV

        ↓

Détection des anomalies thermiques
```