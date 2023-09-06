##########################################################################################
## Script Whisper de retranscription d'entretiens sociologiques.                        ##
## v2.2 - 2023-09-06                                                                    ##
## inspiré de https://www.css.cnrs.fr/whisper-pour-retranscrire-des-entretiens/         ##
## à exécuter en tapant la commande : python3 faster_whisper_interview_transcription.py ##
##########################################################################################

from faster_whisper import WhisperModel
import io
import time
import os
import math
import pathlib
import warnings

warnings.filterwarnings("ignore") # Masquage des warnings dans la console
 
# On définit le chemin de l'enregistrement de son entretien sur son PC
audio_entretien = "./test_mini.m4a" # Chemin du fichier audio à transcrire

#TODO: prompt pour choisir le fichier

# Prompt pour choisir la taille du modèle faster-whisper de transcription (large-v2 par défaut)
modeles_whisper = ["large-v2", "medium", "small"]
modele_whisper = ""

prompt_modele = "Choisir un modèle de retranscription (détermine la qualité et le temps de calcul, 'large-v2' par défaut) :\n"
for index, modele in enumerate(modeles_whisper):
    prompt_modele += f'{index+1}) {modele}\n'
prompt_modele += "Modèle à utiliser : "
modele_whisper = input(prompt_modele)

if modele_whisper in map(str, range(1, len(modeles_whisper) + 1)):
    modele_whisper = modeles_whisper[int(modele_whisper) - 1]
else:
    print(f" (x) Saisie incorrecte, sélection du modèle par défaut.")
    modele_whisper = "large-v2"

# On télécharge le modèle
print(f"\nChargement du modèle {modele_whisper}.")
model = WhisperModel(modele_whisper, device="cpu", compute_type="int8")
 
# Transcription
heure_de_demarrage = time.localtime()
print(f"\n{time.strftime('%Hh%M', heure_de_demarrage)} : démarrage de la retranscription...")
 
transcription, info = model.transcribe(audio_entretien, beam_size=5)

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

