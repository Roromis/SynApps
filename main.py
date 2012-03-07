#!/usr/bin/env python2
# -*- coding: utf-8 -*-
#
#  main.py
#  
#  Copyright 2012 Roromis <admin@roromis.fr.nf>
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

import logging
import os
import sys
import locale
import traceback

logger = logging.getLogger('synapps')
logger.setLevel(logging.DEBUG)

# Affichage des message de debug dans la console
console = logging.StreamHandler()
#console.setLevel(logging.INFO)
console.setLevel(logging.DEBUG)
console.setFormatter(logging.Formatter(fmt='%(message)s'))
logger.addHandler(console)

# Enregistrement des message de debug dans le fichier de log
debugfile = logging.FileHandler("./debug.log", "w", encoding = "utf-8")
debugfile.setLevel(logging.DEBUG)
debugfile.setFormatter(logging.Formatter(fmt='%(asctime)s - %(levelname)-8s : %(message)s', datefmt='%d/%m/%Y %H:%M:%S'))
logger.addHandler(debugfile)

# Enregistrement des messages d'erreur dans le fichier de log
def logging_excepthook(type, value, tb):
    logger.error(u''.join(traceback.format_exception(type, value, tb)))
    
    # TODO : gui (quitter la boucle) et session (supprimer le fichier)
    
    sys.exit()

sys.excepthook = logging_excepthook

from lib.database import database

def main():
    # Utilisation de la langue du système (pour les comparaisons de chaines avec accents)
    locale.setlocale(locale.LC_ALL, '')
    
    if not os.path.isdir('./cache'):
        os.mkdir('./cache')
    if not os.path.isdir('./cache/icons'):
        os.mkdir('./cache/icons')
    
    db = database()
    #logger.debug(u"Version : %s" % db.get_config("version"))
    db.update(force=True)
    
    return 0

if __name__ == '__main__':
    main()

