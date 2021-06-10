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
import asyncio

log = _logging.log.getChild(__name__)

clients = {}

class IRCClientProtocol(asyncio.Protocol):
	def __init__(self, loop, config):
		global clients
		self.loop = loop
		self.config = config
		self.transport = None
		self.log = log.getChild(self.config['name'])
		clients[self.config['name']] = self
		print('moo')

	def connection_made(self, transport):
		self.transport = transport
		self.log.info('Connection established')
		return

	def connection_lost(self, exc):
		global clients
		self.log.info('Lost connection: ' + str(exc))
		del clients[self.config['name']]

		self.log.info('Reconnecting in 30 seconds')
		self.loop.call_later(30, createclient, self.loop, self.config)
		return

	def eof_received(self):
		self.log.debug('EOF received')
		return

	def data_received(self, data):
		lines = data.decode('utf-8').replace('\r', '\n').split('\n')

		for line in lines:
			if len(line) > 0:
				self.log.protocol('Received line: ' + line)
		return

def createclient(loop, conf):
	log.info('Connecting to client ' + conf['name'])
	coro = loop.create_connection(lambda: IRCClientProtocol(loop, conf), conf['server']['host'], conf['server']['port'], ssl=conf['server']['tls'])
	loop.create_task(coro)
