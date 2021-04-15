#%%
import inspect as ins

# TODO: file locations
RINEX_FILES = ''
DATA_FOLDER = ''


# Colors
CEND = '\033[0m'
RED = '\033[31m'
GREEN = '\033[32m'
VIOLET = '\033[35m'


PrintLevel = 0

def Set_PrintLevel(lvl):
  global PrintLevel
  PrintLevel = lvl

def Print(level: str, text: str):
  if '0' in level or '#' in level:
    return
    
  info_type = ''
  if 'debug' in level:
    info_type = f'[DEBUG] {ins.stack()[1].function}()'
  elif 'info' in level:
    info_type = '[INFO]'
  else:
    info_type = '[OTHER]'
  
  s = ''
  e = ''
  if level[0] == '\\':
    s = '\n'

  if level[-1] == '\\':
    e = '\n'

  print(f'{s}{info_type} {text}{e}')


def Debug(level= 0, msg='', nofunc=False):
  global PrintLevel
  if PrintLevel >= level:
    if nofunc:
      print(f'[DEBUG] {msg}')
    else:
      print(f'[DEBUG] {ins.stack()[1].function}() {msg}')

def Stats(level= 0, msg=''):
  global PrintLevel
  if PrintLevel >= level:
    print(f'[STATS] {msg}')


def Info(msg):
  Print('info', msg)
