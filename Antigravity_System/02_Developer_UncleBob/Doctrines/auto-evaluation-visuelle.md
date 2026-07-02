# Auto-évaluation visuelle : produire, regarder, corriger

> Le geste signature de `fabuleux`. Un artefact qui se *regarde* n'est pas fini tant qu'on ne l'a pas
> regardé. Cette page donne le protocole concret et les commandes par type d'artefact (macOS, Windows, Linux).

## Le principe

Croire qu'un visuel est bon ≠ savoir qu'il est bon. La seule preuve, c'est de le **rendre en image**,
de **l'ouvrir avec la vision**, et de **lister ce que l'œil révèle** avant de corriger. On ne livre
jamais un visuel qu'on n'a jamais affiché.

La boucle :

```
PRODUIRE → CAPTURER (screenshot) → REGARDER (vision : Read sur l'image) → LISTER les défauts → CORRIGER → RE-CAPTURER
```

Re-capture après correction : une correction est elle-même une hypothèse. On boucle jusqu'à ce que
l'œil ne trouve plus de défaut bloquant.

## Ce qu'on cherche en regardant

Ne te contente pas de « ça a l'air bien ». Passe en revue, concrètement :

- **Débordements / coupures** : texte qui sort du cadre, lignes tronquées, chevauchements.
- **Alignement & grille** : éléments désalignés, marges incohérentes, centrage raté.
- **Hiérarchie** : le titre se lit-il en premier ? L'œil sait-il où aller ?
- **Lisibilité** : contraste suffisant, taille de police, espacement, texte sur fond chargé.
- **Cohérence de style** : polices, couleurs, rayons, ombres homogènes.
- **Rendu réel des polices/icônes/emojis** : ce qui s'affiche ≠ ce qu'on a écrit (police manquante, glyphe cassé).
- **Fidélité au contenu** : les bons chiffres, les bons libellés, pas de Lorem ipsum oublié.
- **Responsive** (si web) : capturer à au moins deux largeurs (desktop + mobile).

## Commandes par type d'artefact

### Page web / HTML local

Préférer un navigateur headless pour un rendu fidèle (CSS, polices, JS). Le binaire Chrome/Edge selon l'OS :

| OS | Binaire (chemin par défaut) |
|---|---|
| macOS | `/Applications/Google Chrome.app/Contents/MacOS/Google Chrome` |
| Windows | `C:\Program Files\Google\Chrome\Application\chrome.exe` (ou Edge : `C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe`) |
| Linux | `google-chrome` ou `chromium` (souvent déjà dans le PATH) |

macOS / Linux (bash) :

```bash
CHROME="/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"   # ou: google-chrome
"$CHROME" --headless --disable-gpu --screenshot="/tmp/shot.png" \
  --window-size=1280,1600 --hide-scrollbars \
  "file:///chemin/absolu/vers/page.html"

# Deux largeurs pour vérifier le responsive
for w in 1280 390; do
  "$CHROME" --headless --disable-gpu \
    --screenshot="/tmp/shot_${w}.png" --window-size=${w},1600 --hide-scrollbars \
    "file:///chemin/absolu/page.html"
done
```

Windows (PowerShell) :

```powershell
$chrome = "C:\Program Files\Google\Chrome\Application\chrome.exe"   # ou msedge.exe
& $chrome --headless --disable-gpu --screenshot="$env:TEMP\shot.png" `
  --window-size=1280,1600 --hide-scrollbars `
  "file:///C:/chemin/absolu/vers/page.html"

# Deux largeurs (responsive)
foreach ($w in 1280,390) {
  & $chrome --headless --disable-gpu --screenshot="$env:TEMP\shot_$w.png" `
    --window-size="$w,1600" --hide-scrollbars "file:///C:/chemin/absolu/page.html"
}
```

Si Playwright est dispo dans le projet, c'est encore mieux (capture pleine page, attente du chargement), et **identique sur tous les OS** :

```bash
npx playwright screenshot --full-page --viewport-size=1280,800 "file:///chemin/page.html" shot.png
```

Puis **regarde l'image** :

```
Read /tmp/shot.png
```

### Image générée (PNG/JPG)

L'artefact EST déjà une image : il suffit de la regarder. Ne valide jamais une image générée sans l'ouvrir.

```
Read /chemin/vers/image.png
```

Contrôle en plus : texte natif lisible et bien orthographié (les générateurs déforment le texte),
pas de doublon de label, accents corrects, pas de bandeau/watermark parasite.

### PDF / document rendu

Le plus simple, multi-OS : le tool `Read` lit **directement** les PDF (paramètre `pages`) : utilise-le en priorité pour les documents, sans conversion.

Si tu as besoin d'un PNG :

```bash
# macOS : sips (natif). Sinon, pdftoppm (Poppler) ou ImageMagick, dispo sur les 3 OS.
sips -s format png /chemin/doc.pdf --out /tmp/doc.png 2>/dev/null \
  || pdftoppm -png -r 120 /chemin/doc.pdf /tmp/doc
```

```powershell
# Windows (PowerShell) : pdftoppm (Poppler) ou ImageMagick
pdftoppm -png -r 120 "C:\chemin\doc.pdf" "$env:TEMP\doc"   # ou: magick -density 120 doc.pdf doc.png
```

### Schéma / deck (ex. HTML animé en screen-share)

Capturer l'état de chaque étape clé, pas seulement la première. Si le deck a des fragments révélés
par flèches, screenshote au moins le premier et le dernier état de chaque planche, et vérifie que
rien ne déborde de la zone visible (la mise à l'échelle a-t-elle bien tenu ?).

### App / fenêtre à l'écran (capture native de l'OS)

```bash
# macOS
screencapture -x /tmp/screen.png            # plein écran, sans son
screencapture -x -R0,0,1280,800 /tmp/r.png  # région x,y,w,h
```

```powershell
# Windows (PowerShell) : capture plein écran via .NET
Add-Type -AssemblyName System.Windows.Forms,System.Drawing
$b = [System.Windows.Forms.SystemInformation]::VirtualScreen
$bmp = New-Object System.Drawing.Bitmap $b.Width, $b.Height
[System.Drawing.Graphics]::FromImage($bmp).CopyFromScreen($b.Location, [System.Drawing.Point]::Empty, $b.Size)
$bmp.Save("$env:TEMP\screen.png")
```

```bash
# Linux : ImageMagick ou grim (Wayland)
import -window root /tmp/screen.png        # ImageMagick (X11)   |  ou: grim /tmp/screen.png
```

Le plus fiable reste de capturer ce que tu produis via le navigateur headless / Playwright (ci-dessus) plutôt que l'écran entier.

### Artefact INTERACTIF (app, formulaire, mini-jeu, to-do) : l'exercer, pas seulement le regarder

C'est ce que faisait Fable 5 : il lançait un aperçu réel et **y exécutait les interactions** avant de livrer.
Regarder ne suffit pas pour de l'interactif : il faut **dérouler le scénario** : saisir, cliquer, valider, recharger,
et vérifier le résultat. Sans navigateur scriptable, raisonne le JS pas à pas ; avec, exécute pour de vrai :

```bash
# exercer l'app dans une page rendue (Playwright si dispo) : remplir, cliquer, lire le résultat
npx playwright ... # ou un petit harnais Node qui charge le JS et appelle les handlers
```

Check : chaque action promise marche (ajouter, cocher, supprimer, filtrer, calculer), les états vides/erreur
s'affichent, le compteur/total est juste. Une interaction supposée n'est pas une interaction testée.

## Règle d'arrêt

On arrête de boucler quand l'œil ne trouve plus de défaut **bloquant** (un défaut cosmétique mineur
peut être signalé sans bloquer la livraison, mais il est *signalé*, pas caché). Et on rapporte
honnêtement : « capturé, regardé, voici les 2 points corrigés, voici l'état final ».
