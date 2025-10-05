import os
import json
import shutil
import uuid
from datetime import datetime

ROOT = os.path.dirname(os.path.abspath(__file__))
HISTORY_DIR = os.path.join(ROOT, 'history')
IMAGES_DIR = os.path.join(HISTORY_DIR, 'images')
HISTORY_FILE = os.path.join(HISTORY_DIR, 'history.json')


def _ensure_dirs():
    os.makedirs(IMAGES_DIR, exist_ok=True)


def _load_history_list():
    if not os.path.exists(HISTORY_FILE):
        return []
    try:
        with open(HISTORY_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def _save_history_list(lst):
    _ensure_dirs()
    with open(HISTORY_FILE, 'w', encoding='utf-8') as f:
        json.dump(lst, f, ensure_ascii=False, indent=2)


def save_history_entry(analysis_data: dict, image_paths: list) -> dict:
    """Save analysis result and copy images into history folder.

    Returns the saved entry.
    """
    _ensure_dirs()
    entry_id = str(uuid.uuid4())
    ts = datetime.utcnow().isoformat() + 'Z'

    saved_images = []
    for idx, p in enumerate(image_paths):
        if not os.path.exists(p):
            continue
        ext = os.path.splitext(p)[1]
        fname = f"{entry_id}_{idx}{ext}"
        dst = os.path.join(IMAGES_DIR, fname)
        try:
            shutil.copy2(p, dst)
            saved_images.append(os.path.relpath(dst, ROOT))
        except Exception:
            # ignore copy errors
            pass

    entry = {
        'id': entry_id,
        'timestamp': ts,
        'name': analysis_data.get('name', 'N/A'),
        'category': analysis_data.get('category', 'N/A'),
        'summary': {
            'energy_value': analysis_data.get('characteristics', {}).get('energy_value'),
            'total_sugar': analysis_data.get('characteristics', {}).get('total_sugar'),
        },
        'analysis': analysis_data,
        'images': saved_images,
    }

    lst = _load_history_list()
    lst.insert(0, entry)  # newest first
    _save_history_list(lst)
    return entry


def load_history():
    """Return list of history entries (newest first)."""
    lst = _load_history_list()
    # ensure sorted by timestamp desc
    try:
        lst.sort(key=lambda x: x.get('timestamp', ''), reverse=True)
    except Exception:
        pass
    return lst


def delete_history_entry(entry_id: str) -> bool:
    """Delete history entry by id and remove associated image files.

    Returns True if an entry was deleted.
    """
    lst = _load_history_list()
    new_lst = []
    removed = False
    for entry in lst:
        if entry.get('id') == entry_id:
            # delete images
            for img_rel in entry.get('images', []):
                img_path = os.path.join(ROOT, img_rel)
                try:
                    if os.path.exists(img_path):
                        os.remove(img_path)
                except Exception:
                    pass
            removed = True
            continue
        new_lst.append(entry)

    if removed:
        _save_history_list(new_lst)
    return removed
