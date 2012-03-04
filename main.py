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
import locale
import gtk

def logging_excepthook(type, value, tb):
    global session
    errordialog = gtk.MessageDialog(None, gtk.DIALOG_MODAL|gtk.DIALOG_DESTROY_WITH_PARENT, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE, "Une erreur s'est produite; pour plus de détails, consultez le fichier debug.log.")
    errordialog.run()
    errordialog.destroy()
    
    logging.error(''.join(traceback.format_exception(type, value, tb)))
    try:
        gtk.main_quit()
    except:
        pass
    
    try:
        os.remove(session)
    except:
        pass
    
    sys.exit()

# Enregistrelent des message de debug dans le fichier de log
#logging.basicConfig(level=logging.DEBUG, filename='debug.log', format='%(asctime)s - %(levelname)-8s : %(message)s', datefmt='%d/%m/%Y %H:%M:%S')

# Affichage des message de debug dans la console
console = logging.StreamHandler()
#console.setLevel(logging.INFO)
console.setLevel(logging.DEBUG)
console.setFormatter(logging.Formatter('%(message)s'))
logging.getLogger('').addHandler(console)

# Enregistrement des messages d'erreur dans le fichier de log
#sys.excepthook = logging_excepthook

from lib.database import database

def main():
    
    # Utilisation de la langue du système (pour les comparaisons de chaines avec accents)
    locale.setlocale(locale.LC_ALL, '')
    
    if not os.path.isdir('./cache'):
        os.mkdir('./cache')
    
    database()
    
    return 0

if __name__ == '__main__':
    main()

