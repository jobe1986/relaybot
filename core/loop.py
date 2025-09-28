# -*- coding: utf-8 -*-

# RelayBot - Simple Relay Service, core/loop.py
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

import asyncio

_log = _logging.log.getChild(__name__)

def init_loop(args):
	global _log

	_log.info('Initializing main loop ready for use')

	# Create event loop
	loop = asyncio.new_event_loop()
	if args.asynciodebug:
		loop.set_debug(True)
	asyncio.set_event_loop(loop)

	return loop

async def shutdown_loop(loop):
	global _log

	_log.info('Starting graceful shutdown...')

	# Get all pending tasks (excluding the one running this shutdown code)
	tasks = []
	for t in asyncio.all_tasks(loop=loop):
		# Check if the task is NOT the current task (the shutdown_loop itself)
		if t is not current_task:
			tasks.append(t)

	for task in tasks:
		task.cancel()

	try:
		await asyncio.gather(*tasks, return_exceptions=True)
		_log.info('All tasks cancelled and cleaned up.')
	except Exception:
		pass

	if loop.is_running():
		loop.stop()
