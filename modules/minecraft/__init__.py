# -*- coding: utf-8 -*-

# RelayBot - Simple VNC Relay Service, modules/minecraft/minecraft.py
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

	for mccfg in config:
		if not 'name' in mccfg.attrib:
			log.warning('Minecraft client config missing name attribute')
			continue
		if mccfg.attrib['name'] in configs:
			log.warning('Duplicate Minecraft client config name: ' + mccfg.attrib['name'])
			continue

		name = mccfg.attrib['name']
		conf = {'name': name, 'rcon': None, 'udp': None}

		rcon = mccfg.findall('./rcon')
		if rcon:
			rcon = rcon[0].attrib

			if not 'host' in rcon:
				log.warning('Minecraft client ' + name + ' rcon configuration missing host attribute')
				continue
			if not 'port' in rcon:
				log.warning('Minecraft client ' + name + ' rcon configuration missing port attribute')
				continue
			if not 'password' in rcon:
				log.warning('Minecraft client ' + name + ' rcon configuration missing password attribute')
				continue

			conf['rcon'] = rcon

		udp = mccfg.findall('./udp')
		if udp:
			udp = udp[0].attrib

			if not 'host' in udp:
				udp['host'] = '0.0.0.0'
			if not 'port' in udp:
				log.warning('Minecraft client ' + name + ' UDP configuration missing port attribute')
				continue

			conf['udp'] = udp

		if not conf['rcon'] and not conf['udp']:
			log.warning('Minecraft client ' + name + ' requires at least an rcon or udp configuration')
			continue

		configs[name] = conf
		log.debug('Loaded config: ' + str(conf))
	return

def applyconfig(loop):
	global configs

	import modules.minecraft.udpprotocol as _udpprotocol

	for name in configs:
		conf = configs[name]
		log.info('Creating Minecraft client ' + name)

		if conf['udp'] is not None:
			_udpprotocol.createclient(loop, conf)
	return

def shutdown(loop):
	import modules.minecraft.udpprotocol as _udpprotocol

	for cli in _udpprotocol.clients:
		_udpprotocol.clients[cli].shutdown(loop)
