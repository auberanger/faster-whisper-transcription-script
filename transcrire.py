#################################################################################################
## Script Whisper de retranscription d'entretiens sociologiques.                               ##
## v2.4 - 2026-10-14                                                                           ##
## Dépôt et instructions : https://github.com/auberanger/faster-whisper-transcription-script   ##
## à exécuter en tapant la commande : python3 transcrire.py fichier_audio.mp3        ##
#################################################################################################

from faster_whisper import WhisperModel
from faster_whisper.utils import download_model
from huggingface_hub import snapshot_download
from huggingface_hub.utils import enable_progress_bars

import argparse
import io
import time
import os
import math
import pathlib
import sys
import warnings

warnings.filterwarnings("ignore") # Masquage des warnings dans la console

# Modèles de transcription proposés (le premier est le modèle par défaut)
MODELES_WHISPER = ["large-v3-turbo", "large-v3"]

# Dépôts Hugging Face correspondant aux modèles proposés
DEPOTS_HF = {
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "large-v3": "Systran/faster-whisper-large-v3",
}
# Fichiers nécessaires au modèle (les mêmes que ceux téléchargés par faster-whisper)
FICHIERS_MODELE = ["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*"]

# Récupération du fichier audio à transcrire passé en argument
def creation_parser_arg():
    # Créée and retourne l'objet ArgumentParser

    parser = argparse.ArgumentParser(description="Utilitaire de pré-transcription d'entretiens, utilisant faster-whisper.")
    parser.add_argument("audio_entretien",
        help="Chemin et nom du fichier audio à retranscrire.")
    parser.add_argument("-m", "--modele", choices=MODELES_WHISPER, default=MODELES_WHISPER[0], help="Modèle de transcription (défaut : large-v3-turbo ; large-v3 = précision maximale, calcul plus long).")
    parser.add_argument("-l", "--langue", default=None,
        help="Code de la langue parlée (fr, en, es, de...). Par défaut : détection automatique.")
    return parser

# Parsing des argument rentrés en ligne de commande et vérification qu'ils soient corrects
p = creation_parser_arg().parse_args()

# Vérification de l'existence du fichier
if os.path.exists(p.audio_entretien):
    audio_entretien = p.audio_entretien
    print(f"\nFichier audio à retranscrire : {audio_entretien}")
else:
    sys.exit(f" (x) Fichier introuvable : {p.audio_entretien}")

# Vérification de l'argument de la langue
if p.langue:
    p.langue = p.langue.strip().lower()
    try:
        from faster_whisper.tokenizer import _LANGUAGE_CODES
        if p.langue not in _LANGUAGE_CODES:
            sys.exit(f" (x) Langue invalide : '{p.langue}'. Utiliser un code à deux lettres (fr, en, es, de...).")
    except ImportError:
        pass  # si la liste interne est indisponible, le try/except autour de transcribe() prend le relais

# Modèle de transcription choisi en paramètre (large-v3-turbo par défaut)
modele_whisper = p.modele

enable_progress_bars()  # garantit l'affichage de la barre de téléchargement
depot = DEPOTS_HF[modele_whisper]

try:
    try:
        # Modèle déjà présent sur la machine ? (aucun accès au réseau)
        chemin_modele = snapshot_download(depot, allow_patterns=FICHIERS_MODELE, local_files_only=True)
        if not os.path.exists(os.path.join(chemin_modele, "model.bin")):
            raise FileNotFoundError("téléchargement incomplet")
    except Exception:
        print(f"\nPremier lancement avec le modèle {modele_whisper} : téléchargement en cours")
        print("(1,5 à 3 Go selon le modèle, cela peut durer plusieurs minutes avec une connexion lente).")
        chemin_modele = snapshot_download(depot, allow_patterns=FICHIERS_MODELE)

    print(f"\nChargement du modèle {modele_whisper}.")
    model = WhisperModel(chemin_modele, device="cpu", compute_type="int8")

except Exception as e:
    print(f"\n (x) Impossible de télécharger ou de charger le modèle '{modele_whisper}' : {e}")
    print("     Vérifier la connexion internet et l'espace disque disponible, puis relancer le script.")
    sys.exit(1)
 
# Transcription, avec vérification de l'erreur du paramètre de choix de langue
heure_de_demarrage = time.localtime()
print(f"\n{time.strftime('%Hh%M', heure_de_demarrage)} : démarrage de la retranscription...")
 
try:
    transcription, info = model.transcribe(audio_entretien, beam_size=5, language=p.langue, vad_filter=True)
except ValueError as e:
    print(f"\n (x) Langue invalide : '{p.langue}'. Utiliser un code à deux lettres (fr, en, es, de...).")
    print(f"     Détail : {e}")
    sys.exit(1)

if p.langue:
    print(f"Langue imposée : '{p.langue}'.")
else:
    print("Langue détectée : '%s', avec une probabilité de %f." % (info.language, info.language_probability))

# Fonction pour faciliter l'horodatage des segments de parole en heures, minutes et secondes
def convertir(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"
    
# Récupération du nom du fichier débarrassé de son extension à l'aide de pathlib et création d'un fichier texte au même nom
fileNameStem = pathlib.Path(audio_entretien).stem
entretien_transcrit = f"{fileNameStem}.txt"

# Enregistrement de la transcription
with open(entretien_transcrit , 'w', encoding='utf-8') as f:
    for segment in transcription:
        start_time = convertir(segment.start)
        end_time = convertir(segment.end)
        f.write(f"{start_time} - {end_time}: {segment.text}\n")
        
heure_de_fin = time.localtime()
print(f"{time.strftime('%Hh%M', heure_de_fin)} : transcription terminée.")

print(f"\nEntretien transcrit et enregistré dans le fichier : {entretien_transcrit}")

# Calcul et affichage conditionnel de la durée de retranscription 
temps_retranscription = float(time.mktime(heure_de_fin) - time.mktime(heure_de_demarrage))
temps_retranscription_min = math.trunc(temps_retranscription/60)

if temps_retranscription_min > 59:
	duree_a_afficher = str(math.trunc(temps_retranscription/3600)) + "h" + str(round(temps_retranscription/60%60))
elif temps_retranscription_min >= 10:
	duree_a_afficher = str(temps_retranscription_min) + " min"
elif temps_retranscription_min >= 1:
	duree_a_afficher = str(temps_retranscription_min) + " min " + str(round(temps_retranscription%60))
else:
	duree_a_afficher = str(round(temps_retranscription)) + " sec"

print(f"Temps de retranscription de l'entretien avec le modèle {modele_whisper} : {duree_a_afficher}\n")

