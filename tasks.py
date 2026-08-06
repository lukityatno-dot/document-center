"""
Background tasks for RQ. If RQ isn't used, functions can be imported and called directly.
"""
from PIL import Image
import os


def generate_thumbnail_task(src_path, dest_path, size=(300,300)):
    try:
        with Image.open(src_path) as img:
            if img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            img.thumbnail(size)
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            img.save(dest_path, format='JPEG', quality=85)
            return True
    except Exception as e:
        return False
