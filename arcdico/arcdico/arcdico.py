import time
import struct
from enum import IntEnum
from serial import Serial
from collections import abc


def _to_be_bytes(num):
    return num.to_bytes(4, byteorder='big')


class DiCoException(Exception):
    pass


class Status(IntEnum):
    # all good
    OK: int = 0
    # DAC value out of range
    EDACRANGE: int = 1
    # Unknown command
    EUNKNOWN: int = 2

    def __str__(self):
        if self == Status.OK:
            return "OK"
        elif self == Status.EDACRANGE:
            return "DAC voltage out of range"
        elif self == Status.EUNKNOWN:
            return "Unknown command"
        else:
            return super().__str__()

    @staticmethod
    def from_code(num):
        return Status(num)


class Command(IntEnum):
    STATUS: int = 0x00
    VERSION: int = 0x01
    OUTP_ENABLE: int = 0x02
    OUTP_DISABLE: int = 0x03
    SET_VOLTAGE: int = 0x04
    SET_PINS: int = 0x05
    CLEAR: int = 0x06


# convert header pin to switch bit
CHANMAP = [ 0,  1,  2,  3, \
            7,  6,  5,  4, \
            8,  9, 10, 11, \
           15, 14, 13, 12, \
           16, 17, 18, 19, \
           23, 22, 21, 20, \
           24, 25, 26, 27, \
           31, 30, 29, 28]


class DiCo:

    VMAX = 15.0
    DACMAX = 1024
    PACKET_FORMAT = '<BxH4B'
    RESP_FORMAT = '<BxH'

    def __init__(self, com):
        self._port = Serial(com, baudrate=57600)

    def __make_data(self, command, voltage, mask):
        return struct.pack(self.PACKET_FORMAT, command,
            voltage, *_to_be_bytes(mask))

    def __idx_to_voltage(self, idx):
        return idx/self.DACMAX * self.VMAX

    def __voltage_to_idx(self, voltage):
        vidx = int((self.DACMAX * voltage)/self.VMAX)

        if vidx > self.DACMAX:
            raise ValueError("Requested Voltage out of range")

        return vidx

    def __raise_if_not_ok(self, status):
        if status != Status.OK:
            raise DiCoException(Status(status))

    def __mask_from_pins(self, pins):
        if isinstance(pins, abc.Sequence) and not isinstance(pins, str):
            # ensure selected pins are unique
            pins = set(pins)
            # find the channels that correspond to selected pins
            channels = [CHANMAP[i] for i in pins]
            # make the mask
            return sum([1 << x for x in channels])
        else:
            raise TypeError("Need a pin list to make mask")

    def reset(self):
        data = self.__make_data(Command.CLEAR, 0x0, 0x0)
        self._port.write(data)
        (status, _) = struct.unpack(self.RESP_FORMAT, self._port.read(4))
        self.__raise_if_not_ok(status)

    def set_state(self, pins=None, voltage=None):

        if (pins is None) and (voltage is None):
            raise ValueError("At least one of (pins, voltage) is required")

        if (pins is None) and (voltage is not None):
            cmd = Command.SET_VOLTAGE
            vidx = self.__voltage_to_idx(voltage)
            # switch mask is ignored on SET_VOLTAGE
            mask = 0x0
        elif (pins is not None) and (voltage is None):
            cmd = Command.SET_PINS
            mask = self.__mask_from_pins(pins)
            # voltage is ignored on SET_PINS
            vidx = 0x0
        else:
            cmd = Command.OUTP_ENABLE
            vidx = self.__voltage_to_idx(voltage)
            mask = self.__mask_from_pins(pins)

        data = self.__make_data(cmd, vidx, mask)
        self._port.write(data)
        (status, _) = struct.unpack(self.RESP_FORMAT, self._port.read(4))
        self.__raise_if_not_ok(status)

    @property
    def version(self):
        data = self.__make_data(Command.VERSION, 0x0, 0x0)
        self._port.write(data)

        (status, version) = struct.unpack(self.RESP_FORMAT, self._port.read(4))
        self.__raise_if_not_ok(status)

        (major, minor) = (version >> 8, version & 0xFF)

        return (major, minor)
