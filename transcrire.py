#################################################################################################
## Utilitaire de retranscription d'entretiens sociologiques (faster-whisper et pyannote).      ##
## v3.2 - 2026-10-17                                                                           ##
## Dépôt et instructions : https://github.com/auberanger/faster-whisper-transcription-script   ##
## à exécuter en tapant la commande : python3 transcrire.py fichier_audio.mp3                  ##
#################################################################################################

from faster_whisper import WhisperModel
from faster_whisper.audio import decode_audio
from faster_whisper.utils import download_model

from huggingface_hub import snapshot_download
from huggingface_hub.utils import enable_progress_bars

from contextlib import nullcontext

from rich.console import Console, Group
from rich.live import Live
from rich.markup import escape
from rich.progress import Progress, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn, TimeRemainingColumn
from rich.text import Text

import argparse
import importlib.util
import math
import os
import pathlib
import re
import sys
import time
import warnings

warnings.filterwarnings("ignore") # Masquage des warnings dans la console





#===== Paramètres =====#

# Modèles de transcription proposés (le premier est le modèle par défaut)
MODELES_WHISPER = ["large-v3-turbo", "large-v3"]

# Dépôts Hugging Face correspondant aux modèles proposés
DEPOTS_HF = {
    "large-v3-turbo": "mobiuslabsgmbh/faster-whisper-large-v3-turbo",
    "large-v3": "Systran/faster-whisper-large-v3",
}
# Fichiers nécessaires au modèle (les mêmes que ceux téléchargés par faster-whisper)
FICHIERS_MODELE = ["config.json", "preprocessor_config.json", "model.bin", "tokenizer.json", "vocabulary.*"]

# Modèle de diarisation (identification de qui parle)
MODELE_DIARISATION = "pyannote/speaker-diarization-community-1"
NB_PERSONNES_DEFAUT = 2  # Par défaut on prend le cas standard d'un entretien en face à face

NB_LIGNES_APERCU = 5  # nombre de dernières lignes affichées sous la barre (3 à 5 conseillé)
# Styles de l'aperçu (nuances de gris, pensées pour un terminal à fond sombre)
STYLE_APERCU = "grey82"               # lignes du milieu : bien lisibles
STYLE_APERCU_APPARITION = "grey50"    # ligne la plus récente : elle « apparaît »
STYLE_APERCU_DISPARITION = "grey30"   # ligne la plus ancienne : elle « disparaît »

# Découpage des tours de parole trop longs en paragraphes (en nombre de caractères) :
# on coupe à la première fin de phrase après PARAGRAPHE_CIBLE, et dans tous les cas à PARAGRAPHE_MAX
PARAGRAPHE_CIBLE = 400
PARAGRAPHE_MAX = 700





#===== Fonctions =====#

# Récupération du fichier audio à transcrire passé en argument
def creation_parser_arg():
    # Créée and retourne l'objet ArgumentParser

    parser = argparse.ArgumentParser(description="Utilitaire de pré-transcription d'entretiens, utilisant faster-whisper et pyannote.")
    parser.add_argument("audio_entretien",
        help="Chemin et nom du fichier audio à retranscrire.")
    parser.add_argument("-m", "--modele", choices=MODELES_WHISPER, default=MODELES_WHISPER[0], help="Modèle de transcription (défaut : large-v3-turbo ; large-v3 = précision maximale, calcul plus long).")
    parser.add_argument("-l", "--langue", default=None,
        help="Code de la langue parlée (fr, en, es, de...). Par défaut : détection automatique.")
    parser.add_argument("-n", "--nombre-personnes", type=int, default=NB_PERSONNES_DEFAUT,
        help=f"Nombre de personnes qui parlent dans l'enregistrement (défaut : {NB_PERSONNES_DEFAUT}).")
    parser.add_argument("-v", "--vocabulaire", default=None,
        help="Termes à reconnaître en priorité (noms propres, sigles, termes métier) : liste entre guillemets séparée par des virgules, ou chemin d'un fichier texte avec un terme par ligne.")
    return parser

# Fonction pour faciliter l'horodatage des segments de parole en heures, minutes et secondes
def convertir(seconds):
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"

# Horodatage au format SRT : HH:MM:SS,mmm
def convertir_srt(secondes):
    ms = int(round(secondes * 1000))
    h, ms = divmod(ms, 3600000)
    m, ms = divmod(ms, 60000)
    s, ms = divmod(ms, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"

# Diarisation : retourne la liste des tours de parole (début, fin, étiquette de la personne)
def diariser(chemin_audio, nb_personnes):
    import torch
    from pyannote.audio import Pipeline

    # Décodage de l'audio avec PyAV (via faster-whisper) : mono, 16 kHz
    audio = decode_audio(chemin_audio, sampling_rate=16000)
    entree = {"waveform": torch.from_numpy(audio).unsqueeze(0), "sample_rate": 16000}

    pipeline = Pipeline.from_pretrained(MODELE_DIARISATION, token=os.environ.get("HF_TOKEN"))
    if pipeline is None:
        raise RuntimeError("modèle de diarisation inaccessible (jeton Hugging Face requis ?)")

    # Barre de progression de pyannote si disponible, sinon sans
    try:
        from pyannote.audio.pipelines.utils.hook import ProgressHook
        contexte = ProgressHook()
    except ImportError:
        contexte = nullcontext()

    with contexte as hook:
        sortie = pipeline(entree, hook=hook, num_speakers=nb_personnes)

    # Version « exclusive » : une seule personne parle à la fois, plus simple à croiser avec la transcription
    return [(tour.start, tour.end, personne) for tour, personne in sortie.exclusive_speaker_diarization]

# Attribue à chaque segment la personne dont la parole le recouvre le plus (Speaker 1, Speaker 2, ...)
def attribuer_locuteurs(segments, tours):
    noms = {}  # étiquette pyannote -> "Speaker 1", dans l'ordre d'apparition
    for seg in segments:
        recouvrement = {}
        for debut, fin, personne in tours:
            duree = min(seg["fin"], fin) - max(seg["debut"], debut)
            if duree > 0:
                recouvrement[personne] = recouvrement.get(personne, 0) + duree
        if recouvrement:
            brut = max(recouvrement, key=recouvrement.get)
            seg["locuteur"] = noms.setdefault(brut, f"Speaker {len(noms) + 1}")
        else:
            seg["locuteur"] = "Unknown speaker"

# Regroupe les segments consécutifs d'une même personne en tours de parole, puis découpe les tours trop longs en paragraphes (à la première fin de phrase après PARAGRAPHE_CIBLE caractères)
def regrouper_en_paragraphes(segments):
    paragraphes = []
    for seg in segments:
        courant = paragraphes[-1] if paragraphes else None
        if courant and courant["locuteur"] == seg["locuteur"]:
            longueur = len(courant["texte"])
            fin_de_phrase = courant["texte"].endswith((".", "?", "!", "…"))
            if longueur < PARAGRAPHE_CIBLE or (longueur < PARAGRAPHE_MAX and not fin_de_phrase):
                courant["fin"] = seg["fin"]
                courant["texte"] += " " + seg["texte"]
                continue
        paragraphes.append(dict(seg))
    return paragraphes

# Fichier .txt : un paragraphe par ligne, avec horodatage et personne qui parle
def ecrire_txt(segments, chemin, avec_locuteurs):
    with open(chemin, 'w', encoding='utf-8') as f:
        if avec_locuteurs:
            for par in regrouper_en_paragraphes(segments):
                f.write(f"[{convertir(par['debut'])} - {convertir(par['fin'])}] {par['locuteur']} : {par['texte']}\n\n")
        else:
            for seg in segments:
                f.write(f"{convertir(seg['debut'])} - {convertir(seg['fin'])}: {seg['texte']}\n")

# Fichier .srt : mêmes paragraphes que le .txt (l'horodatage est dans l'en-tête de chaque bloc)
def ecrire_srt(segments, chemin, avec_locuteurs):
    if avec_locuteurs:
        blocs = [(par["debut"], par["fin"], f"{par['locuteur']} : {par['texte']}")
                 for par in regrouper_en_paragraphes(segments)]
    else:
        blocs = [(seg["debut"], seg["fin"], seg["texte"]) for seg in segments]

    with open(chemin, 'w', encoding='utf-8') as f:
        for numero, (debut, fin, texte) in enumerate(blocs, start=1):
            f.write(f"{numero}\n{convertir_srt(debut)} --> {convertir_srt(fin)}\n{texte}\n\n")

# Retourne la liste des termes, à partir d'un fichier texte (un terme par ligne) ou d'une liste séparée par des virgules.
def lire_vocabulaire(valeur):
    if valeur is None:
        return None
    if os.path.isfile(valeur):
        with open(valeur, encoding='utf-8') as f:
            termes = [ligne.strip() for ligne in f if ligne.strip() and not ligne.startswith("#")]
    elif valeur.lower().endswith(".txt"):
        quitter(f"Fichier de vocabulaire introuvable : {val(valeur)}") 
    else:
        termes = [t.strip() for t in valeur.split(",") if t.strip()]
    return termes or None

# Compte les occurrences de chaque terme du vocabulaire dans la transcription (sans tenir compte de la casse).
def compter_vocabulaire(termes, segments):
    texte = " ".join(seg["texte"] for seg in segments)
    return {terme: len(re.findall(rf"(?<!\w){re.escape(terme)}(?!\w)", texte, flags=re.IGNORECASE))
            for terme in termes}

# Affiche un bilan du vocabulaire retrouvé à l'issu de la retranscription
def afficher_bilan_vocabulaire(occurrences):
    trouves = sorted(((t, n) for t, n in occurrences.items() if n > 0), key=lambda x: -x[1])
    liste = ", ".join(f"{escape(t)} [dim]({n})[/]" for t, n in trouves)
    succes(f"Vocabulaire retrouvé : {val(len(trouves))} terme·s sur {len(occurrences)}" + (f" : {liste}" if trouves else ""))

# Fonctions d'affichage
console = Console()
console_erreur = Console(stderr=True)

def val(valeur):
    """Met une valeur en gras. Les crochets sont échappés : pour rich, ils servent au balisage."""
    return f"[bold]{escape(str(valeur))}[/]"

def heure():
    return f"[dim bold cyan]{time.strftime('%Hh%M')}[/]"

def etape(message):
    console.print(f"[bold cyan]▶[/] {message}")

def succes(message):
    console.print(f"[bold green]✔[/] {message}")

def avertissement(message):
    console.print(f"[bold yellow]⚠[/] {message}")

def detail(message):
    console.print(f"  [dim]{message}[/]")

def erreur(message):
    console_erreur.print(f"[bold red]✖[/] {message}")

def quitter(message):
    erreur(message)
    sys.exit(1)




#===== Script =====#

# Parsing des argument rentrés en ligne de commande et vérification qu'ils soient corrects
p = creation_parser_arg().parse_args()

# Vérification de la saisie d'un nombre de personnes cohérent
if p.nombre_personnes < 1:
    quitter(f"Le nombre de personnes (-n) doit être au moins égal à 1.")

# Vérification de l'existence du fichier audio à transcrire
if os.path.exists(p.audio_entretien):
    audio_entretien = p.audio_entretien
    etape(f"Fichier audio à retranscrire : {val(audio_entretien)}")
else:
    quitter(f"Fichier introuvable : {val(p.audio_entretien)}")

# Vérification de l'argument de la langue
if p.langue:
    p.langue = p.langue.strip().lower()
    try:
        from faster_whisper.tokenizer import _LANGUAGE_CODES
        if p.langue not in _LANGUAGE_CODES:
            sys.exit(f" (x) Langue invalide : '{p.langue}'. Utiliser un code à deux lettres (fr, en, es, de...).")
    except ImportError:
        pass  # si la liste interne est indisponible, le try/except autour de transcribe() prend le relais

# La diarisation nécessite pyannote.audio : sans lui, la transcription est produite sans identifier les personnes
try:
    diarisation_possible = importlib.util.find_spec("pyannote.audio") is not None
except ModuleNotFoundError:
    diarisation_possible = False
if not diarisation_possible:
    avertissement("pyannote.audio n'est pas installé : la transcription sera produite sans identification des personnes.")
    detail("Pour l'installer : pip install pyannote.audio")

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
        etape(f"Premier lancement avec le modèle {val(modele_whisper)} : téléchargement en cours")
        detail("(1,5 à 3 Go selon le modèle, cela peut durer plusieurs minutes avec une connexion lente)")
        chemin_modele = snapshot_download(depot, allow_patterns=FICHIERS_MODELE)

    etape(f"Chargement du modèle {val(modele_whisper)}")
    model = WhisperModel(chemin_modele, device="cpu", compute_type="int8")

except Exception as e:
    erreur(f"Impossible de télécharger ou de charger le modèle {val(modele_whisper)} : {escape(str(e))}")
    detail("Vérifier la connexion internet et l'espace disque disponible, puis relancer le script.")
    sys.exit(1)

# Ajout du vocabulaire fourni à la variable hotwords pour la retranscription
termes = lire_vocabulaire(p.vocabulaire)
hotwords = ", ".join(termes) if termes else None
if termes:
    succes(f"Vocabulaire fourni : {val(len(termes))} terme·s")

# Transcription, avec vérification de l'erreur du paramètre de choix de langue
heure_de_demarrage = time.localtime()
etape(f"{heure()} Démarrage de la retranscription...")
 
try:
    transcription, info = model.transcribe(audio_entretien, beam_size=5, language=p.langue, vad_filter=True, hotwords=hotwords)
except ValueError:
    if p.langue is None:
        raise  # erreur sans rapport avec la langue : on ne la masque pas
    avertissement(f"Langue invalide : {val(p.langue)}. Passage en détection automatique.")
    p.langue = None
    transcription, info = model.transcribe(audio_entretien, beam_size=5, language=None, vad_filter=True, hotwords=hotwords)

if p.langue is not None:
    succes(f"Langue imposée : {val(p.langue)}")
else:
    succes(f"Langue détectée : {val(info.language)} (probabilité {info.language_probability:.0%})")

duree_audio = info.duration  # durée totale de l'audio, en secondes
derniers = []   # dernières lignes transcrites, pour l'aperçu
segments = []   # tous les segments : {"debut", "fin", "texte", "locuteur"}

# Barre de progression (rich), avec aperçu en direct des dernières lignes transcrites
progression = Progress(
    TextColumn("[bold]{task.description}"),
    BarColumn(bar_width=None),
    TaskProgressColumn(),
    TextColumn("•"),
    TimeElapsedColumn(),
    TextColumn("•"),
    TimeRemainingColumn(),
)
tache = progression.add_task("Retranscription", total=duree_audio)

def affichage():
    """Ce que rich affiche à chaque rafraîchissement : la barre, puis l'aperçu s'il y en a un."""
    if not derniers:
        return progression
    apercu = Text(no_wrap=True, overflow="ellipsis")
    n = len(derniers)
    for i, ligne in enumerate(derniers):
        if i == n - 1:
            style = STYLE_APERCU_APPARITION
        elif i == 0 and n == NB_LIGNES_APERCU:
            style = STYLE_APERCU_DISPARITION
        else:
            style = STYLE_APERCU
        apercu.append(ligne + ("\n" if i < n - 1 else ""), style=style)
    return Group(progression, apercu)

with Live(get_renderable=affichage, refresh_per_second=8, console=console):
    for segment in transcription:
        start_time = convertir(segment.start)
        segments.append({"debut": segment.start, "fin": segment.end,
                         "texte": segment.text.strip(), "locuteur": None})

        # Avancement de la barre jusqu'à la fin du segment qui vient d'être traité
        progression.update(tache, completed=min(segment.end, duree_audio))

        # Aperçu des dernières lignes, la plus récente en bas
        derniers.append(f"[{start_time}] {segment.text.strip()}")
        del derniers[:-NB_LIGNES_APERCU]

    # Complète la barre à 100 % et efface l'aperçu : seule la barre reste affichée
    progression.update(tache, completed=duree_audio)
    derniers.clear()

# Diarisation : identification de qui parle
diarisation_ok = False
if diarisation_possible:
    etape(f"{heure()} Identification des personnes qui parlent ({val(p.nombre_personnes)} attendues), cette étape peut être longue sur CPU...")
    try:
        tours = diariser(audio_entretien, p.nombre_personnes)
        attribuer_locuteurs(segments, tours)
        diarisation_ok = True
    except Exception as e:
        erreur(f"La diarisation a échoué : {escape(str(e))}")
        detail("La transcription est enregistrée sans identification des personnes.")

# Les segments vides (silences transcrits comme du vide) ne sont pas écrits
segments = [seg for seg in segments if seg["texte"]]

# Récupération du nom du fichier débarrassé de son extension à l'aide de pathlib et création des fichiers de sortie au même nom
fileNameStem = pathlib.Path(audio_entretien).stem
entretien_transcrit = f"{fileNameStem}.txt"
entretien_srt = f"{fileNameStem}.srt"

# Enregistrement de la transcription
ecrire_txt(segments, entretien_transcrit, diarisation_ok)
ecrire_srt(segments, entretien_srt, diarisation_ok)

heure_de_fin = time.localtime()
succes(f"{heure()} Transcription terminée.")

succes(f"Fichiers enregistrés : {val(entretien_transcrit)} et {val(entretien_srt)}")

if termes:
    afficher_bilan_vocabulaire(compter_vocabulaire(termes, segments))

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

console.print(f"[dim]Temps de retranscription avec le modèle {escape(modele_whisper)} :[/] {val(duree_a_afficher)}")