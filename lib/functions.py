#!/usr/bin/python2
# -*- coding: utf-8 -*-

import os
import platform
import ctypes
import zipfile
import hashlib
from distutils import version

def cmp_version(a,b):
    """
        Compare deux chaînes représentant une version.
    """
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
    """
        Renvoie : la taille du dossier ou fichier path
    """
    size = 0
    if os.path.isfile(path):
        size = os.path.getsize(path)
    elif os.path.isdir(path):
        for dirpath, dirnames, filenames in os.walk(path):
            for filename in filenames:
                size += os.path.getsize(os.path.join(dirpath, filename))
    return size

def md5file(path):
    """
        Renvoie la somme md5 du fichier path
    """
    md5 = hashlib.md5()
    f = open(path, "rb")
    while True:
        data = f.read(2**20) # Pour éviter d'utiliser trop de mémoire
        if not data:
            break
        md5.update(data)
    return md5.hexdigest()

def rmtree(path, ignore_errors=False, callback=None, exclude=[], onerror=None, foldersize=0, delsize=0):
	"""Recursively delete a directory tree.

	If ignore_errors is set, errors are ignored; otherwise, if onerror
	is set, it is called to handle the error with arguments (func,
	path, exc_info) where func is os.listdir, os.remove, or os.rmdir;
	path is the argument to that function that caused it to fail; and
	exc_info is a tuple returned by sys.exc_info().  If ignore_errors
	is false and onerror is None, an exception is raised.
	"""
	if foldersize == 0 and os.path.isdir(path):
		for (folder, dirs, files) in os.walk(path):
			for file in files:
				foldersize += os.path.getsize(os.path.join(folder, file))
	
	if callback is None:
		callback = lambda a,b : None
	
	if ignore_errors:
		onerror = lambda *a: None
	elif onerror is None:
		def onerror(*args):
			raise
	try:
		if os.path.islink(path):
			# symlinks to directories are forbidden, see bug #1669
			raise OSError("Cannot call rmtree on a symbolic link")
	except OSError:
		onerror(os.path.islink, path, sys.exc_info())
		# can't continue even if onerror hook returns
		return
	names = []
	try:
		names = os.listdir(path)
	except os.error, err:
		onerror(os.listdir, path, sys.exc_info())
	for name in names:
		fullname = os.path.join(path, name)
		try:
			mode = os.lstat(fullname).st_mode
		except os.error:
			mode = 0
		if not fullname in exclude:
			if stat.S_ISDIR(mode):
				delsize = rmtree(fullname, ignore_errors, callback, exclude, onerror, foldersize, delsize)
			else:
				try:
					delsize += os.path.getsize(fullname)
					os.remove(fullname)
					callback(delsize, foldersize)
				except os.error, err:
					onerror(os.remove, fullname, sys.exc_info())
	try:
		os.rmdir(path)
	except os.error:
		onerror(os.rmdir, path, sys.exc_info())
		
	return delsize

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
