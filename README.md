# Script whisper de retranscription automatique d'entretiens

Ce script a été écrit dans le but de simplifier l'utilisation de l'outil de retranscription automatique d'audio open-source [whisper](https://github.com/openai/whisper) d'OpenAI. L'entretien est un exercice routinier des enquêtes en sciences sociales. Bien qu'il ne soit pas toujours attendu d'en réaliser une retranscription intégrale, cela peut être pertinent dans de nombreux cas (codage de corpus d'entretiens, collaborations sur un corpus, etc.). Cet exercice, s'il a le mérite de permettre de gagner en familiarité avec le contenu de l'entretien, se révèle être particulièrement chronophage et incombant majoritairement aux précaires du monde de la recherche. 

Le but de ce script est de permettre de gagner du temps sur ce travail de transcription, gratuitement et dans le respect de la confidentialité des enquêté·es (les calculs se font en local). Il permet d'obtenir une __pré-transcription horodatée__, qui nécissite ensuite une passe manuelle pour rajouter les locuteurices et corriger les erreurs de retranscription. __Cet outil n’est donc pas un substitut à l’écoute attentive des entretiens.__

Je me suis inspiré de l'article de blog de [Yacine Chitour](https://www.css.cnrs.fr/whisper-pour-retranscrire-des-entretiens), pour réaliser un script optimisé, utilisant [faster-whisper](https://github.com/guillaumekln/faster-whisper), une réimplémentation de Whisper permettant d'accélérer significativement le temps de calcul.

Pour l'instant, je n'ai pu tester ce script que sous Linux. Des retours sur son fonctionnement et le guide d'utilisation avec d'autres systèmes d'exploitations sont les bienvenus.

## Installation
S'assurer d'avoir [Python](https://www.python.org/downloads/) installé sur son OS et que la version est supérieure ou égale à python 3.2. Cela peut être vérifié en tappant la commande suivante dans le terminal :
```
python3 --version
```

Prévoir quelques Go d'espace disque de libre pour l'installation des modèles de calcul, ça peut être assez gourmand. 

Commencez par créer un environnement virtuel dédié :
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

Installer ensuite [faster-whisper](https://github.com/guillaumekln/faster-whisper), avec la commande : 
```
pip install -U faster-whisper "av<19"
```
> [!NOTE]
> **Pourquoi `"av<19"` ?** faster-whisper utilise la bibliothèque PyAV (paquet `av`) pour lire les fichiers audio. La version 19 de PyAV (septembre 2026) n'est pas compatible avec la dernière version publiée de faster-whisper (1.2.1) : sans cette contrainte, la transcription s'arrête avec l'erreur `TypeError: open() got an unexpected keyword argument 'metadata_errors'"`. Cette contrainte pourra être retirée quand faster-whisper publiera une version corrigée (voir le [suivi]() du problème). Si vous rencontrez déjà cette erreur, lancez simplement `pip install "av<19"` dans l'environnement activé ou réinstallez complètement faster-whisper :
> ```
> pip install -U --force-reinstall av faster-whisper "av<19"
> ```

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


Whisper reconnaît une centaine de langues ; la liste complète des codes se trouve dans le dépôt de whisper. Si le code saisi n'existe pas (par exemple francais au lieu de fr), le script affiche un message d'erreur et s'arrête avant de lancer le calcul.

### Choix du modèle
Si le fichier est bien trouvé, il vous sera alors demandé de choisir le modèle de calcul :
```
Choisir un modèle de retranscription (détermine la qualité et le temps de calcul, 'large-v2' par défaut) :
1) large-v2
2) medium
3) small
Modèle à utiliser : _
```
J'utilise personnellement le modèle le plus puissant, `large-v2`, car la retranscription est plus précise et que mon ordinateur est relativement performant. 

> __Conseil :__ quelque soit le modèle choisi, faites tourner cet utilitaire à un moment où vous n'avez pas besoin de votre machine. Toutes les capacités de calcul seront mobilisées par la retransciption.

La première fois que vous mobiliserez un modèle, il faudra d'abord le télécharger, ce qui peut prendre un peu de temps (le modèle `large-v2` pèse pas loin de 3Go).

La retranscription démarre. La langue est détectée automatiquement à partir des premières dizaines de secondes du fichier audio. 

La retranscription du fichier audio est stockée dans un fichier texte éponyme, dans le dossier courant.

## Améliorations
Des améliorations du script sont prévues mais le temps dont je dispose pour les mettre en œuvre est limité. Aussi, toute contribution est la bienvenue, en particulier s'agissant de rendre l'expérience d'utilisation la plus simple possible pour des personnes peu à l'aise avec la manipulation de ce genre de scripts. N'hésitez pas à ouvrir des issues avec des suggestions d'améliorations ou à forker le projet.

N'hésitez pas non plus à venir en discuter sur Mastodon : [@au_be@mamot.fr](https://mamot.fr/@au_be).

## Licence
Ce script est d'isponible sous la licence libre MIT. Voir le fichier [LICENSE](https://github.com/auberanger/faster-whisper-transcription-script/blob/main/LICENSE) pour plus d'informations.