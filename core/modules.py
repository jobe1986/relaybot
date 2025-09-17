# -*- coding: utf-8 -*-

# RelayBot - Simple Relay Service, core/modules.py
#
# Copyright (C) 2025 Matthew Beeching
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
import importlib

_log = _logging.log.getChild(__name__)

_mods = {}

def loadmod(name):
	global _mods

	if name in _mods:
		_log.warning('Unable to load module ' + name + ': already loaded')
		return False

	try:
		m = importlib.import_module('modules.' + name)
		importlib.invalidate_caches()
		m.name = name
	except Exception as e:
		_log.error('Error loading module ' + name + ': ' + str(e))
		return False

	_mods[name] = m
	_log.debug('Loaded module ' + name)
	return m

def loadconfig(config):
	global _mods

	modcfgs = config.findall('module')

	for mod in modcfgs:
		if not 'name' in mod.attrib:
			_log.warning('Missing name attribute for module')
			continue
		name = mod.attrib['name']

		m = loadmod(name)

	_log.debug('Modules loaded: ' + ', '.join(_mods.keys()))

	for name in _mods:
		m = _mods[name]
		if m != None:
			if hasattr(m, 'loadconfig'):
				cfg = config.findall(name)
				m.loadconfig(cfg, m)

	return True

def getmodule(name):
	global _mods

	if name in _mods:
		return _mods[name]
	return None

def applyconfig(loop):
	global _mods

	for name in _mods:
		if hasattr(_mods[name], 'applyconfig'):
			_log.debug('Applying configuration for module ' + name)
			_mods[name].applyconfig(loop, _mods[name])

def shutdown(loop):
	global _mods
	for name in _mods:
		if hasattr(_mods[name], 'shutdown'):
			_log.debug('Shutting down module ' + name)
			_mods[name].shutdown(loop)
