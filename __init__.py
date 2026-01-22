from flask import Flask
import json
import pymongo
from flask_bcrypt import Bcrypt

with open('../config.json') as config_file:
    config = json.load(config_file)
app = Flask(__name__)
app.secret_key = config['SECRET_KEY']

client = pymongo.MongoClient(config['MONGO_URI'])
db = client.gopass_db
bcrypt = Bcrypt(app)

import routes