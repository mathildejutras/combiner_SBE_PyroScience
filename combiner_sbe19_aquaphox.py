# /// script
# requires-python = ">=3.9"
# dependencies = [
#     "matplotlib>=3.9.4",
#     "numpy>=2.0.2",
#     "pandas>=2.3.3",
# ]
# ///

# -------------------------------------------------------------------------------
# Script pour combiner les données de la sonde SBE19 et PyroScience AquapHOx-L
#
# Version initiale du script : Lyna Karkri - sept 2026
# Mise à jour : Mathilde Jutras - nov 2026
#
# Les lignes ci-haut servent à l'éxécution sur toute machine
# -------------------------------------------------------------------------------

import numpy as np
import matplotlib.pyplot as plt
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path
import re
import sys

def afficher_figures():
    """Affiche les figures ouvertes sans bloquer le script."""
    plt.show(block=False)
    plt.pause(0.1)   # laisse la fenêtre se dessiner avant la saisie


# --- Fonctions pour lire les fichiers 

def lire_cnv(fichier): #CTD
    """Lit un fichier Sea-Bird CNV et retourne un DataFrame."""

    with open(fichier, "r", encoding="latin-1") as f:
        lignes = f.readlines()

    colonnes = []

    # Extraire les noms de variables de l'en-tête
    for ligne in lignes:
        if ligne.startswith("# name"):
            partie = ligne.split("=", 1)[1].strip()
            nom = partie.split(":", 1)[0].strip()
            colonnes.append(nom)

        # extraire la date
        if ligne.startswith("# start_time"):
            m = re.search(r"start_time\s*=\s*\w{3}\s+\d{2}\s+(\d{4})", ligne)
            annee = int(m.group(1))
            break

        if ligne.strip() == "*END*":
            break

    # Localiser le début des données
    debut = next(i for i, ligne in enumerate(lignes)if ligne.strip() == "*END*") + 1

    # Importer les données numériques
    df = pd.read_csv(fichier,sep=r"\s+",skiprows=debut,header=None,names=colonnes)

    # Ajouter le nom du fichier source
    df["fichier"] = fichier.stem
    df["DateTime"] = pd.to_datetime(str(annee), format="%Y") + pd.to_timedelta(df["timeJ"] - 1, unit="D")

    return df


def read_pyro_csv(filename):
    """Lit un fichier CSV PyroScience et retourne un DataFrame."""

    with open(filename, "r", encoding="latin1") as f:
        lines = f.readlines()

    # Extraire les métadonnées
    metadata = {}

    for line in lines:
        if line.startswith("#--- Measurement Data"):
            break

        if line.startswith("#Log Name"):
            metadata["LogName"] = line.split("\t", 1)[1].strip()

        elif line.startswith("#Serial number"):
            metadata["SerialNumber"] = line.split("\t", 1)[1].strip()

        elif line.startswith("#Device Name"):
            metadata["Device"] = line.split("\t", 1)[1].strip()

    # Trouver le début des données
    header_idx = next(i for i, line in enumerate(lines)if line.startswith("Date [A Ch.1 Main]"))

    # Lire les données
    df = pd.read_csv(filename,sep=";",skiprows=header_idx,header=0,encoding="latin1")

    df.columns = df.columns.str.strip()

    # Ajouter les métadonnées
    for key, value in metadata.items(): df[key] = value

    # Ajouter le nom du fichier
    df["fichier"] = filename.stem

    # Créer une colonne DateTime
    df["DateTime"] = pd.to_datetime(df["Date [A Ch.1 Main]"].astype(str) + " " +df["Time [A Ch.1 Main]"].astype(str).str.replace(",", ".", regex=False),dayfirst=True,errors="coerce")

    df = df.rename(columns={'Oxygen (%air sat.) [A Ch.1 Main]':'oxysat_%', 'Sample Temp. (°C) [A T1]':'optode_temp_degC'})

    return df


def read_pyro_txt(filename):
    """Lit un fichier txt PyroScience et retourne un DataFrame."""

    with open(filename, "r", encoding="latin1") as f:
        lines = f.readlines()

    # Extraire les métadonnées
    metadata = {}

    n = 0
    for line in lines:
        if line.startswith("#"):
            n+=1

    # Lire les données
    df = pd.read_csv(filename,sep="\t",skiprows=n,header=0,encoding="latin1")

    df.columns = df.columns.str.strip()

    # convertir les unités
    df['airSat (0.001 %air sat)'] = df['airSat (0.001 %air sat)']*0.001
    df['umolar (0.001 umol/L)'] = df['umolar (0.001 umol/L)']*0.001
    df['tempSample (0.001 °C)'] = df['tempSample (0.001 °C)']*0.001

    df = df.rename(columns={'DateTime (YYYY-MM-DD hh:mm:ss)':"DateTime", 'airSat (0.001 %air sat)':'oxysat_%', 'umolar (0.001 umol/L)':'oxy_micromol/L',
                'tempSample (0.001 °C)':'optode_temp_degC'})

    return df

def demander_decalage():
    """Demande un décalage à ajouter au datetime de la CTD."""
    while True:
        saisie = input('Décalage à ajouter à la date de la CTD, en format DD HH:mm:ss : ').strip()
        signe = -1 if saisie.startswith('-') else 1
        saisie = saisie.lstrip('+-').strip()
        try:
            return signe * pd.Timedelta(saisie.replace(' ', ' days ', 1))
        except ValueError:
            print('Format invalide.')

# ----------------------------------------------------------------------

# Charger les données 

while True : 
    path = input('Inscrivez le nom du dossier contenant les données :  ')
    try: 
        path = Path(path) # direction entre le code et les fichiers

        # Trouver tous les fichiers CNV du dossier (CTD)
        fichiersCNV = [each for each in sorted(path.glob("*.cnv")) if 'SBE19' not in each.name]
        # Trouver tous les fichiers csv du dossier (optode)
        fichiersCVS = sorted(path.glob("*.csv"))
        # Trouver tous les fichiers txt du dossier (optode)
        fichiersTXT = sorted(path.glob("*.txt"))

        ### CTD
        profils = [lire_cnv(f) for f in fichiersCNV]
        dfCTD = pd.concat(profils, ignore_index=True)

        ### optode
        if not fichiersTXT:
            df = {f.stem: read_pyro_csv(f) for f in fichiersCVS}
            dfOpt = pd.concat([d.assign(cast=name) for name, d in df.items()],ignore_index=True)
        else:
            df = {f.stem: read_pyro_txt(f) for f in fichiersTXT}
            dfOpt = pd.concat([d.assign(cast=name) for name, d in df.items()],ignore_index=True)
        break
    except: 
        print('Entrée invalide ou fichiers absents. Réessayez')


# --------------------
# Aligner les données

def seul(source, cible, tol=np.timedelta64(6, "h")):
    # identifie les points qui n'ont pas de Opt/CTD à l'intérieur du seuil de tolérance
    src = source.to_numpy()
    cib = np.sort(cible.dropna().to_numpy())
    idx = np.searchsorted(cib, src)
    gauche = cib[np.clip(idx - 1, 0, len(cib) - 1)]
    droite = cib[np.clip(idx, 0, len(cib) - 1)]
    ecart = np.minimum(np.abs(src - gauche), np.abs(src - droite))
    return ecart > tol

seul_opt = seul(dfOpt.DateTime, dfCTD.DateTime)

plt.figure(figsize=(12,2))
plt.plot(dfCTD.DateTime, np.zeros(len(dfCTD)), 'xk')
plt.plot(dfOpt.DateTime, np.ones(len(dfOpt)), 'ok')
plt.plot(dfOpt.DateTime[seul_opt], np.ones(seul_opt.sum()), 'or', label='Points qui seront retirés')
plt.yticks([0, 1], ['CTD', 'Optode'])
plt.ylim([-1, 2])
plt.legend(loc='upper right')
plt.tight_layout()

# retirer les points de l'optode identifiés comme isolés
dfOpt = dfOpt[~seul_opt]
print('Les points sans données CTD ont été retirés')

# choisir les données à convertir
def demander_date(message, saisie=None):
    """Redemande la date tant qu'elle n'est pas valide."""
    print(' ')
    while True:
        saisie = input(message)
        try:
            date = pd.Timestamp(saisie)
            if pd.isna(date):   
                raise ValueError
            return date
        except (ValueError, TypeError):
            print('Mauvais format, réessayez (ex. 2026-05-15 23:00) :')

afficher_figures()
print(' ')
print('Vous souhaitez extraire les données sur quelle période?')
t0 = input('Date de début (format YYYY-MM-DD HH:mm ou "toutes") : ')
if 'tout' in t0 :
    dfCTDl = dfCTD
    dfOptl = dfOpt
else:
    t0 = demander_date('Date de début :', saisie=t0)
    tf = demander_date('Date de fin : ')

    dfCTDl = dfCTD[ (dfCTD['DateTime'] >= t0) & (dfCTD['DateTime'] <= tf) ]
    dfOptl = dfOpt[ (dfOpt['DateTime'] >= t0) & (dfOpt['DateTime'] <= tf) ]
plt.close()

# séparer par déploiements
seuil = pd.Timedelta(minutes=5)
ecart = dfCTDl['DateTime'].diff() 
dfCTDl['no_prof'] = (ecart > seuil).cumsum() 
ecart = dfOptl['DateTime'].diff() 
dfOptl['no_prof'] = (ecart > seuil).cumsum()

# Vérifier
fig, [ax1,ax2] = plt.subplots(2,1,figsize=(10,8))
ax1.plot(dfCTDl['DateTime'], dfCTDl['tv290C'], 'b.', label='CTD')
ax1.plot(dfOptl['DateTime'], dfOptl['optode_temp_degC'], 'm.', label='optode')
# un déploiement
ctd_prof = dfCTDl[dfCTDl.no_prof==1]
opt_prof = dfOptl[dfOptl.no_prof==1]
ax2.plot(ctd_prof.DateTime, ctd_prof.tv290C, 'b.')
ax2.plot(opt_prof.DateTime, opt_prof['optode_temp_degC'], 'm.')
ax1.legend()
for ax in [ax1,ax2]:
    ax.grid()
    ax.set_ylabel(r'Température [$^\circ$C]')

# Demander si les données sont alignées
afficher_figures()
print(' ')
while True :
    check = input('Les données du CTD et de l\'optode sont-elles bien alignées ? (O/N) ').strip().lower()
    if ('o' in check) | ('n' in check) : 
        break
    print('Réponse invalide.')

if 'o' in check : 
    print('super')
    dt=pd.Timedelta(0)
    plt.close()

else :
    plt.close()

    # --- Si elles le ne sont pas, essayer de les aligner avec le min de T
    idx_ctd = ctd_prof['tv290C'].idxmin()
    t_ctd = dfCTD.loc[idx_ctd, 'DateTime']
    idx_opt = opt_prof['optode_temp_degC'].idxmin()
    t_opt = dfOpt.loc[idx_opt, 'DateTime']
    # écart 
    dt = t_opt - t_ctd

    # vérifier
    fig, [ax1,ax2] = plt.subplots(2,1,figsize=(10,8))
    ax1.plot(dfCTDl['DateTime']+dt, dfCTDl['tv290C'], 'b.', label='CTD')
    ax1.plot(dfOptl['DateTime'], dfOptl['optode_temp_degC'], 'm.', label='optode')
    # un déploiement
    ax2.plot(ctd_prof.DateTime+dt, ctd_prof.tv290C, 'b.')
    ax2.plot(opt_prof.DateTime, opt_prof['optode_temp_degC'], 'm.')
    ax1.legend()
    for ax in [ax1,ax2]:
        ax.grid()
        ax.set_ylabel(r'Température [$^\circ$C]')

    afficher_figures()
    while True :
        check = input('Et maintenant, les données sont elles bien alignées ? (O/N) ').strip().lower()
        if ('o' in check) | ('n' in check) : 
            break
        print('Réponse invalide.')
        plt.close()

    if 'n' in check : 
        # --- faire ajustement manuel
        print('Ok, nous allons choisir le décalage manuellement')
        dt = pd.Timedelta(0)
        check = 'n'
        while True:
            fig, ax = plt.subplots(figsize=(10, 4))
            ax.plot(ctd_prof.DateTime + dt, ctd_prof.tv290C, 'b.', label='CTD')
            ax.plot(opt_prof.DateTime, opt_prof['optode_temp_degC'], 'm.', label='optode')
            ax.set_title(f'Décalage : {dt}')
            ax.set_ylabel(r'Température [$^\circ$C]')
            ax.legend()
            ax.grid()
            afficher_figures()

            if dt != pd.Timedelta(0): # ne pas demander la première fois
                while True:
                    check = input('Les données sont elles bien alignées ? (O/N) ').strip().lower()
                    if ('o' in check) | ('n' in check) : 
                        break
                    print('Réponse invalide.')

            if 'o' in check:
                break
            dt = demander_decalage()
        plt.close()



# --- ensuite, tester de combiner les deux datasets

dfOpt_test = dfOptl.copy()
dfOpt_test['DateTime'] = dfOpt_test['DateTime'] - dt

dfOpt_test = dfOpt_test.sort_values("DateTime")
dfCTDl = dfCTDl.sort_values("DateTime")
dfCTDl["DateTime"] = pd.to_datetime(dfCTDl["DateTime"]).astype("datetime64[ns]")
dfOpt_test["DateTime"] = pd.to_datetime(dfOpt_test["DateTime"]).astype("datetime64[ns]")

# garder juste certaines variables
var_opt = ['oxysat_%', 'oxy_micromol/L']
var_opt_l = [each for each in var_opt if each in list(dfOpt_test.keys())]
var_ctd = ['depSM', 'sal00', 'tv290C', 'potemp090C', 'density00', 'prdM']
var_ctd_l = [each for each in var_ctd if each in list(dfCTDl.keys())]

df = pd.merge_asof(dfCTDl,dfOpt_test,on="DateTime",direction="nearest",tolerance=pd.Timedelta("1m"))

# vérifier sur les profils
fig, [ax1,ax2] = plt.subplots(1,2,figsize=(8,5), sharey=True)
ax1.plot(df.tv290C, df.depSM, 'b.', markersize=1, label='CTD')
ax1.plot(df['optode_temp_degC'], df.depSM, 'm.', markersize=1, label='optode')
ax1.set_xlabel(r'Température [$^\circ$C]') ; ax1.set_ylabel('Depth [m]')
ax1.legend()
ax2.plot(df['oxysat_%'], df.depSM, 'm.', markersize=1)
ax2.set_xlabel(r'Oxygen saturation [\%]') 
plt.gca().invert_yaxis()

# vérifier
afficher_figures()
print(' ')
while True :
    check = input('Est-ce que la combinaison des données semble s\'être effectuée sans problème ? (O/N) ').strip().lower()
    if ('o' in check) | ('n' in check) : 
        break
    print('Réponse invalide.')

plt.close()

# --------------
# Créer le dataset final

dfsave = df[['DateTime',  'no_prof_x']+var_ctd_l+var_opt_l ]
dfsave = dfsave.rename(columns={'depSM':'depth_m', 'tv290C':'temp_degC', 'potemp090C':'potemp_degC',
                        'sal00':'psal_psu', 'prDM':'pres_db', 'density00':'dens_kgm3', 'prdM':'pres_db',
                        'no_prof_x':'no_prof'})

path = input('Où souhaitez-vous sauvegarder le fichier (. pour le dossier présent) ')
if path[-1] != '/' :
    path = path+'/'
#name = input('Quel nom souhaitez-vous donner au fichier? ')
name = 'CTD+optode'
namefile = '%s%s.csv'%(path,name)
dfsave.to_csv(namefile)
print(' ')
print('Fichier %s sauvegardé'%namefile)