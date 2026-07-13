#!/usr/bin/python3
# -*- coding: utf-8 -*-

# RelayBot - Simple Relay Service, run.py
#
# Copyright (C) 2026 Matthew Beeching
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
import core.config as _config
import core.daemon as _daemon
import core.signals as _signals

from core.loop import init_loop, shutdown_loop

import argparse, asyncio, os, sys

log = _logging.log.getChild('main')

def parse_args():
	parser = argparse.ArgumentParser(add_help=False)
	parser.add_argument('-h', '-?', '--help', help='Show this help message and exit', action='help')
	parser.add_argument('-c', '--config', help='Specify the path to config.xml', action='store', default=_config.configpath, dest='config')
	parser.add_argument('-d', '--debug', help='Enable debug output to STDOUT', action='store_true', dest='debug')
	parser.add_argument('-f', '--foreground', help='Run in the foreground', action='store_true', dest='nofork')
	parser.add_argument('-n', '--nofork', help='Run in the foreground', action='store_true', dest='nofork')
	parser.add_argument('-p', '--pidfile', help='Path to process id (pid) file', action='store', default='relaybot.pid', dest='pidfile')
	parser.add_argument('-a', '--asynciodebug', help=argparse.SUPPRESS, action='store_true', dest='asynciodebug')

	args = parser.parse_args()

	if os.name == 'nt':
		args.nofork = True

	return args

args = parse_args()

_config.checkoverrides(args)
_logging.init_logging(args, _config)

if os.name == 'nt':
	log.debug('Running on Windows, -n/-f implied')
log.debug('Command line options: ' + str(vars(args)))

_daemon.daemonize(args)

# Create event loop
loop = init_loop(args)

_signals.init_signals(loop)

# Load the config, this will start adding tasks etc... to the loop ready to be run by loop.run_forever()
_config.load(loop, args)

log.info('Starting event loop')

try:
	loop.run_forever()
except Exception as e:
	log.error('Loop error: ' + str(e))
finally:
	log.info('Finalizing tasks')

	loop.run_until_complete(shutdown_loop(loop))

	pending_tasks = asyncio.all_tasks(loop=loop)
	if pending_tasks:
		log.debug('Cancelling ' + str(len(pending_tasks)) + ' tasks')
		for t in pending_tasks:
			log.debug('Cancelling task ' + str(t))
			t.cancel()
		loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
	loop.close()
