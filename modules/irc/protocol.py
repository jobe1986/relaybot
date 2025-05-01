# -*- coding: utf-8 -*-

# RelayBot - Simple Relay Service, modules/irc/protocol.py
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
import asyncio
import re

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
		self.pingcheck = False

		self.rejoindelay = 30
		self.pingfrequency = 30

		self.chans = config['channels']
		self.user = config['user']
		self.user['newnick'] = self.user['nick']

		self.n005kv = re.compile('^(?P<key>[^=]+?)(?:=(?P<value>.*?))?$')

		self.chantypes = '#'
		self.chanusrpfx = '@+'
		self.chanusrpfxmodes = 'ov'
		self.chanmodes = ['b', 'k', 'l', 'imnpst']
		self.haswhox = False

		self.rejointimer = None
		self.pingtimer = None
		self.timers = []

		self.handlers = {
			'005': self.m_005,
			'353': self.m_353,
			'354': self.m_354,
			'366': self.m_366,
			'433': self.m_433,
			'ACCOUNT': self.m_account,
			'CAP': self.m_cap,
			'ERROR': self.m_error,
			'JOIN': self.m_join,
			'KICK': self.m_kick,
			'KILL': self.m_kill,
			'MODE': self.m_mode,
			'NICK': self.m_nick,
			'PART': self.m_part,
			'PING': self.m_ping,
			'PRIVMSG': self.m_privmsg,
			'QUIT': self.m_quit
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
		self._resetping()
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

		self._resetping()

		for line in lines:
			if len(line) > 0:
				self.log.protocol('Received line: ' + line)
				msg = self._parse_raw_irc(line)
				self.log.protocol('Parsed message: ' + str(msg))

				if msg['msg'] in self.handlers:
					self.handlers[msg['msg']](msg)

				#_modules.send_event(self.loop, self.module, self.config['name'], 'irc', 'IRC_RAW', msg)
		return

	def disconnect(self, reason):
		self._send('QUIT', reason)
		if self.transport:
			self.transport.close()
		for chan in self.chans:
			try:
				if self.chans[chan]['jointimer']:
					self.chans[chan]['jointimer'].cancel()
			except:
				pass
		for timer in self.timers:
			try:
				timer.cancel()
			except:
				pass
		if self.rejointimer:
			try:
				self.rejointimer.cancel()
			except:
				pass
			self.rejointimer = None
		if self.pingtimer:
			try:
				self.pingtimer.cancel()
			except:
				pass
			self.pingtimer = None

	def shutdown(self, loop):
		self.isshutdown = True
		self.disconnect('Shutting down')

	def handle_event(self, loop, module, sender, protocol, event, data):
		if event != 'IRC_SENDCMD':
			return

		if not 'command' in data:
			self.log.warning('Event ' + event + ' missing command to execute')
			return

		self._send(data['command'])

	#RPL_ISUPPORT
	def m_005(self, msg):
		for isup in msg['params'][1:-1]:
			m = self.n005kv.match(isup)
			if not m:
				self.log.warning('Numeric 005 option failed parsing: ' + isup)
				continue

			key = m.group('key')
			value = m.group('value')

			if key == 'CHANTYPES':
				if value:
					self.chantypes = value
			elif key == 'PREFIX':
				self.log.debug(str(key))
				self.log.debug(str(value))
				if value:
					pfxparts = value.split(')')
					self.chanusrpfx = pfxparts[1]
					self.chanusrpfxmodes = pfxparts[0][1:]
			elif key == 'CHANMODES':
				if value:
					self.chanmodes = value.split(',')
			elif key == 'WHOX':
				self.haswhox = True

		if self.hasperformed:
			return

		for chan in self.chans:
			self.chans[chan]['joined'] = False

		self._joinchans()

		self.hasperformed = True

	#RPL_NAMREPLY
	def m_353(self, msg):
		chan = msg['params'][-2].lower()
		usrlist = msg['params'][-1]

		if chan in self.chans:
			users = usrlist.split(' ')

			for user in users:
				pfx = ''
				pfxm = ''

				for c in range(0, len(user)):
					if not user[c] in self.chanusrpfx:
						pfx = user[:c]
						user = user[c:]
						break

				nuh = self._parse_nuh(user)

				for p in pfx:
					pfxm = pfxm + self.chanusrpfxmodes[self.chanusrpfx.index(p)]

				if nuh['name'].lower() in self.chans[chan]['users']:
					self.chans[chan]['users'][nuh['name'].lower()]['status'] = pfxm
				else:
					self.chans[chan]['users'][nuh['name'].lower()] = {'nick': nuh['name'], 'status': pfxm, 'account': ''}

	#RPL_WHOSPCRPL:
	def m_354(self, msg):
		tag = msg['params'][1]

		if tag != '696':
			return

		who = msg['params'][2].lower()
		account = msg['params'][3]

		if account == '0':
			account = ''

		for chan in self.chans:
			if who in self.chans[chan]['users']:
				self.chans[chan]['users'][who]['account'] = account

	#RPL_ENDOFNAMES
	def m_366(self, msg):
		if self.haswhox:
			chan = msg['params'][-2]
			if chan.lower() in self.chans:
				self._send('WHO', chan, '%tna,696')

	#ERR_NICKNAMEINUSE
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

	def m_account(self, msg):
		who = msg['source']['name'].lower()
		account = msg['params'][0]

		if account == '*':
			account = ''

		for chan in self.chans:
			if who in self.chans[chan]['users']:
				self.chans[chan]['users'][who]['account'] = account

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

	def m_mode(self, msg):
		target = msg['params'][0]
		modes = msg['params'][1]
		nextparam = 2

		if target.lower() in self.chans:
			add = True
			for m in modes:
				if m == '+':
					add = True
				elif m == '-':
					add = False

				if m in self.chanusrpfxmodes:
					who = msg['params'][nextparam]
					if who.lower() in self.chans[target.lower()]['users']:
						if add:
							if not m in self.chans[target.lower()]['users'][who.lower()]['status']:
								self.chans[target.lower()]['users'][who.lower()]['status'] = self.chans[target.lower()]['users'][who.lower()]['status'] + m
						else:
							self.chans[target.lower()]['users'][who.lower()]['status'] = self.chans[target.lower()]['users'][who.lower()]['status'].replace(m, '')
					nextparam = nextparam + 1
				elif m in self.chanmodes[0]:
					nextparam = nextparam + 1
				elif m in self.chanmodes[1]:
					nextparam = nextparam + 1
				elif m in self.chanmodes[2] and add:
					nextparam = nextparam + 1

	def m_join(self, msg):
		chan = msg['params'][0].lower()
		account = ''
		who = msg['source']['name'].lower()

		if len(msg['params']) > 1:
			if msg['params'][1] != '*':
				account = msg['params'][1]

		if who == self.user['nick'].lower():
			if chan in self.chans:
				log.info('Joined channel ' + self.chans[chan]['name'])
				self.chans[chan]['joined'] = True
				self.chans[chan]['users'] = {}
				try:
					self.chans[chan]['jointimer'].cancel()
				except:
					pass
				self.chans[chan]['jointimer'] = None

		if chan in self.chans:
			self.chans[chan]['users'][who] = {'nick': msg['source']['name'], 'status': '', 'account': account}
			log.debug('Added user ' + who + ' to channel ' + chan + ': ' + str(self.chans[chan]['users'][who]))

	def m_kick(self, msg):
		chan = msg['params'][0].lower()
		victim = msg['params'][1].lower()

		if victim == self.user['nick'].lower():
			if chan in self.chans:
				log.info('Kicked from channel ' + self.chans[chan]['name'])
				self.chans[chan]['joined'] = False

			self.chans[chan]['jointimer'] = self.loop.call_later(self.rejoindelay, self._joinchan, chan)
		else:
			if chan in self.chans:
				del self.chans[chan]['users'][victim]

	def m_nick(self, msg):
		who = msg['source']['name'].lower()
		newnick = msg['params'][0]

		if who == self.user['nick'].lower():
			self.user['nick'] = newnick
			self.user['newnick'] = newnick
			log.info('Changed nick to ' + newnick)

		for chan in self.chans:
			if who in self.chans[chan]['users']:
				self.chans[chan]['users'][newnick.lower()] = self.chans[chan]['users'][who]
				self.chans[chan]['users'][newnick.lower()]['nick'] = newnick
				del self.chans[chan]['users'][who]

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
		else:
			if chan in self.chans:
				del self.chans[chan]['users'][who]

	def m_quit(self, msg):
		who = msg['source']['name'].lower()

		if who == self.user['nick'].lower():
			self.log.debug('I Quit! *Storms off in a huff*')
			return
		else:
			for chan in self.chans:
				if who in self.chans[chan]['users']:
					del self.chans[chan]['users'][who]

	def m_kill(self, msg):
		victim = msg['params'][0]

		if victim == self.user['nick'].lower():
			self.log.debug('Death comes for me!')
			return
		else:
			for chan in self.chans:
				if victim in self.chans[chan]['users']:
					del self.chans[chan]['users'][victim.lower()]

	def m_ping(self, msg):
		self._send('PONG', msg['params'][0])

	def m_privmsg(self, msg):
		text = msg['params'][-1]
		target = msg['params'][0]
		if len(text) > 0:
			if target.lower() in self.chans:
				statusmodes = ''
				if msg['source']['name'].lower() in self.chans[target.lower()]['users']:
					statusmodes = self.chans[target.lower()]['users'][msg['source']['name'].lower()]['status']

				src = msg['source'].copy()
				src['modes'] = statusmodes

				textparts = text.split(' ')

				if textparts[0] == '?ops':
					if self._isop(msg['source']['name'], target):
						ops = []
						for user in self.chans[target.lower()]['users']:
							if self._isop(user, target):
								ops.append(self.chans[target.lower()]['users'][user]['nick'])

						self._send('PRIVMSG', target, 'Ops: ' + ', '.join(ops))
				elif textparts[0] == '?account':
					if self._isop(msg['source']['name'], target):
						if len(textparts) > 1:
							who = textparts[1]
							if not who.lower() in self.chans[target.lower()]['users']:
								self._send('PRIVMSG', target, 'There is no user named ' + who)
							else:
								account = self.chans[target.lower()]['users'][who.lower()]['account']
								if account == '':
									self._send('PRIVMSG', target, 'I do not know what account ' + who + ' is logged in as')
								else:
									self._send('PRIVMSG', target, who + ' is logged in as ' + account)

				if self.chans[target]['joined']:
					event = 'CHANNEL_MESSAGE'
					if text[:7] == '\x01ACTION':
						if len(text) > 8:
							text = text[8:]
							if text[-1] == '\x01':
								text = text[:-1]
							event = 'CHANNEL_ACTION'
					evt = {'name': msg['source']['name'], 'target': target.lower(), 'message': text, 'source': src}
					self.log.debug('Event "' + event + '": ' + str(evt))

					_modules.send_event(self.loop, self.module, self.config['name'], 'irc', event, evt)
			else:
				vtext = text
				if vtext[0] == '\x01':
					vtext = vtext[1:]
					if len(vtext) > 0:
						if vtext[-1] == '\x01':
							vtext = vtext[:-1]
					if len(vtext) > 0:
						words = vtext.split(' ')
						if words[0].upper() == 'VERSION':
							self._send('NOTICE', msg['source']['name'], '\x01VERSION RelayBot 2.0 https://github.com/jobe1986/relaybot\x01')

				if not self._ischannel(target):
					event = 'USER_MESSAGE'
					if text[:7] == '\x01ACTION':
						if len(text) > 8:
							text = text[8:]
							if text[-1] == '\x01':
								text = text[:-1]
							event = 'USER_ACTION'
					evt = {'name': msg['source']['name'], 'target': target, 'message': text, 'source': msg['source']}
					self.log.debug('Event "' + event + '": ' + str(evt))

					_modules.send_event(self.loop, self.module, self.config['name'], 'irc', event, evt)

	def _resetping(self):
		self.pingcheck = True
		if self.pingtimer:
			try:
				self.pingtimer.cancel()
			except:
				pass
		self.pingtimer = self.loop.call_later(self.pingfrequency, self._doping)

	def _doping(self):
		if self.pingcheck:
			self._send('PING', 'CHECKCONN')
			self.pingcheck = False
			self.pingtimer = self.loop.call_later(self.pingfrequency, self._doping)
		else:
			self.disconnect('Ping Timeout')

	def _capend(self):
		self._send('CAP', 'END')
		self.capendhandle = None

	def _joinchans(self):
		self.log.debug('Checking channels to JOIN')
		self.rejointimer = None

		j = 0
		chans = []
		chank = {}
		for chan in self.chans:
			if self.chans[chan]['joined']:
				continue
			chan = self.chans[chan]

			if 'key' in chan:
				chank[chan['name']] = chan['key']
			else:
				chans.append(chan['name'])

			j = j + 1

		if j <= 0:
			return

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

		self.rejointimer = self.loop.call_later(self.rejoindelay, self._joinchans)

	def _joinchan(self, chan):
		if self.chans[chan]['joined']:
			return

		log.debug('Attempting to join channel ' + chan)

		if 'key' in self.chans[chan]:
			self._send('JOIN', chan, self.chans[chan]['key'])
		else:
			self._send('JOIN', chan)

		self.chans[chan]['jointimer'] = self.loop.call_later(self.rejoindelay, self._joinchan, chan)

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

	def _isop(self, nick, chan):
		if not chan.lower() in self.chans:
			return False
		if not nick.lower() in self.chans[chan.lower()]['users']:
			return False
		if 'o' in self.chans[chan.lower()]['users'][nick.lower()]['status']:
			return True
		return False

	def _ischannel(self, name):
		if len(name) < 1:
			return False
		if not name[0] in self.chantypes:
			return False
		return True

	def _parse_nuh(self, nuh):
		ret = {'full': nuh, 'name': '', 'ident': '', 'host': ''}

		val = nuh
		if val.find('@') >= 0:
			ret['host'] = val[val.find('@')+1:]
			val = val[:val.find('@')]
		if val.find('!') >= 0:
			ret['ident'] = val[val.find('!')+1:]
			val = val[:val.find('!')]
		ret['name'] = val

		return ret

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
