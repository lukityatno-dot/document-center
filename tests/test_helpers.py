import os
import tempfile
from app import compute_checksum, generate_thumbnail


def test_compute_checksum_and_thumbnail():
    data = b'hello world'
    tmp = tempfile.NamedTemporaryFile(delete=False)
    try:
        tmp.write(data)
        tmp.flush()
        tmp.close()
        checksum = compute_checksum(tmp.name)
        assert isinstance(checksum, str) and len(checksum) == 64

        # create a small image and thumbnail
        from PIL import Image
        img_path = tmp.name + '.jpg'
        im = Image.new('RGB', (100, 100), color='red')
        im.save(img_path)
        thumb_path = img_path + '.thumb.jpg'
        ok = generate_thumbnail(img_path, thumb_path, size=(50,50))
        assert ok and os.path.exists(thumb_path)
    finally:
        try:
            os.remove(tmp.name)
        except Exception:
            pass
        try:
            os.remove(img_path)
        except Exception:
            pass
        try:
            os.remove(thumb_path)
        except Exception:
            pass
