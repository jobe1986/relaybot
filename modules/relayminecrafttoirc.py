# -*- coding: utf-8 -*-

# RelayBot - Simple VNC Relay Service, modules/relayminecrafttoirc.py
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
import core.modules as _modules
import json, re

log = _logging.log.getChild(__name__)

configs = {}

def loadconfig(config, module):
	global configs
	global log

	for relaycfg in config:
		if not 'name' in relaycfg.attrib:
			log.warning('Relay (Minecraft To IRC) config missing name attribute')
			continue
		if relaycfg.attrib['name'] in configs:
			log.warning('Duplicate Relay (Minecraft To IRC) config name: ' + relaycfg.attrib['name'])
			continue

		name = relaycfg.attrib['name']
		conf = {'name': name, 'irc': '', 'minecraft': '', 'channels': []}

		irc = relaycfg.findall('./irc')
		if not irc:
			log.warning('Relay (Minecraft To IRC) ' + name + ' missing IRC configuration')
			continue
		if not 'name' in irc[0].attrib:
			log.warning('Relay (Minecraft To IRC) ' + name + ' IRC configuration missing name attribute')
			continue

		conf['irc'] = irc[0].attrib['name']

		chans = irc[0].findall('./channel')
		if not chans:
			log.warning('Relay (Minecraft To IRC) ' + name + ' IRC configuration missing channels')
			continue
		for chan in chans:
			if not 'name' in chan.attrib:
				log.warning('Relay (Minecraft To IRC) ' + name + ' IRC configuration missing channel name attribute')
				continue
			conf['channels'].append(chan.attrib['name'])

		mc = relaycfg.findall('./minecraft')
		if not mc:
			log.warning('Relay (Minecraft To IRC) ' + name + ' missing Minecraft configuration')
			continue
		if not 'name' in mc[0].attrib:
			log.warning('Relay (Minecraft To IRC) ' + name + ' Minecraft configuration missing name attribute')
			continue

		conf['minecraft'] = mc[0].attrib['name']

		configs[name] = conf
		log.debug('Loaded config: ' + str(conf))
	return

def applyconfig(loop, module):
	global configs
	global log

	for name in configs:
		conf = configs[name]
		log.info('Creating Relay (Minecraft To IRC) ' + name)
	return

def shutdown(loop):
	return

def handle_event(loop, module, sender, protocol, event, data):
	global log
	global configs
	
	events = [
		'PLAYER_CONNECT',
		'PLAYER_DISCONNECT',
		'MESSAGE',
		'ACTION',
		'ADVANCEMENT',
		'DEATH',
		'WHITELIST_FAIL'
		]

	if module.name != 'minecraft':
		return

	if not event in events:
		return

	log.debug('Relaying event ' + event + ' to irc: ' + str(data))

	for name in configs:
		conf = configs[name]

		if conf['minecraft'] != sender:
			continue

		text = ''
		target = {'module': 'irc', 'name': conf['irc']}

		if event == 'PLAYER_CONNECT':
			text = data['name'] + ' ' + data['message']
		elif event == 'PLAYER_DISCONNECT':
			text = data['name'] + ' ' + data['message']
		elif event == 'MESSAGE':
			text = data['raw']
		elif event == 'ACTION':
			text = data['raw']
		elif event == 'ADVANCEMENT':
			text = data['name'] + ' ' + data['message']
		elif event == 'DEATH':
			text = data['message']
		elif event == 'WHITELIST_FAIL':
			text = '*** Connection from ' + data['ip'] + ' rejected (not whitelisted: ' + data['name'] + ')'

		for chan in conf['channels']:
			evt = {'command': 'PRIVMSG ' + chan + ' :' + text, 'callback': None}
			_modules.send_event_target(loop, target, module, sender, 'relay', 'IRC_SENDCMD', evt)
