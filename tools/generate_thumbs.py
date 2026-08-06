import os
from PIL import Image

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
UPLOAD_FOLDER = os.path.join(PROJECT_ROOT, 'files')
THUMB_FOLDER = os.path.join(PROJECT_ROOT, 'static', 'thumbs')

os.makedirs(THUMB_FOLDER, exist_ok=True)

IMAGE_EXTS = {'.jpg', '.jpeg', '.png', '.gif'}

created = []
updated = []
skipped = []
errors = []

for name in sorted(os.listdir(UPLOAD_FOLDER)):
    src = os.path.join(UPLOAD_FOLDER, name)
    if not os.path.isfile(src):
        continue
    ext = os.path.splitext(name)[1].lower()
    if ext not in IMAGE_EXTS:
        skipped.append(name)
        continue

    thumb_name = f"thumb_{name}.jpg"
    dest = os.path.join(THUMB_FOLDER, thumb_name)

    try:
        regenerate = True
        if os.path.exists(dest):
            # only regenerate if source is newer
            if os.path.getmtime(dest) >= os.path.getmtime(src):
                regenerate = False

        if regenerate:
            with Image.open(src) as img:
                if img.mode not in ("RGB", "RGBA"):
                    img = img.convert("RGB")
                img.thumbnail((300, 300))
                img.save(dest, format='JPEG', quality=85)

            if regenerate and not os.path.exists(dest):
                errors.append(name)
            else:
                created.append(name)
        else:
            updated.append(name)
    except Exception as e:
        errors.append(f"{name}: {e}")

print('--- Thumbnail generation summary ---')
print('Created:', len(created))
print('Up-to-date (skipped regen):', len(updated))
print('Skipped (not images):', len(skipped))
print('Errors:', len(errors))
if created:
    print('\nCreated files:')
    for n in created:
        print(' -', n)
if errors:
    print('\nErrors:')
    for e in errors:
        print(' -', e)
print('\nThumbnails are in:', THUMB_FOLDER)
