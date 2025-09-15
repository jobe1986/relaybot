# -*- coding: utf-8 -*-

# RelayBot - Simple Relay Service, core/logging.py
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

import logging, logging.handlers, sys, time, re, os

#from core.config import getattrs

#logging.CRITICAL = 50
#logging.ERROR = 40
#logging.WARNING = 30
#logging.INFO = 20
#logging.DEBUG = 10
#logging.NOTSET = 0

__all__ = ['log', 'LOG_CRITICAL', 'LOG_ERROR', 'LOG_WARNING', 'LOG_INFO', 'LOG_DEBUG', 'LOG_PROTOCOL']

LOG_CRITICAL = logging.CRITICAL	# 50
LOG_ERROR = logging.ERROR		# 40
LOG_WARNING = logging.WARNING	# 30
LOG_INFO = logging.INFO			# 20
LOG_DEBUG = logging.DEBUG		# 10
LOG_PROTOCOL = 5				#  5
LOG_NOTSET = logging.NOTSET		#  0

levels = {'DEBUG': LOG_DEBUG, 'PROTOCOL': LOG_PROTOCOL, 'INFO': LOG_INFO, 'WARNING': LOG_WARNING, 'ERROR': LOG_ERROR, 'CRITICAL': LOG_CRITICAL}

root = logging.getLogger(None)
log = logging.getLogger('relaybot')
mylog = log.getChild(__name__)
args = None

_config = None

def leveltoname(level):
	global levels
	for lvl in levels:
		if levels[lvl] == level:
			return lvl
	return 'NOTSET'

class UTCFormatter(logging.Formatter):
	converter = time.gmtime

# Relay Bot Logger Class
class RBLogger(logging.Logger):
	def protocol(self, message, *args, **kws):
		if self.isEnabledFor(LOG_PROTOCOL):
			self._log(LOG_PROTOCOL, message, args, **kws)

	def getChildObj(self, suffix):
		if self.root is not self:
			suffix = '#'.join((self.name, suffix))
		return self.manager.getLogger(suffix)

confs = {'outputs': []}

def loadconfig(conf, args):
	global confs, levels, _config

	outs = conf.findall('output')

	logoutschema = {
		'type': {'type': 'string', 'reqd': True, 'vals': ['stdout', 'stderr', 'file']},
		'level': {'type': 'string', 'def': 'INFO', 'vals': list(levels.keys())},
		'path': {'type': 'string', 'def': None},
		'rollover': {'type': 'string', 'def': None, 'regex': re.compile('^(?:(?:midnight)|(?:[1-9][0-9]*))$')}
	}

	for out in outs:
		attrs = _config.getattrs(out, mylog, logoutschema)

		outconf = {'type': attrs['type'].lower(), 'path': None, 'rollover': None, 'level': LOG_INFO}

		outconf['level'] = levels[attrs['level'].upper()]

		if outconf['type'] == 'file':
			if attrs['path'] is None:
				mylog.error('Missing path attribute in file logging output')
				continue
			outconf['path'] = out.attrib['path']

			if not attrs['rollover'].lower() in ['midnight']:
				outconf['rollover'] = int(attrs['rollover'])
			else:
				outconf['rollover'] = attrs['rollover'].lower()

		oc2 = outconf.copy()
		oc2['level'] = leveltoname(oc2['level'])
		mylog.debug('Found logging output: ' + str(oc2))
		confs['outputs'].append(outconf)

	return True

def applyconfig(loop, args):
	global confs, root, defloghandler, deflogformatter, cliargs

	removedef = False

	for out in confs['outputs']:
		if out['type'] == 'stdout':
			if not args.nofork:
				continue
			loghandler = logging.StreamHandler(sys.stdout)
		elif out['type'] == 'stderr':
			if not args.nofork:
				continue
			loghandler = logging.StreamHandler(sys.stderr)
		elif out['type'] == 'file':
			dir = os.path.dirname(out['path'])
			if not os.path.exists(dir):
				try:
					os.makedirs(dir, 0o700)
				except Exception as ex:
					log.error('Unable to create log directory "' + dir + '": ' + str(ex))
			if out['rollover'] == None:
				loghandler = logging.FileHandler(out['path'])
			elif out['rollover'] == 'midnight':
				loghandler = logging.handlers.TimedRotatingFileHandler(out['path'], when='midnight', interval=1, backupCount=10, utc=True)
			else:
				loghandler = logging.handlers.RotatingFileHandler(out['path'], maxBytes=out['rollover'], backupCount=10)
		else:
			continue

		logformatter = UTCFormatter('[%(asctime)s] [%(name)s/%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
		loghandler.setFormatter(logformatter)
		loghandler.setLevel(out['level'])
		root.addHandler(loghandler)
		removedef = True

	if removedef:
		root.removeHandler(defloghandler)
		mylog.debug('Default logging handler no longer needed')

def init_logging(args, configns):
	global rblog, levels, root, defloghandler, deflogformatter, cliargs, _config
	_config = configns

	cliargs = args

	logging.setLoggerClass(RBLogger)

	for name in levels:
		logging.addLevelName(levels[name], name)

	defloghandler = logging.StreamHandler(sys.stderr)
	deflogformatter = UTCFormatter('[%(asctime)s] [%(name)s/%(levelname)s] %(message)s', '%Y-%m-%d %H:%M:%S')
	defloghandler.setFormatter(deflogformatter)

	if args.debug:
		defloghandler.setLevel(LOG_DEBUG)
	else:
		defloghandler.setLevel(LOG_INFO)

	root.setLevel(LOG_NOTSET)
	log.setLevel(LOG_NOTSET)
	root.addHandler(defloghandler)

	if args.debug:
		log.debug('Debug logging enabled')

def getlog(name):
	return log.getChild(name)
