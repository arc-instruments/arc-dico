/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */
#ifndef DRIVER_INIT_INCLUDED
#define DRIVER_INIT_INCLUDED

#include "pinconf.h"

#ifdef __cplusplus
extern "C" {
#endif

#include <hal_atomic.h>
#include <hal_delay.h>
#include <hal_gpio.h>
#include <hal_init.h>
#include <hal_io.h>
#include <hal_sleep.h>

#include <spi_lite.h>

#include <hal_usart_sync.h>

#include <hal_delay.h>

#include <hal_dac_sync.h>

extern struct usart_sync_descriptor USART_0;

extern struct dac_sync_descriptor DAC_0;

void   SPI_0_PORT_init(void);
void   SPI_0_CLOCK_init(void);
int8_t SPI_0_init(void);

void USART_0_PORT_init(void);
void USART_0_CLOCK_init(void);
void USART_0_init(void);

void delay_driver_init(void);

void DAC_0_PORT_init(void);
void DAC_0_CLOCK_init(void);
void DAC_0_init(void);

void system_init(void);

#ifdef __cplusplus
}
#endif
#endif // DRIVER_INIT_INCLUDED
