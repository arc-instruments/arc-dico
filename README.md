# ArC Digital Control Module

This repository includes the firmware and a python library for the ArC
Instruments Digital Control Module (DiCo). The DiCo provides 32 programmable
I/O pins. Since the DiCo is mostly intended with controlling selector
transistor circuits in memory crossbars the voltage levels are shared among
the I/O pins, so in that case it is not a general purpose I/O tool.

## Building the firmware

The bulk of this repository is boilerplate and drivers to initialise the
SAMD13AMU microcontroller that powers the DiCo. The main logic itself is
relatively straightforward and contained in `main.c`. To build the firmware you
will need the GNU ARM Embedded toolchain. On Linux it should be available from
your package manager; on Windows it's included in the
[MSYS2](https://www.msys2.org/) repositories (part of the Mingw64 toolchain);
on macOS it's available on
[homebrew](https://formulae.brew.sh/cask/gcc-arm-embedded) and also from
[ARM](https://developer.arm.com/tools-and-software/open-source-software/developer-tools/gnu-toolchain).
The ARM compilers should also be able to compile the firmware although it's
fully untested and unsupported. Once you obtain the GNU ARM toolchain descent
into `gcc` and type `make`. The compiler should produce an
`ArCDico{bin,elf,hex}` set of outputs.

## Flashing the board

You will need a CMSIS-DAP probe to flash the μC. Any SWD supporting board
should work, including inexpensive ones such as
[MCU-LINK](https://www.nxp.com/design/microcontrollers-developer-resources/mcu-link-debug-probe:MCU-LINK).
OpenOCD can be used to flash the firmware. Other options include FT232H-based
solutions or you can use fancy programmers such as the J-Link that can talk the
SWD protocol. Connect the 2×5 header on the board and from the top-level
directory, once you build the firmware, type

```
openocd -f ocd.cfg -c "program gcc/ArCDiCo.elf verify reset exit"
```

The μC will be reset and it's ready for operation. It accepts commands over
serial with baud 57600. A simple [Python
wrapper](https://github.com/arc-instruments/arc-dico/tree/master/arcdico) is
provided.

## License

Bootstrapping code provided by Atmel/Microchip is licensed under Apache
Software Foundation License 2.0. This covers code under the `config`, `hal`,
`hpl`, `hri`, `include`, `CMSIS` as well as the startup code for SAMD10D13
(`gcc/gcc/startup_samd10.c`). Everything else is licensed under the Mozilla
Public License 2.0.
