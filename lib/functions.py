#!/usr/bin/python2
# -*- coding: utf-8 -*-

import os
import platform
import ctypes
import zipfile
from distutils import version

def cmp_version(a,b):
    """Compare deux chaînes représentant une version."""
    return -cmp(version.LooseVersion(a), version.LooseVersion(b))

def get_free_space(folder):
    """
        Arguments :
            folder : chemin
        
        Renvoie :
            L'espace libre dans le dossier folder en octets
    """
    if platform.system() == 'Windows':
        free_bytes = ctypes.c_ulonglong(0)
        ctypes.windll.kernel32.GetDiskFreeSpaceExW(ctypes.c_wchar_p(folder), None, None, ctypes.pointer(free_bytes))
        return free_bytes.value
    else:
        s = os.statvfs(folder)
        return s.f_bsize * s.f_bavail

def get_size(path):
    """Renvoie : la taille du dossier ou fichier path"""
    size = 0
    if os.path.isfile(path):
        size = os.path.getsize(path)
    elif os.path.isdir(path):
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                size += os.path.getsize(os.path.join(dirpath, filename))
    return size

def zipextractall(zip, path=None, callback=None, members=None, pwd=None, exclude=[]):
	"""Extract all members from the archive to the current working
	   directory. `path' specifies a different directory to extract to.
	   `members' is optional and must be a subset of the list returned
	   by namelist().
	"""
	zip = zipfile.ZipFile(zip, 'r')
	
	if callback is None:
		callback = lambda a,b : None
	
	if members is None:
		members = zip.namelist()
	
	for i in exclude:
		for j in members:
			if os.path.normpath(j).startswith(i):
				members.remove(j)
	
	zipsize = 0
	for infos in zip.infolist():
		zipsize += infos.file_size
	dirsize = 0
	
	for zipinfo in members:
		zip.extract(zipinfo, path, pwd)
		dirsize += zip.getinfo(zipinfo).file_size
		callback(dirsize, zipsize)

	zip.close()
