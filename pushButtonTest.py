#!/usr/bin/env python
# coding: utf-8

# Test a push button hooked up to a Raspberry Pi's GPIO.
# Button should be normally-open, and connected between the GND and GPIO17 pins.
# If connected correctly, then when the button is pressed, a line is written to stdout, and the Pi's default audio output goes ding-dong.
# Danny Khen (GitHub ID: dannykhen)

import	RPi.GPIO as GPIO
import	time
import	datetime
import	pygame

button_pin = 17

# Init GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
cnt = 0

# Init sound playing
pygame.init()
pygame.mixer.music.load('/home/pi/SmartDoorbell/Ding-dong.wav')

while True:
	input_state = GPIO.input(button_pin)
	if not input_state:
		print datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + ': Button pressed #' + str(cnt)
		cnt += 1
		pygame.mixer.music.play()
		time.sleep(0.2)
