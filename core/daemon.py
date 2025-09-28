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

import os, sys, atexit, resource

log = _logging.log.getChild(__name__)

def daemonize(args):
	global log

	pid = None
	try:
		with open(args.pidfile, 'r') as pf:
			pid = int(pf.read().strip())
	except (FileNotFoundError, ValueError):
		pass
	if pid and os.path.exists(f'/proc/{pid}'):
		log.error('PID file exists and process is running. Is RelayBot already running?')
		sys.exit(1)

	if not args.nofork:
		log.debug('Forking into the background')

		log.debug('Attempting first fork...')
		try:
			pid = os.fork()
			if pid > 0:
				sys.exit(0)
		except Exception as e:
			log.error('First fork failed: ' + str(e))
			sys.exit(1)

		log.debug('Successfully forked once')

		os.setsid()

		log.debug('Closing inherited file descriptors (FDs)')
		try:
			# Get the maximum file descriptor limit
			maxfd = resource.getrlimit(resource.RLIMIT_NOFILE)[1]
			if maxfd == resource.RLIM_INFINITY:
				maxfd = 1024 
			for fd in range(3, maxfd):
				try:
					os.close(fd)
				except OSError:
					pass
		except Exception as e:
			log.warning(f'Could not safely close FDs: {e}')

		log.debug('Attempting second fork...')
		try:
			pid = os.fork()
			if pid > 0:
				sys.exit(0)
		except Exception as e:
			log.error('Second fork failed: ' + str(e))
			sys.exit(1)

		log.debug('Successfully forked into the background')

		sys.stdout.flush()
		sys.stderr.flush()
		with open(os.devnull, 'r') as si:
			os.dup2(si.fileno(), sys.stdin.fileno())
		with open(os.devnull, 'a+') as so:
			os.dup2(so.fileno(), sys.stdout.fileno())
		with open(os.devnull, 'a+') as se:
			os.dup2(se.fileno(), sys.stderr.fileno())
	else:
		log.debug('Running in the foreground')

	log.debug('Creating PID file ' + os.path.abspath(args.pidfile))
	atexit.register(delpidfile, args.pidfile)
	pid = str(os.getpid())
	try:
		with open(args.pidfile, 'w') as pf:
			pf.write(str(pid) + '\n')
	except IOError as e:
		log.error('Could not create PID file: ' + str(e))
		sys.exit(1)

	return

def delpidfile(file):
	try:
		os.remove(file)
	except:
		log.error('Could not delete PID file')
