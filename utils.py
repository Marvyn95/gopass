import os
import secrets
from __init__ import app

def save_image(file):
    random_hex = secrets.token_hex(8)
    _, f_ext = os.path.splitext(file.filename)
    image_name = random_hex + f_ext
    image_path = os.path.join(app.root_path, 'static/event_images', image_name)
    file.save(image_path)
    return image_name

def delete_image(image_name):
    image_path = os.path.join(app.root_path, 'static/event_images', image_name)
    if os.path.exists(image_path):
        os.remove(image_path)