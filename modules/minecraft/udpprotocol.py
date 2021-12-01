# -*- coding: utf-8 -*-

# RelayBot - Simple VNC Relay Service, modules/minecraft/udpprotocol.py
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
import asyncio, re

log = _logging.log.getChild(__name__)

clients = {}

class MCUDPProtocol(asyncio.Protocol):
	def __init__(self, loop, config):
		global clients
		self.loop = loop
		self.config = config
		self.transport = None
		self.log = log.getChildObj(self.config['name'])

		self.isshutdown = False

		self.logre = re.compile('^\[(?P<time>[^\]]+)\] \[(?P<thread>[^\]]+?)(?: #[0-9]+)?/(?P<level>[A-Z]+)\]: (?P<message>[^\\r\\n]+)$')
		self.msgre = {
			'Server thread': {
				'USER_IP': [re.compile('^(?P<name>.+?)\\[/(?P<ip>.+?):(?P<port>[0-9]+?)\\] logged in with entity id.*?$')],
				'USER_CONNECT': [re.compile('^(?P<name>.+?) (?:\\(formerly known as .+?\\) )?joined the game$')],
				'USER_DISCONNECT': [re.compile('^(?P<name>.+?) (?:\\(formerly known as .+?\\) )?left the game$')],
				'WHITELIST_FAIL': [re.compile('^com.mojang.authlib.GameProfile.+?id=(?P<uuid>[-a-f0-9]+),.*?name=(?P<name>.+?),.*?lost connection: You are not white-listed on this server!.*?$')],
				'MESSAGE': [
					re.compile('^(?P<raw><(?P<name>.+?)> (?P<message>.*?))$'),
					re.compile('^(?P<raw>\\[(?P<name>[^ ]+?)\\] (?P<message>.*?))$')
					],
				'ACTION': [re.compile('^(?P<raw>\\* (?P<name>.+?) (?P<message>.*?))$')],
				'ADVANCEMENT': [
					re.compile('^(?P<name>.+?) (?P<message>has (?:lost|just earned) the achievement \\[(?P<advancement>.*?)\\])$'),
					re.compile('^(?P<name>.+?) (?P<message>has made the advancement \\[(?P<advancement>.*?)\\])$'),
					re.compile('^(?P<name>.+?) (?P<message>has completed the challenge \\[(?P<advancement>.*?)\\])$'),
					re.compile('^(?P<name>.+?) (?P<message>has reached the goal \\[(?P<advancement>.*?)\\])$')
					],
				'DEATH': [
					re.compile('^(?P<message>(?P<name>.*?) was slain by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was killed by even more magic)$'),
					re.compile('^(?P<message>(?P<name>.*?) tried to swim in lava)$'),
					re.compile('^(?P<message>(?P<name>.*?) fell off some vines)$'),
					re.compile('^(?P<message>(?P<name>.*?) fell too far and was finished by .*? using .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was impaled by .*? with .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) fell off some twisting vines)$'),
					re.compile('^(?P<message>(?P<name>.*?) was squashed by a falling block whilst fighting .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was burnt to a crisp whilst fighting .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was killed by .*? using magic)$'),
					re.compile('^(?P<message>(?P<name>.*?) experienced kinetic energy)$'),
					re.compile('^(?P<message>(?P<name>.*?) was killed trying to hurt .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) blew up)$'),
					re.compile('^(?P<message>(?P<name>.*?) was struck by lightning)$'),
					re.compile('^(?P<message>(?P<name>.*?) was squashed by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was roasted in dragon breath by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was impaled on a stalagmite)$'),
					re.compile('^(?P<message>(?P<name>.*?) fell while climbing)$'),
					re.compile('^(?P<message>(?P<name>.*?) went off with a bang due to a firework fired from .*? by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was fireballed by .*? using .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was squished too much)$'),
					re.compile('^(?P<message>(?P<name>.*?) was shot by .*? using .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) went up in flames)$'),
					re.compile('^(?P<message>(?P<name>.*?) was skewered by a falling stalactite whilst fighting .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) fell off some weeping vines)$'),
					re.compile('^(?P<message>(?P<name>.*?) was blown up by .*? using .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) fell too far and was finished by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) experienced kinetic energy whilst trying to escape .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was shot by a skull from .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) went off with a bang whilst fighting .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was squashed by a falling anvil)$'),
					re.compile('^(?P<message>(?P<name>.*?) was shot by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) drowned)$'),
					re.compile('^(?P<message>(?P<name>.*?) was doomed to fall by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) starved to death)$'),
					re.compile('^(?P<message>(?P<name>.*?) was impaled by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) fell from a high place)$'),
					re.compile('^(?P<message>(?P<name>.*?) was squashed by a falling anvil whilst fighting .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) withered away)$'),
					re.compile('^(?P<message>(?P<name>.*?) tried to swim in lava to escape .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) died because of .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) froze to death)$'),
					re.compile('^(?P<message>(?P<name>.*?) was roasted in dragon breath)$'),
					re.compile('^(?P<message>(?P<name>.*?) drowned whilst trying to escape .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) fell off a ladder)$'),
					re.compile('^(?P<message>(?P<name>.*?) was pummeled by .*? using .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was struck by lightning whilst fighting .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) hit the ground too hard)$'),
					re.compile('^(?P<message>(?P<name>.*?) was killed by magic)$'),
					re.compile('^(?P<message>(?P<name>.*?) died from dehydration)$'),
					re.compile('^(?P<message>(?P<name>.*?) was pummeled by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was impaled on a stalagmite whilst fighting .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) fell off scaffolding)$'),
					re.compile('^(?P<message>(?P<name>.*?) was skewered by a falling stalactite)$'),
					re.compile('^(?P<message>(?P<name>.*?) was stung to death)$'),
					re.compile('^(?P<message>(?P<name>.*?) suffocated in a wall whilst fighting .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was slain by .*? using .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was pricked to death)$'),
					re.compile('^(?P<message>(?P<name>.*?) fell out of the world)$'),
					re.compile('^(?P<message>(?P<name>.*?) was frozen to death by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was squashed by a falling block)$'),
					re.compile('^(?P<message>(?P<name>.*?) was killed by .*? using .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) suffocated in a wall)$'),
					re.compile('^(?P<message>(?P<name>.*?) walked into fire whilst fighting .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) burned to death)$'),
					re.compile('^(?P<message>(?P<name>.*?) starved to death whilst fighting .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was poked to death by a sweet berry bush)$'),
					re.compile('^(?P<message>(?P<name>.*?) walked into danger zone due to .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was killed by .*? trying to hurt .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was stung to death by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) didn\'t want to live in the same world as .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was doomed to fall by .*? using .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) went off with a bang)$'),
					re.compile('^(?P<message>(?P<name>.*?) was poked to death by a sweet berry bush whilst trying to escape .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) discovered the floor was lava)$'),
					re.compile('^(?P<message>(?P<name>.*?) died)$'),
					re.compile('^(?P<message>(?P<name>.*?) was killed by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) died from dehydration whilst trying to escape .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) hit the ground too hard whilst trying to escape .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was doomed to fall)$'),
					re.compile('^(?P<message>(?P<name>.*?) was killed by magic whilst trying to escape .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was fireballed by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) was blown up by .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) walked into a cactus whilst trying to escape .*?)$'),
					re.compile('^(?P<message>(?P<name>.*?) withered away whilst fighting .*?)$'),
					]
				},
			'User Authenticator': {
				'USER_UUID': [re.compile('^UUID of player (?P<name>.+) is (?P<uuid>[-a-f0-9]+)$')]
				}
			}

		clients[self.config['name']] = self

	def connection_made(self, transport):
		self.transport = transport

	def connection_lost(self, exc):
		global clients

		if not exc is None:
			self.log.info('Lost UDP connection: ' + str(exc))
		else:
			self.log.info('Lost UDP connection')
		if self.config['name'] in clients:
			del clients[self.config['name']]

		if self.isshutdown:
			return

		self.log.info('Retrying in 30 seconds')
		self.loop.call_later(30, createclient, self.loop, self.config)

	def error_received(self, ex):
		self.log.debug('Error received: ' + str(ex))

	def datagram_received(self, data, addr):
		lines = data.decode('utf-8').replace('\r', '\n').split('\n')
		for line in lines:
			if len(line) <= 0:
				continue
			self.log.protocol('Received UDP message from ' + str(addr) + ': ' + line)
			match = self.logre.match(line)
			if match:
				self.log.protocol('Parsed UDP message: ' + str(match.groupdict()))
				self._handle_msg(match.groupdict())
			else:
				self.log.warning('Unable to parse UDP message')

	def shutdown(self, loop):
		self.isshutdown = True
		self.log.info('Shutting down UDP listener on ' + self.config['udp']['host'] + ']:' + self.config['udp']['port'])
		self.transport.close()
	
	def _handle_msg(self, msg):
		for thread in self.msgre:
			if msg['thread'] == thread:
				for event in self.msgre[thread]:
					for rec in self.msgre[thread][event]:
						match = rec.match(msg['message'])
						if match:
							self.log.debug('Event "' + event + '": ' + str(match.groupdict()))
							#relay events here
			else:
				continue
		
		return

async def connectclient(loop, conf):
	try:
		serv = '[' + conf['udp']['host'] + ']:' + conf['udp']['port']
		log.info('Creating UDP listener ' + conf['name'] + ' listening on ' + serv)
		await loop.create_datagram_endpoint(lambda: MCUDPProtocol(loop, conf), (conf['udp']['host'], conf['udp']['port']), reuse_address=True, reuse_port=True)
	except Exception as e:
		log.warning('Exception occurred attempting to create UDP listener ' + conf['name'] + ': ' + str(e))
		log.info('Retrying in 30 seconds')
		loop.call_later(10, createclient, loop, conf)
	return

def createclient(loop, conf):
	loop.create_task(connectclient(loop, conf))
