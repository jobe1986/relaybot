# -*- coding: utf-8 -*-

# RelayBot - Simple VNC Relay Service, modules/irc/protocol.py
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
import asyncio

log = _logging.log.getChild(__name__)

clients = {}

class IRCClientProtocol(asyncio.Protocol):
	def __init__(self, loop, config, module):
		global clients
		self.loop = loop
		self.config = config
		self.module = module
		self.transport = None
		self.log = log.getChildObj(self.config['name'])

		self.isshutdown = False
		self.hasperformed = False
		self.errormsg = None
		self.capendhandle = None

		self.chans = config['channels']
		self.user = config['user']
		self.user['newnick'] = self.user['nick']

		self.handlers = {
			'005': self.m_005,
			'433': self.m_433,
			'CAP': self.m_cap,
			'ERROR': self.m_error,
			'JOIN': self.m_join,
			'KICK': self.m_kick,
			'NICK': self.m_nick,
			'PART': self.m_part,
			'PING': self.m_ping,
			'PRIVMSG': self.m_privmsg
		}

		self.caps = {
			'away-notify': False,
			'account-notify': False,
			'extended-join': False,
			'multi-prefix': False,
			'userhost-in-names': False
		}

		clients[self.config['name']] = self

	def connection_made(self, transport):
		self.transport = transport
		self.log.info('Connection established')
		self._send('CAP', 'LS')
		if self.config['server']['password'] is not None:
			self._send('PASS', self.config['server']['password'])
		self._send('NICK', self.config['user']['nick'])
		self._send('USER', self.config['user']['user'], '0', '*', self.config['user']['gecos'])
		return

	def connection_lost(self, exc):
		global clients
		if not exc is None:
			self.log.info('Lost connection: ' + str(exc))
		elif not self.errormsg is None:
			self.log.info('Lost connection: ' + self.errormsg)
		else:
			self.log.info('Lost connection')
		if self.config['name'] in clients:
			del clients[self.config['name']]

		if self.capendhandle is not None:
			self.capendhandle.cancel()

		if self.isshutdown:
			return

		self.log.info('Reconnecting in 30 seconds')
		self.loop.call_later(30, createclient, self.loop, self.config, self.module)
		return

	def eof_received(self):
		self.log.debug('EOF received')
		return

	def data_received(self, data):
		lines = data.decode('utf-8').replace('\r', '\n').split('\n')

		for line in lines:
			if len(line) > 0:
				self.log.protocol('Received line: ' + line)
				msg = self._parse_raw_irc(line)
				self.log.protocol('Parsed message: ' + str(msg))

				if msg['msg'] in self.handlers:
					self.handlers[msg['msg']](msg)

				#_modules.send_event(self.loop, self.module, self.config['name'], 'irc', 'IRC_RAW', msg)
		return

	def shutdown(self, loop):
		self.isshutdown = True
		self._send('QUIT', 'Shutting down')
		if self.transport:
			self.transport.close()

	def handle_event(self, loop, module, sender, protocol, event, data):
		if event != 'IRC_SENDCMD':
			return

		if not 'command' in data:
			self.log.warning('Event ' + event + ' missing command to execute')
			return

		self._send(data['command'])

	def m_005(self, msg):
		if self.hasperformed:
			return

		chans = []
		chank = {}
		for chan in self.chans:
			self.chans[chan]['joined'] = False
			chan = self.chans[chan]

			if 'key' in chan:
				chank[chan['name']] = chan['key']
			else:
				chans.append(chan['name'])

		i = 0
		chanlst = ''
		for chan in chans:
			if len(chanlst) > 0:
				chanlst += ','
			chanlst += chan
			i += 1

			if i >= 5:
				self.log.debug('Joining channels: ' + chanlst)
				self._send('JOIN', chanlst)
				chanlst = ''
				i = 0
		if i > 0:
			self.log.debug('Joining channels: ' + chanlst)
			self._send('JOIN', chanlst)

		i = 0
		chanlst = ''
		keylst = ''
		for chan in chank:
			if len(chanlst) > 0:
				chanlst += ','
				keylst += ' '
			chanlst += chan
			keylst += chank[chan]
			i += 1

			if i >= 5:
				self.log.debug('Joining channels: ' + chanlst)
				self._send('JOIN', chanlst, keylst)
				chanlst = ''
				keylst = ''
				i = 0
		if i > 0:
			self.log.debug('Joining channels: ' + chanlst)
			self._send('JOIN', chanlst, keylst)

		self.hasperformed = True

	def m_433(self, msg):
		targ = msg['params'][0]
		newnick = msg['params'][1]
		if targ == '*' or targ.lower() == self.user['nick'].lower() or newnick.lower() == self.user['newnick'].lower():
			if not 'inc' in self.user:
				self.user['inc'] = 0
			else:
				self.user['inc'] += 1
			self.user['newnick'] = self.config['user']['nick'] + ('%04d' % self.user['inc'])
			self._send('NICK', self.user['newnick'])

	def m_cap(self, msg):
		if msg['params'][1] == 'LS':
			if self.capendhandle is not None:
				self.capendhandle.cancel()

			caps = msg['params'][-1].split(' ')
			req = []
			for cap in caps:
				if cap in self.caps:
					req.append(cap)

			self._send('CAP', 'REQ', ' '.join(req))

			self.capendhandle = self.loop.call_later(2, self._capend)
		elif msg['params'][1] == 'ACK':
			caps = msg['params'][-1].split(' ')
			for cap in caps:
				if cap in self.caps:
					self.caps[cap] = True

	def m_error(self, msg):
		self.errormsg = msg['params'][-1]
		self.log.error('Received error: ' + self.errormsg)

	def m_join(self, msg):
		chan = msg['params'][0].lower()
		who = msg['source']['name'].lower()

		if who == self.user['nick'].lower():
			if chan in self.chans:
				log.info('Joined channel ' + self.chans[chan]['name'])
				self.chans[chan]['joined'] = True

	def m_kick(self, msg):
		chan = msg['params'][0].lower()
		victim = msg['params'][1].lower()

		if victim == self.user['nick'].lower():
			if chan in self.chans:
				log.info('Kicked from channel channel ' + self.chans[chan]['name'])
				self.chans[chan]['joined'] = False

	def m_nick(self, msg):
		who = msg['source']['name'].lower()
		newnick = msg['params'][0]

		if who == self.user['nick'].lower():
			self.user['nick'] = newnick
			self.user['newnick'] = newnick
			log.info('Changed nick to ' + newnick)

	def m_part(self, msg):
		chan = msg['params'][0].lower()
		who = msg['source']['name'].lower()

		if who == self.user['nick'].lower():
			if chan in self.chans:
				log.info('Parted channel ' + self.chans[chan]['name'])
				self.chans[chan]['joined'] = False
				if 'key' in self.chans[chan]:
					self._send('JOIN', self.chans[chan]['name'], self.chans[chan]['key'])
				else:
					self._send('JOIN', self.chans[chan]['name'])

	def m_ping(self, msg):
		self._send('PONG', msg['params'][0])

	def m_privmsg(self, msg):
		text = msg['params'][-1]
		target = msg['params'][0].lower()
		if len(text) > 0:
			if target in self.chans:
				if self.chans[target]['joined']:
					event = 'CHANNEL_MESSAGE'
					if text[:7] == '\x01ACTION':
						if len(text) > 8:
							text = text[8:]
							if text[-1] == '\x01':
								text = text[:-1]
							event = 'CHANNEL_ACTION'
					evt = {'irc': msg, 'name': msg['source']['name'], 'target': target, 'message': text}
					self.log.debug('Event "' + event + '": ' + str(evt))

					_modules.send_event(self.loop, self.module, self.config['name'], 'irc', event, evt)
			else:
				if text[0] == '\x01':
					text = text[1:]
					if len(text) > 0:
						if text[-1] == '\x01':
							text = text[:-1]
					if len(text) > 0:
						words = text.split(' ')
						if words[0].upper() == 'VERSION':
							self._send('NOTICE', msg['source']['name'], '\x01VERSION RelayBot 2.0 https://github.com/jobe1986/relaybot\x01')

	def _capend(self):
		self._send('CAP', 'END')
		self.capendhandle = None

	def _send(self, msg, *params, **kwargs):
		line = msg

		if len(msg) <= 0:
			return

		for param in params:
			if len(param) <= 0:
				continue
			line += ' '
			if ' ' in param or param[0] == ':':
				line += ':'
			line += param

		if self.transport:
			self.transport.write((line + '\r\n').encode('utf-8'))
		self.log.protocol('Sent line: ' + line)

	def _parse_raw_irc(self, line):
		ret = {'source': {'full': '', 'name': '', 'ident': '', 'host': ''}, 'msg': '', 'params': []}
		stat = 0
		words = line.split(' ')

		for word in words:
			if ((stat < 3) and (len(word) == 0)):
				continue

			if (stat == 0):
				stat += 1
				if (word[0] == ':'):
					ret['source']['full'] = word[1:]
				else:
					ret['msg'] = word
					stat += 1
			elif (stat == 1):
				ret['msg'] = word
				stat += 1
			elif (stat == 2):
				if (word[0] == ':'):
					ret['params'].append(word[1:])
					stat += 1
				else:
					ret['params'].append(word)
			else:
				ret['params'][-1] = ret['params'][-1] + ' ' + word

		if (len(ret['source']['full']) > 0):
			src = ret['source']['full']
			if (src.find('@') >= 0):
				ret['source']['host'] = src[src.find('@')+1:]
				src = src[:src.find('@')]
			if (src.find('!') >= 0):
				ret['source']['ident'] = src[src.find('!')+1:]
				src = src[:src.find('!')]
			ret['source']['name'] = src

		return ret

async def connectclient(loop, conf, module):
	try:
		serv = '[' + conf['server']['host'] + ']:'
		if conf['server']['tls']:
			serv = serv + '+'
		serv = serv + str(conf['server']['port'])
		log.info('Connecting IRC client ' + conf['name'] + ' to ' + serv)
		await loop.create_connection(lambda: IRCClientProtocol(loop, conf, module), conf['server']['host'], conf['server']['port'], ssl=conf['server']['tls'])
	except Exception as e:
		log.warning('Exception occurred attempting to connect IRC client ' + conf['name'] + ': ' + str(e))
		log.info('Reconnecting in 30 seconds')
		loop.call_later(10, createclient, loop, conf, module)

def createclient(loop, conf, module):
	loop.create_task(connectclient(loop, conf, module))
