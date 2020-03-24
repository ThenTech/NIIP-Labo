import bluetooth
import traceback


def find_addr(device_name):
    found_addr = None

    nearby_devices = bluetooth.discover_devices(lookup_names=True)

    for bdaddr, name in nearby_devices:
        if name == device_name:
            found_addr = bdaddr
            break

    if found_addr is not None:
        print("Found device with address: " + found_addr)
    else:
        print("Could not find device")

    return found_addr

def find_service(bdaddr):
    service_matches = bluetooth.find_service(name = None, uuid = None, address = bdaddr)
    first_match = service_matches[0]
    print("Uses protocol: " + first_match["protocol"])


addr = find_addr('Xbox Wireless Controller')
find_service(addr)
try:
    sock = bluetooth.BluetoothSocket(bluetooth.L2CAP)
    print('Connecting with device...')
    sock.connect((addr, 3))
    print('Connected')
    data = sock.recv(1024)
    print("Got input: " + str(data))
except:
    print("Shithead, it didn't work")
    traceback.print_exc()
