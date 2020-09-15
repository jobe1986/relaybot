# -*- coding: utf-8 -*-

# RelayBot - Simple VNC Relay Service, irc.py
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

import core.logging as _logging

log = _logging.log.getChild(__name__)

configs = {}

def loadconfig(config):
	global configs

	for irccfg in config:
		if not 'name' in irccfg.attrib:
			log.warning('IRC client config missing name attribute')
			continue
		if irccfg.attrib['name'] in configs:
			log.warning('Duplicate IRC client config name: ' + irccfg.attrib['name'])
			continue

		name = irccfg.attrib['name']
		conf = {'server': {}, 'user': {}, 'channels': {}}

		serv = irccfg.findall('./server')
		if not serv:
			log.warning('IRC client ' + name + ' missing server configuration')
			continue
		serv = serv[0].attrib

		if not 'host' in serv:
			log.warning('IRC client ' + name + ' server missing host attribute')
			continue
		if not 'port' in serv:
			log.warning('IRC client ' + name + ' server missing port attribute')
			continue

		conf['server'] = serv
		if not 'tls' in conf['server']:
			conf['server']['tls'] = False
		else:
			if conf['server']['tls'].lower() in ['true', 'yes', 'y']:
				conf['server']['tls'] = True
			elif int(conf['server']['tls']) != 0:
				conf['server']['tls'] = True
			else:
				conf['server']['tls'] = False
		if not 'password' in conf['server']:
			conf['server']['password'] = None
		if conf['server']['password'] == '':
			conf['server']['password'] = None

		user = irccfg.findall('./user')
		if not user:
			log.warning('IRC client ' + name + ' missing user configuration')
			continue
		user = user[0].attrib

		if not 'nick' in user:
			log.warning('IRC client ' + name + ' user missing nick attribute')
			continue
		if not 'user' in user:
			log.warning('IRC client ' + name + ' user missing user attribute')
			continue
		if not 'gecos' in user:
			log.warning('IRC client ' + name + ' user missing gecos attribute')
			continue
		conf['user'] = user

		chans = irccfg.findall('./channel')
		if not chans:
			log.warning('IRC client ' + name + ' missing channel configuration')
			continue

		for chan in chans:
			continue

		print(str(conf))
	return

def applyconfig(loop):
	return
