import pycom
import machine
import time

use_uart = False
uart = None

if use_uart:
    from machine import UART
    uart = UART(1, baudrate=9600, pins=('P20','P21'))


def write(text):
    if use_uart and uart:
        uart.write(text)
    else:
        print(text, end="")

def read(prompt=""):
    if use_uart and uart:
        if prompt: write(prompt)
        while not uart.any(): continue
        return uart.readline()
    else:
        return input(prompt)


class SlotMachine:
    class Commands:
        SPIN = b"spin"   # Pull lever and see results
        QUIT = b"quit"   # Quit playing

    class Values:
        CHERRY = 0
        LEMON  = 1
        ORANGE = 2
        PLUM   = 3
        BELL   = 4
        BAR    = 5
        SEVEN  = 6

    _payout = {
        Values.CHERRY: 1,
        Values.LEMON : 5,
        Values.ORANGE: 7,
        Values.PLUM  : 12,
        Values.BELL  : 15,
        Values.BAR   : 20,
        Values.SEVEN : 'jackpot'
    }

    _cmds   = [Commands.SPIN, Commands.QUIT]
    _values = list(range(1, Values.SEVEN + 1))
    _names  = {
        Values.CHERRY: "\033[41;1m\033[37;1m CHERRY \033[0m",
        Values.LEMON : "\033[43;1m\033[30m  LEMON \033[0m",
        Values.ORANGE: "\033[43m\033[31;1m ORANGE \033[0m",
        Values.PLUM  : "\033[45m\033[37;1m  PLUM  \033[0m",
        Values.BELL  : "\033[46m\033[37m  BELL  \033[0m",
        Values.BAR   : "\033[44m\033[33m  BAR   \033[0m",
        Values.SEVEN : "\033[47;1m\033[31m SEVEN  \033[0m",
    }

    def __init__(self):
        super().__init__()
        self.jackpot = 1000
        self.credits = 50

        write("Welcome to PyCom Slots!\r\n")
        write("Available commands: {0}\r\n".format(self._cmds))


    def __random_slot(self):
        return machine.rng() % (len(self._values) + 1)

    def next_pull(self):
        won_amount = 1
        self.credits -= won_amount
        self.jackpot += won_amount

        write("Putting in {0} credit and pulling lever...  ({1} credits left)\r\n".format(won_amount, self.credits))

        slot1, slot2, slot3 = self.__random_slot(), self.__random_slot(), self.__random_slot()

        write("Result: " + '  '.join(map(lambda s: "{0:^8}".format(self._names[s]), (slot1, slot2, slot3))) + "\r\n")


        if slot1 == slot2 == slot3:
            # All the same
            won_amount = self._payout[slot1]

            if won_amount == self._payout[self.Values.SEVEN]:
                # Jackpot
                won_amount = self.jackpot
                write("Congratulations! You won the jackpot of {0} credits!\r\n".format(won_amount))
            else:
                write("Congratulations! You won {0} credits!\r\n".format(won_amount))

            self.credits += won_amount
            self.jackpot -= won_amount

    def play_round(self):
        cmd = read("Enter command: ")

        if cmd:
            cmd = cmd.strip().lower()
            if cmd and isinstance(cmd, str):
                write(cmd + "\r\n")
                cmd = bytes(cmd, 'utf-8')
            else:
                write(cmd + "\r\n")

            if cmd == self.Commands.QUIT:
                write("Thanks for playing! Your total payout: € {0}\r\n".format(self.credits))
                return False
            elif cmd == self.Commands.SPIN:
                self.next_pull()
                if self.credits > 0:
                    return True
                else:
                    write("Out of credits! See you next time, addict!\r\n")
                    return False
            else:
                write("Invalid command! Try again.\r\n")
        else:
            #write("Invalid command! Try again.\r\n")
            pass

        return True


# Main
if __name__ == "__main__":
    # Disable heartbeat
    pycom.heartbeat(False)
    slots = SlotMachine()

    while slots.play_round(): pass
