# -*- coding: utf-8 -*-

# RelayBot - Simple Relay Service, modules/minecraftircwhitelist.py
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
import core.modules as _modules
import datetime, json, os, re, urllib.request, zipfile

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
			log.warning('Minecraft Version config missing name attribute')
			continue
		if relaycfg.attrib['name'] in configs:
			log.warning('Duplicate Minecraft Version config name: ' + relaycfg.attrib['name'])
			continue

		name = relaycfg.attrib['name']
		conf = {'name': name, 'irc': '', 'minecraft': '', 'channels': [], 'jarfile': '', 'lastcheck': None}

		irc = relaycfg.findall('./irc')
		if not irc:
			log.warning('Minecraft Version ' + name + ' missing IRC configuration')
			continue
		if not 'name' in irc[0].attrib:
			log.warning('Minecraft Version ' + name + ' IRC configuration missing name attribute')
			continue

		ircchans = irc[0].findall('./channel')
		if ircchans:
			for chan in ircchans:
				if not 'name' in chan.attrib:
					log.warning('Minecraft Version ' + name + ' IRC channel configuration missing name attribute')
					continue
				conf['channels'].append(chan.attrib['name'].lower())

		conf['irc'] = irc[0].attrib['name']

		mc = relaycfg.findall('./minecraft')
		if not mc:
			log.warning('Minecraft Version ' + name + ' missing Minecraft configuration')
			continue
		if not 'name' in mc[0].attrib:
			log.warning('Minecraft Version ' + name + ' Minecraft configuration missing name attribute')
			continue
		if not 'jarfile' in mc[0].attrib:
			log.warning('Minecraft Version ' + name + ' Minecraft configuration missing jarfile attribute')
			continue
		if not os.path.exists(mc[0].attrib['jarfile']):
			log.warning('Minecraft Version ' + name + ' Minecraft configuration: the jarfile specified does not exist')
			continue

		conf['minecraft'] = mc[0].attrib['name']
		conf['jarfile'] = mc[0].attrib['jarfile']

		configs[name] = conf
		log.debug('Loaded config: ' + str(conf))
	return

def applyconfig(loop, module):
	global configs
	global log

	for name in configs:
		conf = configs[name]
		log.info('Creating Minecraft Version ' + name)
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
		if not parts[0] in ['?version', '?snapshot']:
			break

		target = {'module': module.name, 'name': sender}
		cached = ''

		type = 'version'
		if parts[0] == '?snapshot':
			type = 'snapshot'

		if (configs[conf]['lastcheck'] is None) or ((datetime.datetime.utcnow() - configs[conf]['lastcheck']).seconds > 300):
			configs[conf]['jarver'] = _getjarversion(configs[conf]['jarfile'])
			configs[conf]['latestver'], configs[conf]['latestsnap'] = _getlatestver('https://launchermeta.mojang.com/mc/game/version_manifest.json')
			configs[conf]['lastcheck'] = datetime.datetime.utcnow()
		else:
			cached = ' (cached)'

		if configs[conf]['jarver'] is None:
			evt = {'command': 'PRIVMSG ' + data['target'] + ' :Unable to retrive the current ' + type + ' for ' + configs[conf]['minecraft'], 'callback': None}
			_modules.send_event_target(loop, target, moduleobj, conf, 'version', 'IRC_SENDCMD', evt)
			break
		if configs[conf]['latestver'] is None:
			evt = {'command': 'PRIVMSG ' + data['target'] + ' :Unable to retrieve the latest available ' + type, 'callback': None}
			_modules.send_event_target(loop, target, moduleobj, conf, 'version', 'IRC_SENDCMD', evt)
			break

		if type == 'snapshot':
			evt = {'command': 'PRIVMSG ' + data['target'] + ' :The latest available minecraft snapshot is: ' + configs[conf]['latestsnap'] + cached, 'callback': None}
			_modules.send_event_target(loop, target, moduleobj, conf, 'version', 'IRC_SENDCMD', evt)
		else:
			if configs[conf]['jarver'] == configs[conf]['latestver']:
				evt = {'command': 'PRIVMSG ' + data['target'] + ' :' + configs[conf]['minecraft'] + ' is currently up to date and running: ' + configs[conf]['jarver'] + cached, 'callback': None}
				_modules.send_event_target(loop, target, moduleobj, conf, 'version', 'IRC_SENDCMD', evt)
			else:
				evt = {'command': 'PRIVMSG ' + data['target'] + ' :' + configs[conf]['minecraft'] + ' is currently running: ' + configs[conf]['jarver'] + cached, 'callback': None}
				_modules.send_event_target(loop, target, moduleobj, conf, 'version', 'IRC_SENDCMD', evt)
				evt = {'command': 'PRIVMSG ' + data['target'] + ' :The latest available minecraft version is: ' + configs[conf]['latestver'] + cached, 'callback': None}
				_modules.send_event_target(loop, target, moduleobj, conf, 'version', 'IRC_SENDCMD', evt)

def _getjarversion(file):
	try:
		z = zipfile.ZipFile(file, 'r')
		txt = z.read('version.json')
		z.close()
		jsobj = json.loads(txt.decode('utf-8'))
		return jsobj['name']
	except:
		return None

def _getlatestver(url):
	try:
		jsontxt = ''
		relval = None
		snapval = None
		with urllib.request.urlopen(url) as f:
			jsontxt = f.read().decode('utf-8')
			f.close()
		jsonobj = json.loads(jsontxt)
		if not 'latest' in jsonobj:
			return None, None
		if 'release' in jsonobj['latest']:
			relval = jsonobj['latest']['release']
		if 'snapshot' in jsonobj['latest']:
			snapval = jsonobj['latest']['snapshot']
		return relval, snapval
	except:
		return None, None
