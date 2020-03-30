# NIIP-Labo 3 MQTT & ZigBee
> **Bram Kelchtermans, William Thenaers**

## Part 2: BLE to MQTT relay

To run the BLE2MQTT relay, `cd` into the `BLE2MQTT` directory and run:

```sh
python3 main.py 
```

For the MQTT Client, `cd` into the `MQTTClient` directory and also run:

```sh
python3 main.py 
```

Both depend on `paho.mqtt`, the relay also uses `bluetooth`. For the client, `pyxinput` is used to emulate a virtual controller.

```
pip install paho-mqtt
pip install PyBluez
pip install PYXInput
```

For Windows, also install the virtual bus driver by running `tools/ScpVBus-x64/install.bat` as admin.

**WARNING** The pip package for `PYXInput` contains a bug: in the file `virtual_controller.py`, change `target_type` on line 128 to `target_value`.

#### Explanation

![schema](0_schema.png)

