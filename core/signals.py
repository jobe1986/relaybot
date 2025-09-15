# -*- coding: utf-8 -*-

# RelayBot - Simple Relay Service, core/signals.py
#
# Copyright (C) 2023 Matthew Beeching
#
# This file is part of RelayBot.
#
# RelayBot is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# RelayBot is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with RelayBot.  If not, see <http://www.gnu.org/licenses/>.

import core.logging as _logging
import core.modules as _modules

import os, signal

log = _logging.log.getChild(__name__)

def handle_sigint(loop):
	log.info('Shutting down: Received signal SIGINT')
	_modules.shutdown(loop)
	loop.call_later(2, loop.stop)

def handle_sighup(loop):
	log.info('Received signal SIGHUP')

def handle_sigusr1(loop):
	log.info('Received signal SIGUSR1')

def handle_sigusr2(loop):
	log.info('Received signal SIGUSR2')

def handle_sigterm(loop):
	log.info('Shutting down: Received signal SIGTERM')
	_modules.shutdown(loop)
	loop.call_later(2, loop.stop)

def init_signals(loop):
	if not os.name == 'nt':
		log.debug('Adding signal handlers')
		loop.add_signal_handler(signal.SIGINT, handle_sigint, loop)
		loop.add_signal_handler(signal.SIGHUP, handle_sighup, loop)
		loop.add_signal_handler(signal.SIGUSR1, handle_sigusr1, loop)
		loop.add_signal_handler(signal.SIGUSR2, handle_sigusr2, loop)
		loop.add_signal_handler(signal.SIGTERM, handle_sigterm, loop)
