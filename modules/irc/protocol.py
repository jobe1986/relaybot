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
		self.log = log.getChildObj(self.config['name'])
		clients[self.config['name']] = self

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

async def connectclient(loop, conf):
	try:
		serv = '[' + conf['server']['host'] + ']:'
		if conf['server']['tls']:
			serv = serv + '+'
		serv = serv + str(conf['server']['port'])
		log.info('Connecting client ' + conf['name'] + ' to ' + serv)
		await loop.create_connection(lambda: IRCClientProtocol(loop, conf), conf['server']['host'], conf['server']['port'], ssl=conf['server']['tls'])
	except Exception as e:
		log.warning('Exception occurred attempting to connect client ' + conf['name'] + ': ' + str(e))
		log.info('Reconnecting in 30 seconds')
		loop.call_later(10, createclient, loop, conf)

		log.debug('Stopping here for log review')
		loop.stop()

def createclient(loop, conf):
	loop.create_task(connectclient(loop, conf))
