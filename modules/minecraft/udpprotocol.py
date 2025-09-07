# -*- coding: utf-8 -*-

# RelayBot - Simple Relay Service, modules/minecraft/udpprotocol.py
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
import asyncio, re

from modules.minecraft.loghandler import LogHandler

log = _logging.log.getChild(__name__)

clients = {}

class MCUDPProtocol(asyncio.Protocol):
	def __init__(self, loop, config, module, handler):
		global clients
		self.loop = loop
		self.config = config
		self.module = module
		self.handler = handler
		self.transport = None
		self.log = log.getChildObj(self.config['name'])

		self.isshutdown = False

		self.logre = re.compile('^\[(?P<time>[^\]]+)\] \[(?P<thread>[^\]]+?)(?: #[0-9]+)?/(?P<level>[A-Z]+)\]: (?P<message>[^\\r\\n]+)$')

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
		self.loop.call_later(30, createclient, self.loop, self.config, self.module)

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
				self.handler.handle_msg(match.groupdict())
			else:
				self.log.warning('Unable to parse UDP message')

	def shutdown(self, loop):
		self.isshutdown = True
		self.log.info('Shutting down UDP listener on ' + self.config['udp']['host'] + ']:' + self.config['udp']['port'])
		self.transport.close()

	def handle_event(self, loop, module, sender, protocol, event, data):
		self.handler.handle_event(loop, module, sender, protocol, event, data)


async def connectclient(loop, conf, module):
	try:
		serv = '[' + conf['udp']['host'] + ']:' + conf['udp']['port']
		handler = LogHandler(loop, conf, module)
		log.info('Creating UDP listener ' + conf['name'] + ' listening on ' + serv)
		await loop.create_datagram_endpoint(lambda: MCUDPProtocol(loop, conf, module, handler), (conf['udp']['host'], conf['udp']['port']), reuse_port=True)
	except Exception as e:
		log.warning('Exception occurred attempting to create UDP listener ' + conf['name'] + ': ' + str(e))
		log.info('Retrying in 30 seconds')
		loop.call_later(30, createclient, loop, conf, module)
	return

def createclient(loop, conf, module):
	loop.create_task(connectclient(loop, conf, module))
