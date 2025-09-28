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
_modinstances = {}

# Module class prototype
class Module:
	def __init__(self, loop, module):
		self.loop = loop
		self.module = module # raw module loaded by importlib
		self.name = module.name
		self.log = _logging.log.getChild(self.__class__.__module__)
		return

	def readconfig(self, config):
		return

	def applyconfig(self):
		return

	def shutdown(self):
		return

# ModuleInstance class prototype
class ModuleInstance:
	def __init__(self, name, module):
		self.loop = module.loop
		self.module = module # instance of Module class
		self.name = name
		self.log = _logging.log.getChild(self.__class__.__module__).getChildObj(name)
		return

def _applyconfigmod(mod):
	_log.debug('Applying configuration for module ' + mod.name)
	mod.applyconfig()

def _shutdownmod(mod):
	_log.debug('Shutting down module ' + mod.name)
	mod.shutdown()

def _loadmod(name, loop):
	global _mods

	if name in _mods:
		_log.warning('Unable to load module ' + name + ': already loaded')
		return False

	try:
		m = importlib.import_module('modules.' + name)
		importlib.invalidate_caches()
		m.name = name

		if hasattr(m, 'Module'):
			o = m.Module(loop, m)
		else:
			_log.error('Unable to load module ' + name + ': missing Module class definition')
			return False
	except Exception as e:
		_log.error('Error loading module ' + name + ': ' + str(e))
		return False

	_mods[name] = o
	_modinstances[name] = {}
	_log.debug('Loaded module ' + name)
	return m

# Read config load modules
def readconfig(config, loop):
	global _mods

	modcfgs = config.findall('module')

	for mod in modcfgs:
		if not 'name' in mod.attrib:
			_log.warning('Missing name attribute for module')
			continue
		name = mod.attrib['name']

		m = _loadmod(name, loop)

	_log.debug('Modules loaded: ' + ', '.join(_mods.keys()))

	for name in _mods:
		m = _mods[name]
		if m != None:
			cfg = config.findall(name)
			m.readconfig(cfg)

	return True

# Find module by name
def getmodule(name):
	global _mods

	if name in _mods:
		return _mods[name]['object#']
	return None

# Loop through loaded modules and schedule task to apply their configs
def applyconfig(loop):
	global _mods

	for name in _mods:
		loop.call_soon(_applyconfigmod, _mods[name])

# loop through loaded modules and schedule task to shut them down
def shutdown(loop):
	global _mods

	for name in _mods:
		loop.call_soon(_shutdownmod, _mods[name])

# Find a module instance (instance of ModuleInstance class)
def findinstance(mod, name):
	global _modinstances

	if not mod in _modinstances:
		return None

	if not name in _modinstances[mod]:
		return None

	return _modinstances[mod][name]

# Register a module instance (instance of ModuleInstance class)
def registerinstance(inst):
	global _modinstances

	if not inst.module.name in _modinstances:
		_modinstances[inst.module.name] = {}

	if inst.name in _modinstances[inst.module.name]:
		_log.debug('Unable to register module instance "' + inst.module.name + '#' + inst.name + '": an instance with that name already exists')
		return False

	_modinstances[inst.module.name][inst.name] = inst
	_log.debug('Registered instance of module instance "' + inst.module.name + '#' + inst.name + '"')
	return True

# Unregister a module instance (instance of ModuleInstance class)
def unregisterinstance(inst):
	global _modinstances

	if not inst.module in _modinstances:
		_log.debug('Unable to unregister module instance "' + inst.module.name + '#' + inst.name + '": no such module loaded')
		return False

	if not inst.name in _modinstances[inst.module.name]:
		_log.debug('Unable to unregister module instance "' + inst.module.name + '#' + inst.name + '": no module instance with that name exists')
		return False

	del(_modinstances[inst.module.name][inst.name])
	_log.debug('Unregistered module instance "' + inst.module.name + '#' + inst.name + '"')
	return True