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


PrintLevel:int = 0

def Set_PrintLevel(lvl):
  global PrintLevel
  PrintLevel = int(lvl)

def Debug(level:int= 0, msg='', nofunc=False):
  global PrintLevel
  if PrintLevel >= level:
    if nofunc:
      print(f'[DEBUG] {msg}')
    else:
      print(f'[DEBUG] {ins.stack()[1].function}() {msg}')

def Stats(level:int= 0, msg=''):
  global PrintLevel
  if PrintLevel >= level:
    print(f'[STATS] {msg}')


def Info(msg):
  print(f'[INFO] {msg}')
