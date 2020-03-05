from flask import Flask, request
from flask_restful import Resource, Api
from sqlalchemy import create_engine
from json import dumps
from flask_jsonpify import jsonify

from os import path

db_file = path.join(path.dirname(__file__), "SensorDB.db")
db_file = db_file.replace('\\', '/')

print(db_file)

db_connect = create_engine('sqlite:///' + db_file)
app = Flask(__name__)
api = Api(app)

# Drop the existing tables
conn = db_connect.connect()
getAllTablesQuery = conn.execute("SELECT name FROM sqlite_master WHERE type='table'")
for gid in getAllTablesQuery.cursor.fetchall():

    print("Dropping table: " + gid[0])
    if gid[0] is not "sqlite_sequence":
        try:
            
            dropQuery = conn.execute("DROP TABLE " + gid[0])
            print "Dropped succesfully"
        except:
            print "Could not drop table"

# Create sensor table
createSensorTable = conn.execute("CREATE TABLE `sensors` ( `id` VARCHAR(255),`ip_address` VARCHAR(255),PRIMARY KEY (`id`));")

# Create key table
createKeyTable = conn.execute("CREATE TABLE `keys` (`id` VARCHAR(255), `sensor_id` VARCHAR(255), `public_key` VARCHAR(255), PRIMARY KEY(`id`));")

# Create attack notification table
createAttackTable = conn.execute("CREATE TABLE `malicious_requests` (`id` VARCHAR(255), `date` TIMESTAMP, `ip_address` VARCHAR(255), PRIMARY KEY(`id`));")