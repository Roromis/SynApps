#!/usr/bin/python2
# -*- coding: utf-8 -*-

from ConfigParser import RawConfigParser, NoSectionError, NoOptionError
from StringIO import StringIO
import codecs

class ConfigParser(RawConfigParser):
    def get(self, section, option, *args):
        if len(args) > 0:
            try:
                return RawConfigParser.get(self, section, option)
            except (NoSectionError, NoOptionError):
                return args[0]
        else:
            return RawConfigParser.get(self, section, option)

    def getboolean(self, section, option, *args):
        if len(args) > 0:
            try:
                return RawConfigParser.getboolean(self, section, option)
            except (NoSectionError, NoOptionError):
                return args[0]
        else:
            return RawConfigParser.get(self, section, option)

    def getint(self, section, option, *args):
        if len(args) > 0:
            try:
                return RawConfigParser.getint(self, section, option)
            except (NoSectionError, NoOptionError):
                return args[0]
        else:
            return RawConfigParser.get(self, section, option)
    
    def getlist(self, section, option):
        if not '%d' in option:
            option = option + '%d'
        i = 1
        l = []
        while self.has_option(section, option % (i,)):
            l.append(self.get(section, option % (i,)))
            i += 1
        return l
    
    def read(self, filenames):
        if type(filenames) == list:
            for filename in filenames:
                self.readfp(codecs.open(filename, "r", "utf8"), filename)
        else:
                self.readfp(codecs.open(filenames, "r", "utf8"), filenames)
    
    def read_string(self, string):
        f = StringIO(string)
        self.readfp(f)
