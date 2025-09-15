# -*- coding: utf-8 -*-

# RelayBot - Simple Relay Service, core/daemon.py
#
# Copyright (C) 2025 Matthew Beeching
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

import os, sys, atexit

log = _logging.log.getChild(__name__)

def daemonize(args):
	global log
	try:
		pf = open(args.pidfile,'r')
		pid = int(pf.read().strip())
		pf.close()
	except:
		pid = None

	if pid and pid != os.getpid():
		log.error('PID file already exists, Is RelayBot already running?')
		sys.exit(1)

	if not args.nofork:
		log.debug('Forking into the background')

		log.debug('Attempting first fork...')
		try:
			pid = os.fork()
			if pid > 0:
				sys.exit(0)
		except Exception as e:
			log.error('First fork failed: ' + str(estrerror))
			sys.exit(1)

		log.debug('Successfully forked once')

		os.setsid()
		
		log.debug('Attempting second fork...')
		try:
			pid = os.fork()
			if pid > 0:
				sys.exit(0)
		except Exception as e:
			log.error('Second fork failed: ' + str(estrerror))
			sys.exit(1)

		log.debug('Successfully forked into the background')

		sys.stdout.flush()
		sys.stderr.flush()
		si = open(os.devnull, 'r')
		so = open(os.devnull, 'a+')
		se = open(os.devnull, 'a+')
		os.dup2(si.fileno(), sys.stdin.fileno())
		os.dup2(so.fileno(), sys.stdout.fileno())
		os.dup2(se.fileno(), sys.stderr.fileno())
	else:
		log.debug('Running in the foreground')

	log.debug('Creating PID file ' + os.path.abspath(args.pidfile))
	atexit.register(delpidfile, args.pidfile)
	pid = str(os.getpid())
	try:
		pf = open(args.pidfile, 'w+')
		pf.write('%s\n' % (pid))
		pf.close()
	except:
		log.error('Could not create PID file')
		sys.exit(0)

	return

def delpidfile(file):
	try:
		os.remove(file)
	except:
		log.error('Could not delete PID file')
