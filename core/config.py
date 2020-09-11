# -*- coding: utf-8 -*-

# RelayBot - Simple VNC Relay Service, core/config.py
#
# Copyright (C) 2016 Matthew Beeching
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

from xml.etree.ElementTree import ElementTree

import core.logging as _logging
import core.modules as _modules

import os

log = _logging.log.getChild(__name__)

config = None
configpath = 'config/config.xml'

TYPE_STRING = 'string'
TYPE_INT = 'int'
TYPE_BOOL = 'bool'
TYPE_FLOAT = 'float'

def load(loop, args):
	global config, configpath
	try:
		log.info('Loading configuration from ' + configpath)

		log.debug('Loading logging configuration')
		logcfg = config.find('logging')
		if _logging.loadconfig(logcfg, args):
			_logging.applyconfig(loop, args)
		else:
			log.error('Unable to load logging configuration')
			loop.stop()
			return

		log.debug('Loading modules')
		if _modules.loadconfig(config):
			_modules.applyconfig(loop)
		else:
			log.error('Unable to load modules')
			loop.stop()
			return

		log.info('Configuration successfully loaded')
		return
	except Exception as e:
		log.error('Error parsing configuration: ' + str(e))
		loop.stop()
		return

def checkoverrides(args):
	global config, configpath
	try:
		configpath = os.path.abspath(args.config)
		tree = ElementTree()
		config = tree.parse(configpath)

		dbgconf = config.findall('debug')
		if len(dbgconf) > 0:
			args.debug = True

		nfconf = config.findall('nofork')
		if len(nfconf) > 0:
			args.nofork = True
	except Exception as e:
		log.error('Error checking configuration for debug mode: ' + str(e))
		
def getattrs(node, log, attrs={}):
	ret = {}

	for key in node.attrib:
		val = node.attrib[key]
		type = TYPE_STRING
		err = None

		if key in attrs:
			if 'type' in attrs[key]:
				type = attrs[key]['type']
			try:
				if type == TYPE_INT:
					val = int(val)
				elif type == TYPE_FLOAT:
					val = float(val)
				elif type == TYPE_BOOL:
					if val.lower() in ['false', 'no', '0']:
						val = False
					else:
						val = True
			except Exception as e:
				if 'def' in attrs[key]:
					log.warning('Error converting attribute ' + key + ' to type ' + type + ', using default value instead')
					val = attrs[key]['def']
				else:
					log.error('Error converting attribute ' + key + ' to type ' + type + ': ' + str(e))
					continue

		ret[key] = val

	req = []
	for key in attrs:
		if not key in ret:
			if 'def' in attrs[key]:
				ret[key] = attrs[key]['def']
			elif 'reqd' in attrs[key]:
				if attrs[key]['reqd']:
					req.append(key)

	if len(req) > 0:
		log.error('Missing attribute(s) for ' + node.tag + ' configuration: ' + ', '.join(req))
		return None

	return ret
