from flask import Flask, request
from flask_restful import Resource, Api
from sqlalchemy import create_engine
from json import dumps
from flask_jsonpify import jsonify
from Crypto.PublicKey import RSA
from base64 import b64decode,b64encode
from datetime import datetime
import rsa
import json
import sys
import argparse

import uuid

from os import path

config = {
    "crit_temp": 51.23,
    "crit_msg": "LP0 is on fire"
}

success_response = {
    "msg": "Success"
}

error_response = {
    "msg": "Error"
}

db_file = path.join(path.dirname(__file__), "SensorDB.db")
db_file = db_file.replace('\\', '/')

print(db_file)

db_connect = create_engine('sqlite:///' + db_file)
app = Flask(__name__)
api = Api(app)

def encrypt_json(json):
    key = RSA.importKey(open("cert/public.pem", "rb"))
    plain = "{"
    for par in json:
        val = json[par]
        plain += "\""+ par + "\":"
        if isinstance(val, (int, long, float, complex)):
            plain += str(val) + ","
        else:
             plain +="\"" + str(val) + "\","
    
    plain = plain[:-1]
    plain += "}"

    cipher = b64encode(rsa.encrypt(plain, key))
    return cipher

def verify_signature(signature, sensor_id):
    data = str(sensor_id) + "_niip"
    key = RSA.importKey(open("cert/public.pem", "rb"))

    return rsa.verify(data, b64decode(signature), key)

def notifyMaliciousAttempt(descr) :
    print("Malicious attempt from " + request.remote_addr)
    id = str(uuid.uuid4())
    conn = db_connect.connect()
    query = conn.execute("INSERT INTO malicious_requests (`id`, `date`, `ip_address`, `descr`) VALUES (\"" + id + "\", \"" + str(datetime.now()) + "\", \"" + request.remote_addr + "\", \"" + descr + "\");")

def notifyFire(sensor_id, temp):
    conn = db_connect.connect()
    query = conn.execute("INSERT INTO fires (`sensor_id`, `date`, `temperature`) VALUES (\"" + sensor_id + "\", \"" + str(datetime.now()) + "\", "+ str(temp) + ")")




class Home(Resource):
    ROUTE = "/"

    def get(self):
        return "Welcome to the Super Burner 3000!"

class Config(Resource):
    ROUTE = Home.ROUTE + "config"

    def get(self):
        try:
            sensor_id = request.json['id']
            signature = request.json['signature']
            isLegit = verify_signature(signature, sensor_id)

            if not isLegit:
                notifyMaliciousAttempt("Wrong signature")
                return {
                    "msg": "You sneaky bastard"
                }

            payload = config 
            if use_encryption:
                payload = encrypt_json(config)


            response = {
                "msg": payload
            }

            return response
        except :
            notifyMaliciousAttempt("CONFIG_GET: " + str(sys.exc_info()[0]))
            return error_response



class Notify(Resource):
    ROUTE = Home.ROUTE + "notify"
    def get(self):
        conn = db_connect.connect()

    def post(self):
        try:
            sensor_id = request.json['id']
            signature = request.json['signature']
            cipher = request.json['msg']

            #Verify signature
            isLegit = verify_signature(signature, sensor_id)

            if not isLegit:
                notifyMaliciousAttempt("NOTIFY_POST: Wrong signature")
                return {
                    "msg": "You sneaky bastard"
                }
                
            #Get private key of sensor
            conn = db_connect.connect()
            private_key = ""
            getKeys = conn.execute("SELECT private_key FROM sensors WHERE id=\"" + sensor_id + "\";")

            for entry in getKeys.cursor.fetchall():
                private_key = entry[0]
           
            key = RSA.importKey(private_key)

            try:
                if use_encryption:
                    decrypted = rsa.decrypt(b64decode(cipher), key)
                    decrypted = json.loads(decrypted)
                else:
                    decrypted = cipher
            except:
                return {
                    "error": "Could not decrypt message"
                }
            print decrypted
            temp = decrypted["temperature"]
           
            notifyFire(sensor_id, temp)
            return success_response
        except:
            notifyMaliciousAttempt("NOTIFY_POST: " + str(sys.exc_info()))
            return error_response
        
        

    

class Sensors(Resource):
    ROUTE = Home.ROUTE + "sensors"
    
    def get(self):
        try:
            conn = db_connect.connect()
            query = conn.execute("SELECT * FROM sensors")

            sensors = []

            for record in query.cursor.fetchall():
                sensor = {
                    "id": record[0]
                }
                sensors.append(sensor)
            

            return jsonify(sensors)
        except:
            notifyMaliciousAttempt("SENSORS_GET: " + str(sys.exc_info()[0]))
            return error_response

    # Add sensor to the system
    def post(self):
        # try:
            id = request.json["id"]
            signature = request.json["signature"]

            isLegit = verify_signature(signature, id)

            if not isLegit:
                notifyMaliciousAttempt("SENSORS_POST: Wrong signature")
                return {
                    "msg": "You sneaky bastard"
                }

            public, private = rsa.newkeys(2048)

            private_key = private.exportKey()
            


            conn = db_connect.connect()
            deleteExisting = conn.execute("DELETE FROM sensors WHERE id=\""+ id + "\";")
            query = conn.execute("INSERT INTO sensors (`id`, `private_key`) VALUES (\"" + id + "\", \"" + private_key + "\");")

            return {
                "public_key": b64encode(public.exportKey())
            };
        # except:
        #     notifyMaliciousAttempt("SENSORS_POST: " + str(sys.exc_info()[0]))
        #     return error_response;

class Debug(Resource):
    ROUTE = Home.ROUTE + "debug"

    def post(self):
        id = request.json["id"]
        signature = request.json["signature"]

        verify_signature(signature, id)

class MaliciousAttempts(Resource):
    ROUTE = Home.ROUTE + "malicious_attempts"

    def get(self):
        conn = db_connect.connect()
        query = conn.execute("SELECT * FROM malicious_requests")

        attempts = []

        for row in query.cursor.fetchall():
            attempt = {
                "id": row[0],
                "date": row[1],
                "ip_address": row[2],
                "descr": row[3]
            }
            attempts.append(attempt)
        
        return jsonify(attempts)

class Fires(Resource):
    ROUTE = Home.ROUTE + "fires"

    def get(self):
        conn = db_connect.connect()
        query = conn.execute("SELECT * FROM fires")

        fires = []

        for row in query.cursor.fetchall():
            fire = {
                "sensor_id": row[0],
                "date": row[1],
                "temperature": row[2]
            }
            fires.append(fire)

        return jsonify(fires)


api.add_resource(Home        , Home.ROUTE)
api.add_resource(Sensors    , Sensors.ROUTE)
api.add_resource(Notify     , Notify.ROUTE)
api.add_resource(Debug      , Debug.ROUTE)
api.add_resource(Config     , Config.ROUTE)
api.add_resource(MaliciousAttempts, MaliciousAttempts.ROUTE)
api.add_resource(Fires      , Fires.ROUTE)

use_encryption = False


if __name__ == '__main__':
    app.run(host='10.42.0.1', port='5000', debug=True, ssl_context=('cert/cert.pem', 'cert/key.pem'))
    # app.run(host='10.42.0.1', port='5000', debug=True)
