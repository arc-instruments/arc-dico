# ArC Digital Control Module

This is a Python wrapper for the ArC Digital Control (ArC DiCo) serial protocol.

## Usage

Usage of the library is fairly straightforward. You only to know the serial
port where the DiCo is connected to.

```python
from arcdico import DiCo

dico = DiCo('/dev/ttyUSB0')

# The DiCo will disable all outputs when initially
# powered on but you can do that programmatically by
# using the `reset` function.
dico.reset()

# connect specified pins to the DAC output
dico.set_state(pins=[1, 8, 22])

# set output voltage at 3.50 V
dico.set_state(voltage=3.50)

# or do both
dico.set_state(pins=[1, 8], voltage=2.25)
```
