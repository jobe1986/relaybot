# -*- coding: utf-8 -*-

# RelayBot - Simple Relay Service, modules/minecraft/__init__.py
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

log = _logging.log.getChild(__name__)

configs = {}

def loadconfig(config, module):
	global configs
	global log

	for mccfg in config:
		if not 'name' in mccfg.attrib:
			log.warning('Minecraft client config missing name attribute')
			continue
		if mccfg.attrib['name'] in configs:
			log.warning('Duplicate Minecraft client config name: ' + mccfg.attrib['name'])
			continue

		name = mccfg.attrib['name']
		conf = {'name': name, 'rcon': None, 'udp': None, 'logreader': None}

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

		logreader = mccfg.findall('./logreader')
		if logreader:
			logreader = logreader[0].attrib

			if not 'file' in logreader:
				log.warning('Minecraft client ' + name + ' Log Reader configuration missing file path')
				continue

			conf['logreader'] = logreader

		if not conf['rcon'] and not conf['udp'] and not conf['logreader']:
			log.warning('Minecraft client ' + name + ' requires at least an rcon, udp or logreader configuration')
			continue
		if conf['udp'] and conf['logreader']:
			conf['udp'] = None
			log.warning('Minecraft client ' + name + ' has both a udp and logreader config, using logreader')

		configs[name] = conf
		log.debug('Loaded config: ' + str(conf))
	return

def applyconfig(loop, module):
	global configs
	global log

	import modules.minecraft.logprotocol as _logprotocol
	import modules.minecraft.udpprotocol as _udpprotocol
	import modules.minecraft.rconprotocol as _rconprotocol

	for name in configs:
		conf = configs[name]
		log.info('Creating Minecraft client ' + name)
		if conf['logreader'] is not None:
			_logprotocol.createclient(loop, conf, module)
		if conf['udp'] is not None:
			_udpprotocol.createclient(loop, conf, module)
		if conf['rcon'] is not None:
			_rconprotocol.createclient(loop, conf, module)
	return

def shutdown(loop):
	global log

	import modules.minecraft.logprotocol as _logprotocol
	import modules.minecraft.udpprotocol as _udpprotocol
	import modules.minecraft.rconprotocol as _rconprotocol

	for cli in _logprotocol.clients:
		_logprotocol.clients[cli].shutdown(loop)

	for cli in _udpprotocol.clients:
		_udpprotocol.clients[cli].shutdown(loop)

	for cli in _rconprotocol.clients:
		_rconprotocol.clients[cli].shutdown(loop)

def handle_event(loop, module, sender, protocol, event, data):
	global log

	import modules.minecraft.logprotocol as _logprotocol
	import modules.minecraft.udpprotocol as _udpprotocol
	import modules.minecraft.rconprotocol as _rconprotocol

	for cli in _logprotocol.clients:
		if module.name == 'minecraft' and protocol == 'udp' and sender == cli:
			continue
		log.debug('Sending event "' + event + '" to client "' + cli + '" logreader')
		_logprotocol.clients[cli].handle_event(loop, module, sender, protocol, event, data)

	for cli in _udpprotocol.clients:
		if module.name == 'minecraft' and protocol == 'udp' and sender == cli:
			continue
		log.debug('Sending event "' + event + '" to client "' + cli + '" udp')
		_udpprotocol.clients[cli].handle_event(loop, module, sender, protocol, event, data)

	for cli in _rconprotocol.clients:
		if module.name == 'minecraft' and protocol == 'rcon' and sender == cli:
			continue
		log.debug('Sending event "' + event + '" to client "' + cli + '" rcon')
		_rconprotocol.clients[cli].handle_event(loop, module, sender, protocol, event, data)

def handle_event_target(loop, target, module, sender, protocol, event, data):
	global log

	import modules.minecraft.logprotocol as _logprotocol
	import modules.minecraft.udpprotocol as _udpprotocol
	import modules.minecraft.rconprotocol as _rconprotocol

	if 'module' in target and target['module'] != 'minecraft':
		return

	for cli in _logprotocol.clients:
		if module.name == 'minecraft' and protocol == 'udp' and sender == cli:
			continue
		if 'name' in target and target['name'] != cli:
			continue
		log.debug('Sending event "' + event + '" to client "' + cli + '" logreader')
		_logprotocol.clients[cli].handle_event(loop, module, sender, protocol, event, data)

	for cli in _udpprotocol.clients:
		if module.name == 'minecraft' and protocol == 'udp' and sender == cli:
			continue
		if 'name' in target and target['name'] != cli:
			continue
		log.debug('Sending event "' + event + '" to client "' + cli + '" udp')
		_udpprotocol.clients[cli].handle_event(loop, module, sender, protocol, event, data)

	for cli in _rconprotocol.clients:
		if module.name == 'minecraft' and protocol == 'rcon' and sender == cli:
			continue
		if 'name' in target and target['name'] != cli:
			continue
		log.debug('Sending event "' + event + '" to client "' + cli + '" rcon')
		_rconprotocol.clients[cli].handle_event(loop, module, sender, protocol, event, data)
