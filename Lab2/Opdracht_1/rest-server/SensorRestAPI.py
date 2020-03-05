from flask import Flask, request
from flask_restful import Resource, Api
from sqlalchemy import create_engine
from json import dumps
from flask_jsonpify import jsonify
from Crypto.PublicKey import RSA    # Requires PyCryptodome

from base64 import b64decode,b64encode
from datetime import datetime

import uuid

from os import path

db_file = path.join(path.dirname(__file__), "SensorDB.db")
db_file = db_file.replace('\\', '/')

print(db_file)

db_connect = create_engine('sqlite:///' + db_file)
app = Flask(__name__)
api = Api(app)

class Home(Resource):
    ROUTE = "/"

    def get(self):
        return "Welcome to the Super Burner 3000!"

class Notify(Resource):
    ROUTE = Home.ROUTE + "notify"

    def post(self):
        sensor_id = request.json['sensor_id']
        cipher = request.json['msg']

        conn = db_connect.connect()
        public_key = ""
        getKeys = conn.execute("SELECT public_key FROM keys WHERE sensor_id=\"" + sensor_id + "\";")

        for entry in getKeys.cursor.fetchall():
            public_key = entry[0]

        public_key = '-----BEGIN RSA PRIVATE KEY-----\n' + public_key + '\n-----END RSA PRIVATE KEY-----'

        #keyDER = b64decode(public_key)
        key = RSA.importKey(public_key)

        try:
            decrypted = key.decrypt(b64decode(cipher))
        except:
            self.notifyMaliciousAttempt()
            return {
                "error": "Could not decrypt message"
            }

        print("Decrypted message: "  + decrypted)

        if "temperature" in decrypted:
            print("Yes")
        else:
            self.notifyMaliciousAttempt()

    def notifyMaliciousAttempt(self) :
        print("Malicious attempt from " + request.remote_addr)
        id = str(uuid.uuid4())
        conn = db_connect.connect()
        query = conn.execute("INSERT INTO malicious_requests (`id`, `date`, `ip_address`) VALUES (\"" + id + "\", \"" + datetime.now() + "\", \"" + request.remote_addr + "\");")


class Keys(Resource):
    ROUTE = Home.ROUTE + "key"

    #Only for debugging purposes
    def get(self):
        conn = db_connect.connect()
        getKeys = conn.execute("SELECT * FROM keys")

        keys = []

        for entry in getKeys.cursor.fetchall():
            key = {
                "id": entry[0],
                "sensor_id": entry[1],
                "public_key": entry[2]
            }
            keys.append(key);

        return jsonify(keys)

    def post(self):
        id = str(uuid.uuid4())
        sensor_id = request.json["sensor_id"]
        key = request.json["public_key"]

        conn = db_connect.connect()

        getSensor = conn.execute("SELECT id FROM sensors WHERE id=\"" + sensor_id + "\";")
        amountSensors = len(getSensor.cursor.fetchall())

        if(amountSensors == 0):
            return {
                "error": "No sensor found with that ID"
            }

        deleteQuery = conn.execute("DELETE FROM keys WHERE sensor_id=\"" + sensor_id + "\";")

        query = conn.execute("INSERT INTO keys (`id`, `sensor_id`, `public_key`) VALUES (\"" + id + "\", \"" + sensor_id + "\", \"" + key + "\");")

        return {
            "response": "success"
        }



class Sensors(Resource):
    ROUTE = Home.ROUTE + "sensors"

    def get(self):
        conn = db_connect.connect()
        query = conn.execute("SELECT * FROM sensors")

        sensors = []

        for record in query.cursor.fetchall():
            sensor = {
                "id": record[0],
                "ip_address": record[1]
            }
            sensors.append(sensor)

        return jsonify(sensors)

    # Add sensor to the system
    def post(self):
        id = request.json["id"]
        ip_address = request.json["ip_address"]

        conn = db_connect.connect()
        deleteExisting = conn.execute("DELETE FROM sensors WHERE ip_address=\""+ ip_address + "\";")
        query = conn.execute("INSERT INTO sensors (`id`, `ip_address`) VALUES (\"" + id + "\", \"" + ip_address + "\");")

        response = {
            "id": id,
            "ip_address": ip_address
        }
        return response;


api.add_resource(Home        , Home.ROUTE)
api.add_resource(Sensors    , Sensors.ROUTE)
api.add_resource(Keys       , Keys.ROUTE)
api.add_resource(Notify     , Notify.ROUTE)


if __name__ == '__main__':
    app.run(port='5000', debug=True)
