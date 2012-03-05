#  framework/interface.py
#  
#  Copyright 2011 Spencer J. McIntyre <SMcIntyre [at] SecureState [dot] net>
#  
#  This program is free software; you can redistribute it and/or modify
#  it under the terms of the GNU General Public License as published by
#  the Free Software Foundation; either version 2 of the License, or
#  (at your option) any later version.
#  
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.

import os
import cmd
import sys
import code
import logging
import traceback
from random import randint
from c1218.errors import *
from framework.options import Options
from framework.core import Framework, FrameworkConfigurationError

__version__ = '0.0.3'

class OverrideCmd(cmd.Cmd, object):														# OverrideCmd class is meant to override methods from cmd.Cmd so they can be imported into the CoriInterpreter class and the ActionEditorBase class.
	__doc__ = 'OverrideCmd class is meant to override methods from cmd.Cmd so they can\nbe imported into the base interpreter class.'
	def __init__(self, debugging = False):
		cmd.Cmd.__init__(self)
		self.__hidden_commands__ = ['EOF']
		self.__package__ = '.'.join(self.__module__.split('.')[:-1])
	
	def cmdloop(self):
		try:
			super(OverrideCmd, self).cmdloop()
		except KeyboardInterrupt:
			self.do_EOF('')
			return
	
	def get_names(self):												
		commands = super(OverrideCmd, self).get_names()
		for name in self.__hidden_commands__:
			if 'do_' + name in commands:
				commands.remove('do_' + name)
		return commands
	
	def emptyline(self): 					# Don't do anything on a blank line being passed
		pass								#stupid repeats are annoying
	
	def help_help(self): 					# Get help out of the undocumented section, stupid python
		self.do_help('')
		
	def precmd(self, line):					# use this to allow using '?' after the command for help
		tmpLine = line.split()
		if len(tmpLine) <= 1:
			return line
		if tmpLine[1] == '?':
			self.do_help(tmpLine[0])
			return ''
		else:
			return line

	def do_exit(self, args):
		return True
	
	def do_EOF(self, args):
		"""Exit The Interpreter"""
		print ''
		return self.do_exit('')

class InteractiveInterpreter(OverrideCmd):													# The core interpreter for the console
	__doc__ = 'The core interpreter for the program'
	__name__ = 'termineter'
	prompt = __name__ + ' > '
	ruler = '+'
	doc_header = 'Type help <command> For Information\nList Of Available Commands:'
	
	@property
	def intro(self):
		intro = os.linesep
		intro += '   ______              _          __         ' + os.linesep
		intro += '  /_  __/__ ______ _  (_)__  ___ / /____ ____' + os.linesep
		intro += '   / / / -_) __/  \' \/ / _ \/ -_) __/ -_) __/' + os.linesep
		intro += '  /_/  \__/_/ /_/_/_/_/_//_/\__/\__/\__/_/   ' + os.linesep
		intro += os.linesep
		intro += '  <[ ' + self.__name__ + ' v' + __version__ + os.linesep
		intro += '  <[ loaded modules: ' + str(len(self.frmwk.modules)) + os.linesep
		return intro
	
	@property
	def prompt(self):
		if self.frmwk.current_module:
			if self.frmwk.use_colors:
				return self.__name__ + ' (\033[1;33m' + self.frmwk.current_module + '\033[1;m) > '
			else:
				return self.__name__ + ' (' + self.frmwk.current_module + ') > '
		else:
			return self.__name__ + ' > '
	
	def __init__(self, check_rc_file = True):
		OverrideCmd.__init__(self)										# this adds the code from the cmd.Cmd.__init__ as inherited by OverrideCmd so it's appended to instead of overwritten
		self.__hidden_commands__.append('exploit')
		self.logger = logging.getLogger(self.__package__ + '.interpreter')
		self.frmwk = Framework()
		self.print_error = self.frmwk.print_error
		self.print_good = self.frmwk.print_good
		self.print_line = self.frmwk.print_line
		self.print_status = self.frmwk.print_status
		
		if check_rc_file:
			user_rc_file = None
			if check_rc_file == True:
				user_rc_file = self.frmwk.directories.user_data + 'console.rc'
			elif isinstance(check_rc_file, str):
				user_rc_file = check_rc_file
			if user_rc_file:
				if os.path.isfile(user_rc_file):
					self.logger.info('processing "' + user_rc_file + '" for commands')
					self.print_status('Processing ' + user_rc_file + ' for commands')
					for line in open(user_rc_file, 'r'):
						self.onecmd(line.strip())
				elif isinstance(check_rc_file, str):
					self.logger.error('invalid rc file: ' + user_rc_file)
					self.print_error('Invalid rc file: ' + user_rc_file)
	
	def do_back(self, args):
		"""Stop using a module"""
		self.frmwk.current_module = None
	
	def do_banner(self, args):
		"""Print the banner"""
		self.print_line(self.intro)
	
	def do_connect(self, args):
		"""Connect the serial interface"""
		if self.frmwk.is_serial_connected():
			self.print_status('Already connected')
			return
		missing_options = self.frmwk.options.getMissingOptions()
		if missing_options:
			self.print_error('The following options must be set: ' + ', '.join(missing_options))
			return
		if self.frmwk.serial_connect():
			self.print_good('Successfully connected and the device is responding')
		else:
			self.print_error('An error occured while opening the serial interface')
	
	def do_disconnect(self, args):
		"""Disconnect the serial interface"""
		args = args.split(' ')
		if not self.frmwk.is_serial_connected():
			self.print_error('Not connected')
			return
		result = self.frmwk.serial_disconnect()
		if result:
			self.print_good('Successfully disconnected')
		else:
			self.print_error('An error occured while closing the serial interface')
		if args[0] == '-r':
			missing_options = self.frmwk.options.getMissingOptions()
			if missing_options:
				self.print_error('The following options must be set: ' + ', '.join(missing_options))
				return
			if self.frmwk.serial_connect():
				self.print_good('Successfully reconnected and the device is responding')
			else:
				self.print_error('An error occured while reopening the serial interface')
	
	def do_exit(self, args):
		"""Exit The Interpreter"""
		QUOTES = [	'I\'ll be back.',
					'Hasta la vista, baby.',
					'Come with me if you want to live.',
					'Where\'s John Connor?'
					]
		self.print_status(QUOTES[randint(0, (len(QUOTES) - 1))])
		self.logger.info('received exit command, now exiting')
		return True
	
	def do_exploit(self, args):
		"""Run the currently selected module"""
		self.do_run(args)
	
	def do_help(self, args):
		super(InteractiveInterpreter, self).do_help(args)
		self.print_line('')
	
	def do_logging(self, args):
		"""Set and show logging options"""
		args = args.split(' ')
		if args[0] == '':
			args[0] = 'show'
		elif not args[0] in ['show', 'set', '-h']:
			self.print_error('Invalid parameter "' + args[0] + '", use "logging -h" for more information')
			return
		if args[0] == '-h':
			self.print_status('Valid parameters for the "logging" command are: show, set')
			return
		elif args[0] == 'show':
			loglvl = logging.getLogger('').getEffectiveLevel()
			self.print_status('Effective logging level is: ' + ({10:'DEBUG', 20:'INFO', 30:'WARNING', 40:'ERROR', 50:'CRITICAL'}.get(loglvl) or 'UNKNOWN'))
		elif args[0] == 'set':
			if len(args) == 1:
				self.print_error('Missing log level, valid options are: debug, info, warning, error, critical')
				return
			if args[1].upper() in ['DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL']:
				logging.getLogger('').setLevel(getattr(logging, args[1].upper()))
				self.print_good('Successfully changed the logging level')
			else:
				self.print_error('Missing log level, valid options are: debug, info, warning, error, critical')
	
	def complete_logging(self, text, line, begidx, endidx):
		return [i for i in ['set', 'show'] if i.startswith(text)]
	
	def do_info(self, args):
		"""Show module information"""
		args = args.split(' ')
		if args[0] == '' and self.frmwk.current_module == None:
			self.print_error('Must select module to show information')
			return
		if args[0]:
			if args[0] in self.frmwk.modules.keys():
				module = self.frmwk.modules[args[0]]
			else:
				self.print_error('Invalid module name')
				return
		else:
			module = self.frmwk.modules[self.frmwk.current_module]
		self.print_line('')
		self.print_line('     Name: ' + module.name)
		if len(module.author) == 1:
			self.print_line('   Author: ' + module.author[0])
		elif len(module.author) > 1:
			self.print_line('  Authors: ' + module.author[0])
			for additional_author in module.author[1:]:
				self.print_line('               ' + additional_author)
		self.print_line('  Version: ' + str(module.version))
		self.print_line('')
		self.print_line('Basic Options: ')
		longest_name = 16
		longest_value = 10
		for option_name, option_def in module.options.items():
			longest_name = max(longest_name, len(option_name))
			longest_value = max(longest_value, len(str(module.options[option_name])))
		fmt_string = "  {0:<" + str(longest_name) + "} {1:<" + str(longest_value) + "} {2}"
		self.print_line(fmt_string.format('Name', 'Value', 'Description'))
		self.print_line(fmt_string.format('----', '-----', '------------'))
		for option_name in module.options.keys():
			option_value = module.options[option_name]
			if option_value == None:
				option_value = ''
			option_desc = module.options.getOptionHelp(option_name)
			self.print_line(fmt_string.format(option_name, str(option_value), option_desc))
		self.print_line('')
		self.print_line('Description:')
		description_text = module.detailed_description.split()
		y, x = 0, 0
		while y < len(description_text):
			if len(' '.join(description_text[x:y])) <= 58:
				y += 1
			else:
				self.print_line('  ' + ' '.join(description_text[x:(y - 1)]))
				x = y - 1
				y += 1
		self.print_line('  ' + ' '.join(description_text[x:y]))
		self.print_line('')
	
	def complete_info(self, text, line, begidx, endidx):
		return [i for i in self.frmwk.modules.keys() if i.startswith(text)]
	
	def do_ipy(self, args):
		"""Start an interactive Python interpreter"""
		vars = {'frmwk':self.frmwk, '__version__':__version__}
		banner = 'The Framework Instance Is In The Variable \'frmwk\'' + os.linesep
		if self.frmwk.serial_connection != None:
			vars['conn'] = self.frmwk.serial_connection
			banner = banner + 'The Connection Instance Is In The Variable \'conn\'' + os.linesep
		pyconsole = code.InteractiveConsole(vars)
		
		savestdin = os.dup(sys.stdin.fileno())
		savestdout = os.dup(sys.stdout.fileno())
		savestderr = os.dup(sys.stderr.fileno())
		try:
			pyconsole.interact(banner)
		except SystemExit:
			sys.stdin = os.fdopen(savestdin, 'r', 0)
			sys.stdout = os.fdopen(savestdout, 'w', 0)
			sys.stderr = os.fdopen(savestderr, 'w', 0)
	
	def do_reload(self, args):
		"""Reload a module in to the framework"""
		args = args.split(' ')
		if args[0] == '':
			if self.frmwk.current_module:
				module_name = self.frmwk.current_module
			else:
				self.print_error('Must \'use\' module first')
				return
		elif not args[0] in self.frmwk.modules.keys():
			self.print_error('Invalid Module Selected.')
			return
		else:
			module_name = args[0]
		self.frmwk.reload_module(module_name)
		self.print_status('Successfully reloaded module: ' + module_name)
	
	def complete_reload(self, text, line, begidx, endidx):
		return [i for i in self.frmwk.modules.keys() if i.startswith(text)]
		
	def do_run(self, args):
		"""Run the currently selected module"""
		args = args.split(' ')
		old_module = None
		if args[0] in self.frmwk.modules.keys():
			old_module = self.frmwk.current_module
			self.frmwk.current_module = args[0]
			if len(args) > 1:
				del(args[0])
			else:
				args[0] = ''
		if self.frmwk.current_module == None:
			self.print_error('Must \'use\' module first')
			return
		module_name = self.frmwk.current_module
		module = self.frmwk.modules[module_name]
		missing_options = self.frmwk.options.getMissingOptions()
		missing_options.extend(module.options.getMissingOptions())
		if missing_options:
			self.print_error('The following options must be set: ' + ', '.join(missing_options))
			return
		del missing_options
		if not self.frmwk.is_serial_connected():
			if self.frmwk.serial_connect():
				self.print_good('Successfully connected')
			else:
				self.print_error('An error occured while opening the serial interface')
				return
		self.logger.info('running module: ' + module_name)
		try:
			module.run(self.frmwk, args)
		except KeyboardInterrupt:
			try:
				self.frmwk.serial_connection.stop()
			except Exception as error:
				self.logger.error('caught ' + error.__class__.__name__ + ': ' + str(error))
				self.print_error('Caught ' + error.__class__.__name__ + ': ' + str(error))
			self.print_line('')
		except Exception as error:
			[ self.print_line(x) for x in traceback.format_exc().split(os.linesep) ]
			self.logger.error('caught ' + error.__class__.__name__ + ': ' + str(error))
			self.print_error('Caught ' + error.__class__.__name__ + ': ' + str(error))
			old_module = None
		if old_module:
			self.frmwk.current_module = old_module
	
	def complete_run(self, text, line, begidx, endidx):
		return [i for i in self.frmwk.modules.keys() if i.startswith(text)]
	
	def do_set(self, args):
		"""Set an option, usage: set [option] [value]"""
		args = args.split(' ')
		if len(args) < 2:
			self.print_error('set: [option] [value]')
			return
		name = args[0].upper()
		value = ' '.join(args[1:])
		
		if self.frmwk.current_module:
			options = self.frmwk.modules[self.frmwk.current_module].options
			advanced_options = self.frmwk.modules[self.frmwk.current_module].advanced_options
		else:
			options = self.frmwk.options
			advanced_options = self.frmwk.advanced_options
		if name in options:
			try:
				options.setOption(name, value)
				self.print_line(name + ' => ' + value)
			except TypeError:
				self.print_error('Invalid data type')
			return
		elif name in advanced_options:
			try:
				advanced_options.setOption(name, value)
				self.print_line(name + ' => ' + value)
			except TypeError:
				self.print_error('Invalid data type')
			return
		self.print_error('Unknown variable name')
	
	def complete_set(self, text, line, begidx, endidx):
		if self.frmwk.current_module:
			return [i for i in self.frmwk.modules[self.frmwk.current_module].options.keys() if i.startswith(text.upper())]
		else:
			return [i for i in self.frmwk.options.keys() if i.startswith(text.upper())]
	
	def do_show(self, args):
		"""Valid parameters for the "show" command are: modules, options"""
		args = args.split(' ')
		if args[0] == '':
			args[0] = 'options'
		elif not args[0] in ['advanced', 'modules', 'options', '-h']:
			self.print_error('Invalid parameter "' + args[0] + '", use "show -h" for more information')
			return
		if args[0] == 'modules':
			self.print_line('')
			self.print_line('Modules' + os.linesep + '=======')
			self.print_line('')
			longest_name = 18
			for module_name in self.frmwk.modules.keys():
				longest_name = max(longest_name, len(module_name))
			fmt_string = "  {0:" + str(longest_name) + "} {1}"
			self.print_line(fmt_string.format('Name', 'Description'))
			self.print_line(fmt_string.format('----', '-----------'))
			module_names = self.frmwk.modules.keys()
			module_names.sort()
			for module_name in module_names:
				module_obj = self.frmwk.modules[module_name]
				self.print_line(fmt_string.format(module_name, module_obj.description))
			self.print_line('')
			return
		elif args[0] == 'options' or args[0] == 'advanced':
			if self.frmwk.current_module and args[0] == 'options':
				options = self.frmwk.modules[self.frmwk.current_module].options
				self.print_line('')
				self.print_line('Module Options' + os.linesep + '==============')
				self.print_line('')
			if self.frmwk.current_module and args[0] == 'advanced':
				options = self.frmwk.modules[self.frmwk.current_module].advanced_options
				self.print_line('')
				self.print_line('Advanced Module Options' + os.linesep + '=======================')
				self.print_line('')
			elif self.frmwk.current_module == None and args[0] == 'options':
				options = self.frmwk.options
				self.print_line('')
				self.print_line('Framework Options' + os.linesep + '=================')
				self.print_line('')
			elif self.frmwk.current_module == None and args[0] == 'advanced':
				options = self.frmwk.advanced_options
				self.print_line('')
				self.print_line('Advanced Framework Options' + os.linesep + '==========================')
				self.print_line('')
			longest_name = 16
			longest_value = 10
			for option_name, option_def in options.items():
				longest_name = max(longest_name, len(option_name))
				longest_value = max(longest_value, len(str(options[option_name])))
			fmt_string = "  {0:<" + str(longest_name) + "} {1:<" + str(longest_value) + "} {2}"
			
			self.print_line(fmt_string.format('Name', 'Value', 'Description'))
			self.print_line(fmt_string.format('----', '-----', '------------'))
			for option_name in options.keys():
				option_value = options[option_name]
				if option_value == None:
					option_value = ''
				option_desc = options.getOptionHelp(option_name)
				self.print_line(fmt_string.format(option_name, str(option_value), option_desc))
			self.print_line('')
		elif args[0] == '-h':
			self.print_status('Valid parameters for the "show" command are: modules, options')
	
	def complete_show(self, text, line, begidx, endidx):
		return [i for i in ['advanced', 'modules', 'options'] if i.startswith(text)]
	
	def do_use(self, args):
		"""Select a module to use"""
		args = args.split(' ')
		if args[0] in self.frmwk.modules.keys():
			self.frmwk.current_module = args[0]
		else:
			self.logger.error('failed to load module: ' + args[0])
			self.print_error('Failed to load module: ' + args[0])
	
	def complete_use(self, text, line, begidx, endidx):
		return [i for i in self.frmwk.modules.keys() if i.startswith(text)]