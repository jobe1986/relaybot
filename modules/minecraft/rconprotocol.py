# -*- coding: utf-8 -*-

# RelayBot - Simple VNC Relay Service, modules/minecraft/rconprotocol.py
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
import asyncio, binascii, struct

log = _logging.log.getChild(__name__)

clients = {}

class MCRConProtocol(asyncio.Protocol):
	def __init__(self, loop, config):
		global clients
		self.loop = loop
		self.config = config
		self.transport = None
		self.log = log.getChildObj(self.config['name'])
		self.id = 0

		self.isshutdown = False

		clients[self.config['name']] = self

	def connection_made(self, transport):
		self.transport = transport
		self.log.debug('Connected to RCON, sending login')
		self._sendcmd(self.config['rcon']['password'], 3)

	def connection_lost(self, exc):
		global clients
		if not exc is None:
			self.log.info('Lost connection: ' + str(exc))
		else:
			self.log.info('Lost connection')
		if self.config['name'] in clients:
			del clients[self.config['name']]

		if self.isshutdown:
			return

		self.log.info('Reconnecting in 30 seconds')
		self.loop.call_later(30, createclient, self.loop, self.config)
		return

	def eof_received(self):
		self.log.debug('EOF received')
		return

	def data_received(self, data):
		self.log.protocol('Received RCON packet: ' + binascii.hexlify(data).decode('utf-8'))
		return

	def shutdown(self, loop):
		self.isshutdown = True
		self.transport.close()

	def _sendcmd(self, cmd, type=2):
		rid = self.id
		pkt = self._rconpacket(self.id, type, cmd)
		self.id += 1
		self.log.protocol('Sending RCON packet: ' + binascii.hexlify(pkt).decode('utf-8'))
		self.transport.write(pkt)
		return rid

	def _rconpacket(self, id=0, type=0, payload=None):
		pkt = struct.pack('<ii', id, type)
		if payload != None:
			pkt += payload.encode('utf-8')
		else:
			payload = ''
		pkt += b'\x00\x00'

		pkt = struct.pack('<i', len(pkt)) + pkt

		return pkt

async def connectclient(loop, conf):
	try:
		log.info('Connecting RCON client ' + conf['name'] + ' to ' + '[' + conf['rcon']['host'] + ']:' + conf['rcon']['port'])
		await loop.create_connection(lambda: MCRConProtocol(loop, conf), conf['rcon']['host'], conf['rcon']['port'])
	except Exception as e:
		log.warning('Exception occurred attempting to connect RCON client ' + conf['name'] + ': ' + str(e))
		log.info('Reconnecting in 30 seconds')
		loop.call_later(10, createclient, loop, conf)
	return

def createclient(loop, conf):
	loop.create_task(connectclient(loop, conf))
