# -*- coding: utf-8 -*-

# RelayBot - Simple VNC Relay Service, modules/irc/__init__.py
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
		conf = {'name': name, 'server': {}, 'user': {}, 'channels': {}}

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
			chana = chan.attrib
			if not 'name' in chana:
				log.warning('Channel for IRC client ' + name + ' missing name attribute')
				continue
			cname = chana['name']
			if cname.lower() in conf['channels']:
				log.warning('Channel ' + cname + ' for IRC client ' + name + ' already exists')
				continue
			if 'key' in chana:
				if ' ' in chana['key']:
					log.warning('Channel ' + cname + ' for IRC client ' + name + ' cannot contain a space, skipping channel')
					continue
			conf['channels'][cname.lower()] = chana

		configs[name] = conf
		log.debug('Loaded config: ' + str(conf))
	return

def applyconfig(loop):
	global configs

	import modules.irc.protocol as _protocol

	for name in configs:
		conf = configs[name]
		log.info('Creating IRC client ' + name)

		_protocol.createclient(loop, conf)
	return

def shutdown(loop):
	import modules.irc.protocol as _protocol
	
	for cli in _protocol.clients:
		_protocol.clients[cli].shutdown(loop)
