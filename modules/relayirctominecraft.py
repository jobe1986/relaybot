# -*- coding: utf-8 -*-

# RelayBot - Simple VNC Relay Service, modules/relayirctominecraft.py
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

rconlistre = re.compile('^(?P<header>There are \d+ of a max of \d+ players online:) ?(?P<list>.*?)$')

def loadconfig(config, module):
	global configs
	global log

	for relaycfg in config:
		if not 'name' in relaycfg.attrib:
			log.warning('Relay (IRC To Minecraft) config missing name attribute')
			continue
		if relaycfg.attrib['name'] in configs:
			log.warning('Duplicate Relay (IRC To Minecraft) config name: ' + relaycfg.attrib['name'])
			continue

		name = relaycfg.attrib['name']
		conf = {'name': name, 'irc': '', 'minecraft': '', 'channels': []}

		irc = relaycfg.findall('./irc')
		if not irc:
			log.warning('Relay (IRC To Minecraft) ' + name + ' missing IRC configuration')
			continue
		if not 'name' in irc[0].attrib:
			log.warning('Relay (IRC To Minecraft) ' + name + ' IRC configuration missing name attribute')
			continue

		ircchans = irc[0].findall('./channel')
		if ircchans:
			for chan in ircchans:
				if not 'name' in chan.attrib:
					log.warning('Relay (IRC To Minecraft) ' + name + ' IRC channel configuration missing name attribute')
					continue
				conf['channels'].append(chan.attrib['name'].lower())

		conf['irc'] = irc[0].attrib['name']

		mc = relaycfg.findall('./minecraft')
		if not mc:
			log.warning('Relay (IRC To Minecraft) ' + name + ' missing Minecraft configuration')
			continue
		if not 'name' in mc[0].attrib:
			log.warning('Relay (IRC To Minecraft) ' + name + ' Minecraft configuration missing name attribute')
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
		log.info('Creating Relay (IRC To Minecraft) ' + name)
	return

def shutdown(loop):
	return

def handle_event(loop, module, sender, protocol, event, data):
	global log
	global configs
	
	events = ['CHANNEL_MESSAGE', 'CHANNEL_ACTION']

	if module.name != 'irc':
		return

	if not event in events:
		return

	log.debug('Relaying event ' + event + ' to minecraft: ' + str(data))

	for name in configs:
		conf = configs[name]

		if conf['irc'] != sender:
			continue

		if len(conf['channels']) > 0:
			if not data['target'].lower() in conf['channels']:
				continue

		if data['message'].split(' ')[0] == '?players':
			cbsourcemod = _modules.getmodule('minecraft')
			if not cbsourcemod:
				continue
			cbtarget = {'module': module.name, 'name': sender}
			cbsource = {'module': cbsourcemod, 'name': conf['minecraft'], 'protocol': 'rcon'}

			target = {'module': 'minecraft', 'name': conf['minecraft']}
			evt = {'command': 'list', 'callback': functools.partial(_rcon_list_callback, loop=loop, source=cbsource, target=cbtarget, irctarget=data['target'])}

			_modules.send_event_target(loop, target, module, sender, 'relay', 'RCON_SENDCMD', evt)

		parts = []
		parts.append('[IRC] ')
		if event == 'CHANNEL_MESSAGE':
			parts.append('<' + data['name'] + '> ')
		elif event == 'CHANNEL_ACTION':
			parts.append('* ' + data['name'] + ' ')

		for part in filter(None, re.split('(https?://[^\s]+)', data['message'])):
			if part[0:7] == 'http://' or part[0:8] == 'https://':
				parts.append({'text': part, 'underlined': True, 'clickEvent': {'action': 'open_url', 'value': part}})
			else:
				parts.append(part)
		text = json.dumps(parts)

def _rcon_list_callback(packet, loop, source, target, irctarget):
	global log
	global rconlistre

	log.debug(str(packet) + ' ' + str(source) + ' ' + str(target) + ' ' + irctarget)

	listtext = packet['payload'].decode('utf-8')

	m = rconlistre.match(listtext)
	if not m:
		return

	evt = {'command': 'PRIVMSG ' + irctarget + ' :' + m.group('header'), 'callback': None}
	_modules.send_event_target(loop, target, source['module'], source['name'], 'relay', 'IRC_SENDCMD', evt)
	if m.group('list') != '':
		evt = {'command': 'PRIVMSG ' + irctarget + ' :' + m.group('list'), 'callback': None}
		_modules.send_event_target(loop, target, source['module'], source['name'], 'relay', 'IRC_SENDCMD', evt)

	return
