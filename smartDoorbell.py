#!/usr/bin/env python
# coding: utf-8

#
# Based on https://wiki.linphone.org/wiki/index.php/Raspberrypi:start
#
# Smart doorbell + security camera.
# 1. Smart doorbell: doorbell button calls the configured Linphone account.
# 2. Security camera: the configured Linphone account can also call into the device running this script.
#
# See main() at the bottom of the file for customization.
#
# Danny Khen (GitHub ID: dannykhen)
#
 
import sys
import linphone
import logging
import signal
import RPi.GPIO as GPIO
import pygame
import time
 
class SmartDoorbell:
  def __init__(self, main_log_level=logging.ERROR, module_log_level=logging.ERROR, button_pin=-1, ding_dong_file=None, username='', password='', trusted=[], camera='', sound_capture='', sound_playback=''):

    self.quit = False
    self.trusted = trusted
    self.ding_dong_file = ding_dong_file 

    logging.basicConfig(format='%(levelname)s-%(name)s: %(asctime)s: %(message)s', level=module_log_level)
    self.logger = logging.getLogger('SmartDoorbell')
    self.logger.setLevel(main_log_level)

    signal.signal(signal.SIGINT, self.signal_handler)

    self.logger.debug('main_log_level	= %d', main_log_level)
    self.logger.debug('module_log_level	= %d', module_log_level)
    self.logger.debug('button_pin	= %d', button_pin)
    self.logger.debug('ding_dong_file	= %s', ding_dong_file)
    self.logger.debug('username	= %s', username)
    self.logger.debug('password	= %s', password)
    self.logger.debug('trusted	= %s', trusted)
    self.logger.debug('camera	= %s', camera)
    self.logger.debug('sound_capture	= %s', sound_capture)
    self.logger.debug('sound_playback	= %s', sound_playback)

    # Configure the GPIO h/w for push button detection (if button is connected - value >=0)
    self.button_pin = button_pin
    if self.button_pin >= 0:
      GPIO.setmode(GPIO.BCM)
      GPIO.setup(self.button_pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
 
    # Configure the linphone core
    linphone.set_log_handler(self.log_handler)
    callbacks = {
      'call_state_changed': self.call_state_changed,
    }
    self.core = linphone.Core.new(callbacks, None, None)
    self.core.max_calls = 1
    self.core.echo_cancellation_enabled = False
    self.core.video_capture_enabled = True
    self.core.video_display_enabled = False
    if len(camera):
      self.core.video_device = camera
    if len(sound_capture):
      self.core.capture_device = sound_capture
    if len(sound_playback):
      self.core.playback_device = sound_playback
 
    # Only enable PCMU and PCMA audio codecs
    for codec in self.core.audio_codecs:
      if codec.mime_type == "PCMA" or codec.mime_type == "PCMU":
        self.core.enable_payload_type(codec, True)
      else:
        self.core.enable_payload_type(codec, False)
 
    # Only enable VP8 video codec
    for codec in self.core.video_codecs:
      if codec.mime_type == "VP8":
        self.core.enable_payload_type(codec, True)
      else:
        self.core.enable_payload_type(codec, False)
 
    # Configure the SIP account
    proxy_cfg = self.core.create_proxy_config()
    proxy_cfg.identity_address = self.core.create_address('sip:{username}@sip.linphone.org'.format(username=username))
    proxy_cfg.server_addr = 'sip:sip.linphone.org;transport=tls'
    proxy_cfg.register_enabled = True
    self.core.add_proxy_config(proxy_cfg)
    auth_info = self.core.create_auth_info(username, None, password, None, None, 'sip.linphone.org')
    self.core.add_auth_info(auth_info)
 
  def signal_handler(self, signal, frame):
    self.logger.debug('Interrupted, signal = %d', signal)
    self.core.terminate_all_calls()
    self.quit = True
 
  def log_handler(self, level, msg):
    method = getattr(logging, level)
    method(msg)
 
  def call_state_changed(self, core, call, state, message):
    if state == linphone.CallState.IncomingReceived:
      if call.remote_address.as_string_uri_only() in self.trusted:
        self.logger.info('Trusted user %s is calling in. Accepting call.', call.remote_address.as_string_uri_only())
        params = core.create_call_params(call)
        core.accept_call_with_params(call, params)
      else:
        self.logger.warning('Untrusted user %s is calling in. Declining and sending message to %s.',
				call.remote_address.as_string_uri_only(),
				self.trusted[0])
        core.decline_call(call, linphone.Reason.Declined)
        chat_room = core.get_chat_room_from_uri(self.trusted[0])
        msg = chat_room.create_message('Untrusted user ' + call.remote_address_as_string + ' tried to call the doorbell.')
        chat_room.send_chat_message(msg)

    else:
      # Log some call states.
      action = None

      if state == linphone.CallState.End:
        action = "ended"
      elif state == linphone.CallState.Error:
        action = "encountered an error"
      elif state == linphone.CallState.Connected:
        action = "connected"

      if action != None:
         self.logger.info('Call %s.', action)
 
  def run(self):
    # TBD: calls_nb
    while not self.quit:
      self.core.iterate()

      # If not in call, and a doorbell button is configured, get button state
      if not self.core.in_call() and self.button_pin >= 0:
        input_state = GPIO.input(self.button_pin)

        # Check if button pressed
        if not input_state:
          self.logger.info('Doorbell button pressed; calling %s', self.trusted[0])

          # Start a call to owner (first address in trusted list)
          self.core.invite(self.trusted[0])

          # Ring the bell
          if self.ding_dong_file != None:
            pygame.mixer.init()
            pygame.mixer.music.load(self.ding_dong_file)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy():
              time.sleep(0.01)
            pygame.mixer.quit()

      time.sleep(0.03)

    self.logger.info('Terminating.')
 
def main():
  # SmartDoorbell object arguments:
  #   main_log_level: log level for the program; logging.{ERROR,WARNING,INFO,DEBUG} (default=INFO)
  #   module_log_level: log level for called modules; logging.{ERROR,WARNING,INFO,DEBUG} (default=ERROR)
  #       Use logging.INFO the first time to see the list of available audio/video devices.
  #   button_pin: GPIO pin the doorbell push button is connected to (do not pass any value if button is not connected)
  #   ding_dong_file: sound effect for ringing the doorbell.
  #       A sample file comes with the GitHub repository; change the path to where you've put it.
  #   username: your smart doorbell device's linphone username
  #   password: your smart doorbell device's linphone password
  #   trusted: trusted account list
  #       First item: the Linphone SIP address that the device should call to when the doorbell button is pushed
  #       More items: any address allowed to call into the device to access the security camera, in addition to the above
  #   camera, sound_capture, sound_playback: your security camera device's video, sound input and sound output devices (use log_level=logging.INFO to see a list of devices during program initialization)
  cam = SmartDoorbell(
	main_log_level=logging.INFO,
	module_log_level=logging.ERROR,
	button_pin=17,
	ding_dong_file='/home/pi/SmartDoorbell/Ding-dong.wav',
	username='dannykhen-rpi',
	password='8ArthurDent17',
	trusted=['sip:dannykhen@sip.linphone.org', 'sip:dankhen@sip.linphone.org'],
	camera='V4L2: /dev/video0',
	sound_capture='ALSA: Microsoft® LifeCam Cinema(TM)',
	sound_playback='ALSA: USB Audio Device')
  cam.run()
 
main()
