/*
 * This Source Code Form is subject to the terms of the Mozilla Public
 * License, v. 2.0. If a copy of the MPL was not distributed with this
 * file, You can obtain one at https://mozilla.org/MPL/2.0/.
 */
#include "driver_init.h"

/**
 *  DiCo firmware version
 */
#define DICO_VER 0x0100

/**
 * Error codes
 */
#define EOK       0 // All good!
#define EDACRANGE 1 // DAC Out of range
#define EUNKNOWN  2 // Unknown command

/**
 * Commands
 */
// Report current status
#define CMD_STATUS       0x00
// Report firmware version
#define CMD_VERSION      0x01
// Set voltage and switches
#define CMD_OUTP_ENABLE  0x02
// Disconnect switches; keep voltage
#define CMD_OUTP_DISABLE 0x03
// Set voltage; don't touch switches
#define CMD_SET_VOLTAGE  0x04
// Set pins; don't touch voltage
#define CMD_SET_PINS     0x05
// Open switches; set DAC to 0 V
#define CMD_CLEAR        0x06


typedef struct _dico_packet_t {
	uint8_t  command;
	uint8_t  _reserved;
	uint16_t voltage;
	uint32_t bitmask;
} dico_packet; // 64 bits

typedef struct _dico_response_t {
	uint8_t  status;
	uint8_t  reserved;
	uint16_t payload;
} dico_response; // 32 bits


void receive_packet(struct io_descriptor *const io, dico_packet *p)
{
	io_read(io, (uint8_t *)p, sizeof(dico_packet));
}

void send_response(struct io_descriptor *const io, dico_response *const r)
{
	io_write(io, (uint8_t *)r, sizeof(dico_response));
}

void send_status_with_payload(struct io_descriptor *const io, uint8_t code,
                              uint16_t payload)
{
	dico_response r = { .status = code, .reserved = 0x0, .payload = payload };
	send_response(io, &r);
}

void send_status(struct io_descriptor *const io, uint8_t code)
{
	send_status_with_payload(io, code, 0x0);
}

void set_switch_mask(uint32_t const mask)
{
	uint8_t *bytes = (uint8_t *)&mask;

	gpio_set_pin_level(CS, false);
	SPI_0_write_block((void *)bytes, 4);
	// idle loops needed for the SPI write to finish
	for(volatile int i = 0; i < 2; i++) { }
	gpio_set_pin_level(CS, true);
}

void clear_switch_mask()
{
	set_switch_mask(0x0);
}

int set_dac_output(uint16_t value)
{
	if(value >= 0x400) {
		return EDACRANGE;
	} else {
		dac_sync_write(&DAC_0, 0, &value, 1);
		return EOK;
	}
}

void reset_dac()
{
	set_dac_output(0x0);
}

void process_packet(dico_packet *const p, dico_response *r)
{

	switch(p->command) {
		case CMD_STATUS:
			r->status = EOK;
			r->payload = 0;
			return;
		case CMD_VERSION:
			r->status = EOK;
			r->payload = DICO_VER;
			return;
		case CMD_OUTP_ENABLE:
			if(set_dac_output(p->voltage) != 0) {
				r->status = EDACRANGE;
				return;
			}
			set_switch_mask(p->bitmask);
			r->status = EOK;
			r->payload = 0;
			return;
		case CMD_OUTP_DISABLE:
			clear_switch_mask();
			r->status = EOK;
			r->payload = 0;
			return;
		case CMD_SET_VOLTAGE:
			if(set_dac_output(p->voltage) != 0) {
				r->status = EDACRANGE;
				r->payload = 0;
				return;
			}
			r->status = EOK;
			r->payload = 0;
			return;
        case CMD_SET_PINS:
            set_switch_mask(p->bitmask);
            r->status = EOK;
            r->payload = 0;
            return;
		case CMD_CLEAR:
			set_dac_output(0x0);
			clear_switch_mask();
			r->status = EOK;
			r->payload = 0;
			return;
		default:
			break;
	}

	r->status = EUNKNOWN;
	r->payload = p->command;
}

int main(void)
{
	system_init();

	struct io_descriptor *USART_0_DSCR;
	usart_sync_get_io_descriptor(&USART_0, &USART_0_DSCR);
	usart_sync_enable(&USART_0);

	dac_sync_enable_channel(&DAC_0, 0);

	// Set SWRST to high
	gpio_set_pin_level(SWRST, true);
	clear_switch_mask();
	delay_ms(5);
	reset_dac();

	dico_packet request;
	dico_response response;

	while (1) {
		receive_packet(USART_0_DSCR, &request);
		process_packet(&request, &response);
		send_response(USART_0_DSCR, &response);
	}
}
