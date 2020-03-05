# main.py -- put your code here!
from machine import UART
from machine import Pin
import pycom
import time
pycom.heartbeat(False)

# this uses the UART_1 default pins for TXD and RXD (``P3`` and ``P4``)
uart = UART(1, baudrate=9600, pins=('P20', 'P21'))
p_in = Pin('P10', mode=Pin.IN, pull=Pin.PULL_DOWN)


def read_all():
    text = ""
    read_bytes = 0
    while read_bytes < 2048:
        nbytes = uart.any()
        if nbytes:
            read_bytes += nbytes
            try:
                bytesin = uart.read(nbytes)
                if bytesin:
                    text += bytesin.decode("utf-8")
            except:
                pass
            nbytes = 0
        else:
            break

    return text

print("Starting...")

while True:
    btn_val = p_in() # get value, 0 or 1

    if (btn_val == 1):
        pycom.rgbled(0x1000)
        print("Sending spin to pull lever.")
        uart.write(b'spin')
        pycom.rgbled(0x0000)

    result = read_all()
    if result: print(result)
    time.sleep(0.2)
