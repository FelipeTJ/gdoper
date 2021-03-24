#%%

# Colors
CEND = '\033[0m'
GREEN = '\033[32m'
VIOLET = '\033[35m'

def Print(level: str, text: str):
  if '0' in level or '#' in level:
    return
    
  info_type = ''
  if 'debug' in level:
    info_type = '[DEBUG]'
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


