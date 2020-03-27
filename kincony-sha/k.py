#!/usr/bin/python
import getopt
import socket
import sys
import re
import time
import os
import subprocess

help_test = 'python3 k.py -i <index> -t <type>[on,off,get,test] && (python3 k.py -i <index> -t flush &)'
kcode = '255'
first_run = False
fix_every_time = False
lock_file_path = '/tmp/k_h.lock'
status_files_prfix = '/tmp/k_s_'

def send2K(address, action_type, index, debug):
	try:
		s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		s.connect(address)
	except:
		if debug:
			print("cannot connect socket")
		# os.remove(lock_file_path)
		sys.exit(8)	

	if first_run:
		s.sendto('RELAY-SCAN_DEVICE-NOW'.encode(), address)
		result = s.recv(1024).decode('utf-8')
		if debug:
			print("scan:" + result)

	if first_run or fix_every_time:
		s.sendto('RELAY-TEST-NOW'.encode(), address)
		result = s.recv(1024).decode('utf-8')
		if debug:
			print("test:" + result)

	if action_type == 'on' and index == 'all':
		command = 'RELAY-SET_ALL-' + kcode + ',255'
	elif action_type == 'off' and index == 'all':
		command = 'RELAY-SET_ALL-' + kcode + ',0'
	elif action_type == 'on':
		command = 'RELAY-SET-' + kcode + ',' + index + ',1'
	elif action_type == 'off':
		command = 'RELAY-SET-' + kcode + ',' + index + ',0'
	elif action_type == 'get':
		command = 'RELAY-READ-' + kcode + ',' + index
	elif action_type == 'test':
		command = 'RELAY-TEST-NOW'
	elif action_type == 'scan':
		command = 'RELAY-SCAN_DEVICE-NOW'
	elif action_type == 'error':
		command = 'zzz'
	else:
		print(help_test)
		s.close()
		sys.exit(2)

	s.sendto(command.encode(), address)
	result = s.recv(1024).decode('utf-8')

	s.close()

	if debug:
		print("request:" + command)
		print("response:" + result)

	return result

def send2KWithLock(address, action_type, index, debug):
	lock_not_created = True
	while lock_not_created:
		try:
			f = open(lock_file_path, 'x')
			f.close()
			f = open(lock_file_path, 'w')
			f.write(str(round(time.time()) + 5))
			f.close()
			lock_not_created = False
		except FileExistsError:
			if debug:
				print("connection busy, sleep")
			time.sleep(0.5)
			try:
				f = open(lock_file_path, 'r')
				lock_time_string = f.read()
				f.close()
				if int(lock_time_string) < time.time():
					if debug:
						print("drop old connection: " + lock_time_string)
					os.remove(lock_file_path)
			except:
				if debug:
					print("cannot read file")

	result = send2K(address, action_type, index, debug)

	os.remove(lock_file_path)

	return result

def setState(index, state, debug):
	path = status_files_prfix + index
	if state:
		try:
			f = open(path, 'x')
			f.close()
		except FileExistsError:
			if debug:
				print("file exists: " + path)
	else:
		try:
			os.remove(path)
		except FileNotFoundError:
			if debug:
				print("file not found: " + path)
	flush(index)

def getState(index):
	path = status_files_prfix + index
	return os.path.isfile(path)

def flush(index): 
	subprocess.Popen(['python3', os.path.realpath(__file__), '-i', str(index), '-t', 'flush'])	

def main(argv):
	default_ip = '192.168.1.103'
	index = 0
	action_type = ''
	debug = False

	try:
		opts, args = getopt.getopt(argv, "hi:t:d:", ["index=", "type=", "debug="])
	except getopt.GetoptError:
		print(help_test)
		sys.exit(2)
	for opt, arg in opts:
		if opt == '-h':
			print(help_test)
			sys.exit()
		elif opt in ("-i", "--index"):
			index = arg
		elif opt in ("-t", "--type"):
			action_type = arg
		elif opt in ("--ip"):
			default_ip = arg
		elif opt in ("-d", "--debug"):
			debug = True
	address = (default_ip, 4196)

	if action_type == 'on':
		setState(index, True, debug)
	elif action_type == 'off':
		setState(index, False, debug)
	elif action_type == 'get':
		print(getState(index) and '1' or '0')
	elif action_type == 'flush':
		action_type = getState(index) and 'on' or 'off'
		if debug:
			print("action_type changed to " + action_type)
		result = send2KWithLock(address, action_type, index, debug)
		if action_type == 'on':
			x = re.match("RELAY-SET-\\d+,\\d+,(\\d+),OK", result)
			if x.group(1) != "1":
				if debug:
					print("exit 5")
				sys.exit(5)
		elif action_type == 'off':
			x = re.match("RELAY-SET-\\d+,\\d+,(\\d+),OK", result)
			if x.group(1) != "0":
				if debug:
					print("exit 6")
				sys.exit(6)
		elif action_type == 'get':
			x = re.match("RELAY-READ-\\d+,\\d+,(\\d+),OK", result)
			print(x.group(1))

	if debug:
		print("exit OK")

if __name__ == "__main__":
	main(sys.argv[1:])
