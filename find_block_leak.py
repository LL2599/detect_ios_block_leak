#! /usr/bin/python
# -*- coding:utf-8 -*-

import os
import time
import glob
import re
from sys import argv
import hh_print
from optparse import OptionParser
import linecache

def find_sutiable_files(path):
	command = 'ag --objc -l "\^" %s' % (path)
	header_paths = os.popen(command).readlines()
	header_paths = map(lambda x : x.strip(), header_paths)
	filtered_files = filter(lambda x : x[-2:] == ".m", header_paths)
	# hh_print.print_array(filtered_files)
	return filtered_files

def block_locations_in_file(file_path):
	command = 'ag "\^" %s' % (file_path)
	header_paths = os.popen(command).readlines()
	locations = map(lambda x : (int(x.split(':')[0]) - 1), header_paths)
	return locations

def find_all_indexs(line, start_index, text):
	if len(line) == 0 or len(text) == 0:
		return []
	indexs = []
	pos = start_index - 1;
	while True:
		pos = line.find(text, pos + 1)
		if pos == -1:
			break;
		indexs.append(pos)
	return indexs

def check_has_self_exist(current_line, start_index):
	if start_index > 0:
		current_line = current_line[start_index:len(current_line)]
	if current_line.find('[self ') != -1:
		return True
	if re.match(r'.*\Wself\.', current_line) != None:
		return True
	if re.match(r'.*[^A-Za-z0-9_"]_[A-Za-z0-9].*', current_line) != None:
		if current_line.find('->_') == -1:
			return True
	return False

def is_start_line_legal(first_line):
	first_line = first_line.strip()
	if first_line.find("enumerateObjectsUsingBlock:^") != -1 or \
		first_line.find("[UIView animate") != -1 or \
		first_line.find(" mas_") != -1 or \
		first_line.find("completion:^(BOOL finished)") != -1 or \
		first_line.find("dispatch_after(") != -1 or \
		first_line.find(" performBatchUpdates:") != -1 or \
		first_line.find("dispatch_async(dispatch_get_main_queue()") != -1 or \
		first_line.find("dispatch_once(") != -1 or \
		first_line.find("animations:^") != -1 or \
		first_line.find(" filteredArrayUsingPredicate:") != -1 or \
		first_line.find("dispatch_apply(") != -1 or \
		first_line.find("dispatch_sync(") != -1 or \
		first_line[0:2] == "//" or \
		first_line[0:3] == "- (" or \
		first_line[0:3] == "+ (":
		return False
	return True

# find whether current code is in static method
def is_static_method_for_current_line(start_index, lines):
	index = start_index
	while True:
		if index < 0:
			return False
		current_line = lines[index].strip()
		index = index - 1
		if len(current_line) < 4 or current_line[0:2] == "//":
			continue
		if current_line[0:3] == "- (":
			return False
		if current_line[0:3] == "+ (":
			return True
	return False

def check_single_file(file_path):
	lines = linecache.getlines(file_path)
	locations = block_locations_in_file(file_path)
	error_locations = []
	# print file_path
	for block_start_location in locations:
		# hh_print.print_color_string("----------------location %d" % (block_start_location))
		first_line = lines[block_start_location]
		if not is_start_line_legal(first_line):
			continue
		pos = first_line.find('^')
		index = pos + 1
		if first_line[pos-1:pos] == "(":
			pos = -1
		pos_next = first_line.find('^', index)
		if pos_next != -1:
			if first_line[pos_next-1:pos_next] != "(":
				pos = pos_next
		# print "pos %s" % pos
		if pos == -1:
			continue
		if is_static_method_for_current_line(block_start_location, lines):
			continue
		temp = first_line.find('{', pos)
		if temp != -1:
			pos = temp
		left_count = 0
		right_count = 0
		line_index = block_start_location
		has_strong_self = False
		has_self_exist = False
		while True:
			if line_index >= len(lines):
				break
			start_index = 0
			if line_index == block_start_location:
				start_index = pos
			current_line = lines[line_index]
			line_index = line_index + 1
			if current_line.strip()[0:2] == "//":
				continue
			# hh_print.print_color_string(current_line)
			left_indexs = find_all_indexs(current_line, start_index, '{')
			right_indexs = find_all_indexs(current_line, start_index, '}')
			left_count += len(left_indexs)
			right_count += len(right_indexs)
			# hh_print.print_color_string("left:%s, right: %s" % (left_count, right_count), "red")
			if has_strong_self == False:
				has_strong_self = current_line.find('strongify(self)', start_index) != -1
			if has_self_exist == False and check_has_self_exist(current_line, start_index):
				has_self_exist = True
			if not has_strong_self and has_self_exist:
				break
			if left_count > 0 and left_count == right_count:
				break
		if not has_strong_self and has_self_exist:
			error_locations.append(block_start_location + 1)
	if len(error_locations):
		hh_print.print_color_string("Maybe Leak in file: %s" % file_path, "cyan")
		print error_locations
	# else:
	# 	hh_print.print_color_string("No leak: %s" % (file_path))
	linecache.clearcache()

if __name__ == '__main__':
    if len(argv) < 2:
    	hh_print.print_color_string("Parameters error: Usage: python %s search_path" % (__file__), "b_red")
    	exit(0)
    search_path = argv[1]
    files = find_sutiable_files(search_path)
    progress = 0
    total = len(files)
    for file_path in files:
    	check_single_file(file_path)
    	hh_print.print_progress(progress, total)
    	progress = progress + 1
    # current_line = '       NSArray *itemArray = [subview valueForKeyPath:@"_viewData.item"];'
    # group = re.match(r'.*[^A-Za-z0-9_"]_[A-Za-z0-9].*', current_line)
    # if group == None:
    # 	print "None..."
    # else:
    # 	print group.group()
    