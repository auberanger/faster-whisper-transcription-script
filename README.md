# Script whisper de retranscription automatique d'entretiens

Ce script a été écrit dans le but de simplifier l'utilisation de l'outil de retranscription automatique d'audio open-source [whisper](https://github.com/openai/whisper) d'OpenAI. L'entretien est un exercice routinier des enquêtes en sciences sociales. Bien qu'il ne soit pas toujours attendu d'en réaliser une retranscription intégrale, cela peut être pertinent dans de nombreux cas (codage de corpus d'entretiens, collaborations sur un corpus, etc.). Cet exercice, s'il a le mérite de permettre de gagner en familiarité avec le contenu de l'entretien, se révèle être particulièrement chronophage et incombant majoritairement aux précaires du monde de la recherche.

Le but de ce script est de permettre de gagner du temps sur ce travail de transcription, gratuitement et dans le respect de la confidentialité des enquêté·es (les calculs se font en local). Il permet d'obtenir une __pré-transcription horodatée__, découpée par tours de parole et avec l'identification automatique des personnes qui parlent, qui nécessite ensuite une passe manuelle pour renommer les locuteurices détecté·es et corriger les erreurs de retranscription. __Cet outil n’est donc pas un substitut à l’écoute attentive des entretiens.__

Je me suis inspiré de l'article de blog de [Yacine Chitour](https://www.css.cnrs.fr/whisper-pour-retranscrire-des-entretiens), pour réaliser un script optimisé, utilisant [faster-whisper](https://github.com/guillaumekln/faster-whisper), une réimplémentation de Whisper permettant d'accélérer significativement le temps de calcul. Je conseille également [cet article](https://agepouvoir.hypotheses.org/646) qui discute de questions méthodologiques et éthiques sur l'usage de Whisper.

Pour l'instant, je n'ai pu tester ce script que sous Linux. Des retours sur son fonctionnement et le guide d'utilisation avec d'autres systèmes d'exploitations sont les bienvenus.

## Installation
S'assurer d'avoir [Python](https://www.python.org/downloads/) installé sur son OS et que la version est supérieure ou égale à python 3.2. Cela peut être vérifié en tappant la commande suivante dans le terminal :
```
python3 --version
```

Prévoir de l'espace disque libre pour l'installation des modèles de calcul et des bibliothèques : plusieurs Go pour les modèles de transcription, et plusieurs Go supplémentaires pour pyannote.audio, qui installe PyTorch. Ça peut être assez gourmand.

Commencer par créer un environnement virtuel dédié :
```
python3 -m venv ~/venv-whisper
```

> [!NOTE]
> Si la commande échoue en signalant que `venv` ou `ensurepip` est absent, installer d'abord le module manquant sous Debian/Ubuntu avec `sudo apt install python3-venv`, puis relancer la commande.
> 
> Il faut ensuite l'activer : le nom de l'environnement, `(venv-whisper)`, s'affiche alors au début de l'invite de commande du terminal.
> ```
> source ~/venv-whisper/bin/activate
> ```
Sous Windows (non testé), la création et l'activation se font avec `py -m venv venv-whisper` puis `venv-whisper\Scripts\activate`.

L'activation vaut uniquement pour le terminal en cours : elle est à refaire à chaque nouveau terminal, avant de lancer le script. Pour quitter l'environnement, taper `deactivate`.

Une fois l'environnement activé, installer [faster-whisper](https://github.com/SYSTRAN/faster-whisper) et [pyannote.audio](https://github.com/pyannote/pyannote-audio) avec la commande :
```
pip install -U faster-whisper pyannote.audio "av<19"
```
L'installation peut être longue (à cause du téléchargement de PyTorch notamment).

> [!NOTE]
> **Pourquoi `"av<19"` ?** faster-whisper utilise la bibliothèque PyAV (paquet `av`) pour lire les fichiers audio. La version 19 de PyAV (septembre 2026) n'est pas compatible avec la dernière version publiée de faster-whisper (1.2.1) : sans cette contrainte, la transcription s'arrête avec l'erreur `TypeError: open() got an unexpected keyword argument 'metadata_errors'"`. Cette contrainte pourra être retirée quand faster-whisper publiera une version corrigée (voir le [suivi]() du problème). Si vous rencontrez déjà cette erreur, lancez simplement `pip install "av<19"` dans l'environnement activé ou réinstallez complètement faster-whisper :
> ```
> pip install -U --force-reinstall av faster-whisper "av<19"
> ```

### Accès au modèle de diarisation
Au premier lancement, le script télécharge le modèle d'identification des personnes [`pyannote/speaker-diarization-community-1`](https://huggingface.co/pyannote/speaker-diarization-community-1). Si ce téléchargement est refusé (message d'erreur d'accès), il faut :
1. créer un compte sur [Hugging Face](https://huggingface.co/) ;
2. accepter les conditions d'utilisation sur la page du modèle, si elle le demande ;
3. créer un jeton d'accès en lecture dans les paramètres de votre compte (« Access Tokens ») ;
4. le fournir au script en tapant, dans le terminal et avant de lancer le script : `export HF_TOKEN=votre_jeton`.

Une fois les modèles téléchargés, tous les calculs se font en local : les enregistrements ne quittent pas votre ordinateur.

## Utilisation
Ce script est conçu pour être utilisé par une personne n'ayant jamais écrit la moindre ligne de code. Il suffit juste pour l'utiliser d'avoir un terminal de commande à sa disposition et d'exécuter quelques commandes basiques.

Vérifier d'abord que vous êtes bien dans l'environnement virtuel dans lequel faster-whisper est installé. Si le nom de l'environnement `(venv-whisper)` ne s'affiche pas au début de l'invite de commande du terminal, relancer :
```
source ~/venv-whisper/bin/activate
```

Télécharger le script `transcrire.py` (sur ce dépôt) et l'enregistrer dans le dossier contenant les fichiers audios d'entretiens à retranscrire. Ouvrir dans ce dossier un terminal et lancer le script avec la commande 
```
python3 transcrire.py fichier_audio_entretien.mp3
```
en remplaçant `fichier_audio_entretien.mp3` par le nom du fichier audio dont vous souhaitez une retranscription (vous pouvez vous aider de la touche `[Tab]` du clavier pour l'auto-complétion du nom de fichier). De nombreux formats audio sont acceptés par whisper (.mp3, .wav, .ogg, .amr, .m4a, etc.).

Si le chemin d'accès ou le nom du fichier est incorrect, le script renverra une erreur et s'arrêtera.

### Récapitulatif des options

| Option | Rôle | Par défaut |
|---|---|---|
| `-l`, `--langue` | Langue parlée (code à deux lettres : `fr`, `en`...) | détection automatique |
| `-m`, `--modele` | Modèle de transcription : `large-v3-turbo` ou `large-v3` | `large-v3-turbo` |
| `-n`, `--nombre-personnes` | Nombre de personnes qui parlent dans l'enregistrement | `2` |

Exemple combinant les trois : `python3 transcrire_entretien.py entretien.mp3 -l fr -m large-v3 -n 3`

### Choisir la langue de l'entretien
Par défaut, la langue est détectée automatiquement à partir des premières dizaines de secondes du fichier audio. Cette détection peut se tromper (accent marqué, début d'enregistrement bruité, entretien mêlant plusieurs langues). Il est donc recommandé de **préciser la langue** avec l'option `-l` (ou `--langue`), suivie du code à deux lettres de la langue :
```
python3 transcrire.py fichier_audio_entretien.mp3 -l fr
```
 
| Langue | Code |
|---|---|
| Français | `fr` |
| Anglais | `en` |
| Espagnol | `es` |
| Allemand | `de` |
| Italien | `it` |
| Portugais | `pt` |
| Arabe | `ar` |

Whisper reconnaît une centaine de langues ; la liste complète des codes se trouve dans le [dépôt de whisper](https://github.com/openai/whisper/blob/main/whisper/tokenizer.py). Si le code saisi n'existe pas (par exemple `francais` au lieu de `fr`), le script le signale et bascule en détection automatique de la langue.

### Choisir le modèle de transcription
Le modèle de calcul se choisit avec l'option `-m` (ou `--modele`). Deux modèles sont proposés, tous deux multilingues :
 
| Modèle | Quand l'utiliser | Poids à télécharger (ordre de grandeur) |
|---|---|---|
| `large-v3-turbo` (**par défaut**) | Bon compromis entre qualité et temps de calcul : adapté à la plupart des entretiens, y compris sur un ordinateur de bureau sans carte graphique. | 1,5 à 2 Go |
| `large-v3` | Précision maximale, à privilégier pour des enregistrements difficiles (accents marqués, bruit de fond, voix qui se chevauchent). Le calcul est nettement plus long. | environ 3 Go |
 
Sans l'option `-m`, le script utilise `large-v3-turbo`. Si le nom du modèle n'est pas l'un des deux ci-dessus, le script affiche la liste des valeurs acceptées et s'arrête.

> [!WARNING]
> **Conseil :** quel que soit le modèle choisi, faites tourner cet utilitaire à un moment où vous n'avez pas besoin de votre machine. Toutes les capacités de calcul seront mobilisées par la retranscription.

Les silences sont ignorés par un filtre de détection de la voix (Silero VAD), ce qui limite les phrases inventées par Whisper et les hallucinations dans les passages sans parole.

La retranscription démarre ensuite. Elle est stockée dans un fichier texte éponyme, dans le dossier courant.

> [!NOTE]
> **Téléchargement et suppression des modèles :** la première fois que vous mobiliserez un modèle, il faudra d'abord le télécharger, ce qui peut prendre un peu de temps. Chaque modèle n'est téléchargé qu'une fois : il est ensuite conservé dans le cache de l'utilisateur (`~/.cache/huggingface` sous Linux). Les modèles abandonnés (par exemple `large-v2` si vous utilisiez une ancienne version du script) peuvent être supprimés de ce dossier pour libérer de la place, en repérant les modèles présents avec la commande `ls ~/.cache/huggingface/hub`, puis en supprimant le modèle obsolète `rm -rf ~/.cache/huggingface/hub/modele-obsolete` (en remplaçant `modele-obsolete` par le vrai nom du modèle).

### Préciser le nombre de personnes
L'identification des personnes qui parlent (« diarisation ») est **toujours activée**. Par défaut, le script suppose **deux personnes** (un entretien en face à face), ce qui améliore la fiabilité de l'identification. Pour un entretien collectif ou un enregistrement avec plus de deux voix, indiquer le nombre exact de personnes avec l'option `-n` (ou `--nombre-personnes`) :
```
python3 transcrire_entretien.py fichier_audio_entretien.mp3 -l fr -n 3
```
Si le nombre indiqué ne correspond pas à la réalité (par exemple deux voix attendues alors que trois personnes parlent), l'identification sera moins fiable.

Si `pyannote.audio` n'est pas installé, ou si l'identification échoue, le script le signale et enregistre quand même la transcription, sans les noms des personnes.

## Formats de sortie
Le script produit **deux fichiers au même nom que le fichier audio**, dans le dossier courant :

- un fichier `.txt`, à lire ou à importer dans un logiciel de traitement de texte ;
- un fichier `.srt` (format de sous-titres), avec le même contenu, pour les logiciels d'analyse et d'encodage d'entretiens qui acceptent ce format (à vérifier selon votre logiciel).

Dans les deux fichiers, la parole est découpée **par tours de parole** : les phrases consécutives d'une même personne sont regroupées. Un tour de parole trop long est découpé en **paragraphes** (autour de 400 caractères, à la première fin de phrase), chacun portant l'étiquette de la personne et son horodatage. Les personnes sont nommées `Speaker 1`, `Speaker 2`, etc., dans l'ordre où elles apparaissent dans l'enregistrement.

Si l'identification des personnes n'est pas disponible, les deux fichiers contiennent simplement les segments de parole horodatés, sans nom ni regroupement.

## Améliorations
Des améliorations du script sont prévues mais le temps dont je dispose pour les mettre en œuvre est limité. Aussi, toute contribution est la bienvenue, en particulier s'agissant de rendre l'expérience d'utilisation la plus simple possible pour des personnes peu à l'aise avec la manipulation de ce genre de scripts. N'hésitez pas à ouvrir des issues avec des suggestions d'améliorations ou à forker le projet.

N'hésitez pas non plus à venir en discuter sur Mastodon : [@au_be@mamot.fr](https://mamot.fr/@au_be).

## Licence
Ce script est d'isponible sous la licence libre MIT. Voir le fichier [LICENSE](https://github.com/auberanger/faster-whisper-transcription-script/blob/main/LICENSE) pour plus d'informations.
