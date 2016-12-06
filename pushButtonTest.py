#!/usr/bin/env python
# coding: utf-8

import	RPi.GPIO as GPIO
import	time
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
		print 'Button pressed: ', cnt
		cnt += 1
		pygame.mixer.music.play()
		time.sleep(0.2)
