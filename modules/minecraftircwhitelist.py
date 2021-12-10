# -*- coding: utf-8 -*-

# RelayBot - Simple VNC Relay Service, modules/minecraftircwhitelist.py
#
# Copyright (C) 2021 Matthew Beeching
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
import functools, json, re

log = _logging.log.getChild(__name__)

configs = {}

moduleobj = None

def loadconfig(config, module):
	global configs
	global log
	global moduleobj

	moduleobj = module

	for relaycfg in config:
		if not 'name' in relaycfg.attrib:
			log.warning('Minecraft IRC Whitelist config missing name attribute')
			continue
		if relaycfg.attrib['name'] in configs:
			log.warning('Duplicate Minecraft IRC Whitelist config name: ' + relaycfg.attrib['name'])
			continue

		name = relaycfg.attrib['name']
		conf = {'name': name, 'irc': '', 'minecraft': '', 'channels': []}

		irc = relaycfg.findall('./irc')
		if not irc:
			log.warning('Minecraft IRC Whitelist ' + name + ' missing IRC configuration')
			continue
		if not 'name' in irc[0].attrib:
			log.warning('Minecraft IRC Whitelist ' + name + ' IRC configuration missing name attribute')
			continue

		ircchans = irc[0].findall('./channel')
		if ircchans:
			for chan in ircchans:
				if not 'name' in chan.attrib:
					log.warning('Minecraft IRC Whitelist ' + name + ' IRC channel configuration missing name attribute')
					continue
				conf['channels'].append(chan.attrib['name'].lower())

		conf['irc'] = irc[0].attrib['name']

		mc = relaycfg.findall('./minecraft')
		if not mc:
			log.warning('Minecraft IRC Whitelist ' + name + ' missing Minecraft configuration')
			continue
		if not 'name' in mc[0].attrib:
			log.warning('Minecraft IRC Whitelist ' + name + ' Minecraft configuration missing name attribute')
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
		log.info('Creating Minecraft IRC Whitelist ' + name)
	return

def shutdown(loop):
	return

def handle_event(loop, module, sender, protocol, event, data):
	global log
	global configs
	global moduleobj
	
	events = ['CHANNEL_MESSAGE']

	if module.name != 'irc':
		return

	if not event in events:
		return

	log.debug('Received event ' + event + ' from irc: ' + str(data))

	for conf in configs:
		if configs[conf]['irc'] != sender:
			continue

		if len(configs[conf]['channels']) > 0:
			if not data['target'].lower() in configs[conf]['channels']:
				break

		parts = data['message'].split(' ')
		if parts[0] != '?whitelist':
			break
		if not 'o' in data['source']['modes']:
			break

		target = {'module': module.name, 'name': sender}

		if len(parts) < 2:
			evt = {'command': 'PRIVMSG ' + data['target'] + ' :Whitelist: Missing sub command (add or remove)', 'callback': None}
			_modules.send_event_target(loop, target, moduleobj, conf, 'whitelist', 'IRC_SENDCMD', evt)
			break
		if not parts[1].lower() in ['add', 'remove']:
			evt = {'command': 'PRIVMSG ' + data['target'] + ' :Whitelist: Invalid sub command, must be add or remove', 'callback': None}
			_modules.send_event_target(loop, target, moduleobj, conf, 'whitelist', 'IRC_SENDCMD', evt)
			break
		if len(parts) < 3:
			evt = {'command': 'PRIVMSG ' + data['target'] + ' :Whitelist: Missing sub command parameter', 'callback': None}
			_modules.send_event_target(loop, target, moduleobj, conf, 'whitelist', 'IRC_SENDCMD', evt)
			break

		cbsourcemod = _modules.getmodule('minecraft')
		if not cbsourcemod:
			continue
		cbtarget = {'module': module.name, 'name': sender}
		cbsource = {'module': cbsourcemod, 'name': configs[conf]['minecraft'], 'protocol': 'rcon'}

		target = {'module': 'minecraft', 'name': configs[conf]['minecraft']}
		evt = {'command': 'whitelist ' + parts[1] + ' ' + parts[2], 'callback': functools.partial(_rcon_whitelist_reply, loop=loop, source=cbsource, target=cbtarget, irctarget=data['target'])}

		_modules.send_event_target(loop, target, module, sender, 'whitelist', 'RCON_SENDCMD', evt)

def _rcon_whitelist_reply(packet, loop, source, target, irctarget):
	global log

	log.debug(str(packet) + ' ' + str(source) + ' ' + str(target) + ' ' + irctarget)

	reply = packet['payload'].decode('utf-8')

	if reply and len(reply) > 0:
		evt = {'command': 'PRIVMSG ' + irctarget + ' :' + reply, 'callback': None}
		_modules.send_event_target(loop, target, source['module'], source['name'], 'whitelist', 'IRC_SENDCMD', evt)
