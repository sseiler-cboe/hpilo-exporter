#!/usr/bin/env python

import hpilo
import logging
import os
import sys
import re
import subprocess
from pprint import pprint

logging.basicConfig(level=logging.DEBUG, format=f'%(asctime)s %(levelname)s %(name)s: %(message)s')

def try_sudo():
  ret = subprocess.check_call("sudo -n -v", shell=True)
  return ret

def get_binpath():
  home = os.getenv('HOME', '/home/'+os.getenv('USER'))
  binpath = home + '/bin'
  try:
    os.mkdir(binpath, mode=0o755)
  except FileExistsError:
    logging.debug('Path {} already exists.'.format(binpath))
  except Exception as e:
    logging.error(e)
    sys.exit(1)

  return binpath

def setup_hponcfg():
  binpath = get_binpath()
  hponcfg = binpath + '/hponcfg'
  raw_script = """
  #!/bin/bash -

  exec /usr/bin/sudo /usr/sbin/hponcfg $@
  """
  script = re.sub(r'^\s+', '', raw_script, flags=re.M)
  try:
    with open(hponcfg, 'w') as hp_script:
      hp_script.write(script)
  except Exception as e:
    logging.error(e)
    sys.exit(1)
    
  os.chmod(hponcfg, 0o755)

  currentpath = os.getenv('PATH')
  os.environ['PATH'] = binpath + ':' + currentpath
  
def sudo_ilo_login():
  if (try_sudo() == 0):
    setup_hponcfg()
    ilo = ilo_login()
    return ilo
  else:
    logging.error('unable to run sudo. you do not have permissions.')
    sys.exit(1)

def ilo_login():
  try:
    ilo = hpilo.Ilo(hostname='localhost')
  except hpilo.IloLoginFailed:
    logging.error("ILO login failed")
  except hpilo.IloCommunicationError as e:
    logging.error(e)

  return ilo

def main():
  ilo = ilo_login()

  try:
    ilo.get_product_name()
  except hpilo.IloError:
    logging.warning('unable to complete initial login. will try via sudo.')
    ilo = sudo_ilo_login()
  except Exception as e:
    logging.error(e)
    sys.exit(1)

  try:
    health = ilo.get_embedded_health()
    pprint(health)
  except Exception as e:
    logging.error(e)
    sys.exit(1)

if __name__ == "__main__":
  main()

# vim: set ts=2 sts=2 sw=2 et:
