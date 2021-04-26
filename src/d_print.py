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

EnabledPrints = []

def Set_PrintLevel(lvl):
  global PrintLevel
  PrintLevel = int(lvl)

def Enable_Debug(pl:int = 0):
  global EnabledPrints
  Set_PrintLevel(pl)
  func_name = ins.stack()[1].function
  EnabledPrints.append(func_name)

def Debug(level:int= 0, msg='', nofunc=False):
  global PrintLevel
  fx_n = ins.stack()[1].function
  if PrintLevel >= level and fx_n in EnabledPrints:
    if nofunc:
      print(f'[DEBUG] {msg}')
    else:
      print(f'[DEBUG] {fx_n}() {msg}')

def Stats(level:int= 0, msg=''):
  global PrintLevel
  if PrintLevel >= level:
    print(f'[STATS] {msg}')

def Info(msg):
  print(f'[INFO]  {msg}')
