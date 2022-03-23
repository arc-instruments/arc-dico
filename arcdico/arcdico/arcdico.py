"""
ArCDiCo is a thin wrapper around the serial port protocol of the ArC DiCo.
It abstracts away the packet encoding and decoding and its use should be
fairly straightforward.

>>> from arcdico import DiCo
>>> # open a new DiCo connection
>>> dico = DiCo('/dev/ttyUSB0')
>>> # disconnect all pins; set voltage to 0.0 V.
>>> dico.reset()
>>> # connect specified pins to the DAC output
>>> dico.set_state(pins=[1, 8, 22])
>>> # set output voltage at 3.50 VC
>>> dico.set_state(voltage=3.50)
>>> # or do both
>>> dico.set_state(pins=[1, 8], voltage=2.25)

See the documentation for the `DiCo` class for more specific information
on the methods provided.
"""

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
    """ Status code for DiCo responses """

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
    """ Command codes for DiCo operations """

    STATUS: int = 0x00
    """ Report status - always 0x0 for now """
    VERSION: int = 0x01
    """
    Report version - 16 bit integer: upper half: major; lower half: minor
    """
    OUTP_ENABLE: int = 0x02
    """ Enable output with voltage and switch bitmask """
    OUTP_DISABLE: int = 0x03
    """ Disable output """
    SET_VOLTAGE: int = 0x04
    """ Set voltage; don't touch switches """
    SET_PINS: int = 0x05
    """ Set switch bitmask; don't touch voltage """
    CLEAR: int = 0x06
    """ Reset everything to 0.0 V; switches open """


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
    """
    Entry object for the DiCo communication.  There are really only two methods
    the user should be interested in ``DiCo.set_state`` and ``DiCo.reset``. The
    first controls the switches (pins) and the voltage (or both) and the second
    resets the state of the DiCo back to the one it had during power up. Please
    note that the DiCo will reset itself on power cycling.
    """

    VMAX = 18.2589
    """ Maximum voltage the DiCo can support """
    DACMAX = 1024
    """ Maximum raw DAC value 2^{10} """
    PACKET_FORMAT = '<BxH4B'
    """
    Command packet format

    ```
    [Command (byte); _pad (byte); DAC value (half word); Switch bitmask (4 bytes)]
    ```
    """
    RESP_FORMAT = '<BxH'
    """
    Response packet format

    ```
    [Status (byte); _pad (byte); Payload (half word)].
    ```

    Payload is only populated when the DiCo sends the `EUNKNOWN` response and
    it includes the command that it received and could not process
    """

    def __init__(self, com):
        """
        Open a new DiCo connection at the specified serial port
        """
        self._port = Serial(com, baudrate=57600)

    def __make_data(self, command, voltage, mask):
        return struct.pack(self.PACKET_FORMAT, command,
            voltage, *_to_be_bytes(mask))

    def __idx_to_voltage(self, idx):
        return idx/self.DACMAX * self.VMAX

    def __voltage_to_idx(self, voltage):
        vidx = int((self.DACMAX * voltage)/self.VMAX)

        if vidx >= self.DACMAX:
            raise ValueError("Requested Voltage out of range")

        return vidx

    def __raise_if_not_ok(self, status):
        if status != Status.OK:
            raise DiCoException(Status(status))

    def __mask_from_pins(self, pins):
        if isinstance(pins, abc.Sequence) and not isinstance(pins, str):
            if len(pins) == 0:
                raise ValueError("Must provide a non-empty list of pins to connect")

            if max(pins) > 31:
                raise ValueError("Highest pin number must not exceed 31")
            # ensure selected pins are unique
            pins = set(pins)
            # find the channels that correspond to selected pins
            channels = [CHANMAP[i] for i in pins]
            # make the mask
            return sum([1 << x for x in channels])
        else:
            raise TypeError("Need a pin list to make mask")

    def reset(self):
        """
        Resets the DiCo (``Command.CLEAR``). This will set voltage to 0.0 V
        and open all switches
        """
        data = self.__make_data(Command.CLEAR, 0x0, 0x0)
        self._port.write(data)
        (status, _) = struct.unpack(self.RESP_FORMAT, self._port.read(4))
        self.__raise_if_not_ok(status)

    def set_state(self, pins=None, voltage=None):
        """
        This function is responsible for setting the state of the DiCo.  Either
        `pins`, `voltage` or both must be set otherwise a ``ValueError`` will
        be raised. Pins must be an array of switches the DiCo would connect.
        The indexes represent _physical_ pins fro 0 to 31. A ``ValueError``
        will be raised if the array has zero length or a channel > 31 is
        included. Please note that new `DiCo.set_state`s will overwrite older
        ones.
        """

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
        """ Current revision of the DiCo firmware `(major, minor)` """
        data = self.__make_data(Command.VERSION, 0x0, 0x0)
        self._port.write(data)

        (status, version) = struct.unpack(self.RESP_FORMAT, self._port.read(4))
        self.__raise_if_not_ok(status)

        (major, minor) = (version >> 8, version & 0xFF)

        return (major, minor)
