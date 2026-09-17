"""Local theme palettes and generated raster illustrations; no downloads or secrets."""
from PySide6.QtGui import QPixmap, QColor

THEMES = {
 'springfield': ('Springfield', 'Tu sofá en Springfield.', '#ffda45', '#111d30', '#17263d'),
 'mcfly': ('Mcfly', 'Tu próxima parada: 1985.', '#ff9c38', '#101923', '#203041'),
 'retro': ('Retro 80s / 90s', 'Dale play a otra época.', '#ff6fae', '#151b2b', '#263047'),
 'dog-eyes': ('Dog Eyes', 'Todo se ve distinto en blanco y negro.', '#ffffff', '#101010', '#242424'),
}

def stylesheet(base, theme):
 _, _, accent, background, panel = THEMES[theme]
 replacements = {'#ffda45':accent, '#f5cc39':accent, '#f6cc3b':accent,
 '#111d30':background, '#17263d':panel, '#ffe681':accent}
 if theme == 'dog-eyes':
  import re
  for color in set(re.findall(r'#[0-9a-fA-F]{6}', base)):
   q=QColor(color); value=round(.299*q.red()+.587*q.green()+.114*q.blue())
   replacements.setdefault(color, QColor(value,value,value).name())
  replacements['#00e5ff']='#ffffff'
 import re
 return re.sub(r'#[0-9a-fA-F]{6}', lambda m: replacements.get(m[0],m[0]), base)

def illustration(theme, kind):
 from pathlib import Path
 stem = {'live':'tv', 'vod':'movies', 'series':'series'}[kind]
 path = Path(__file__).parent / f'assets/backgrounds/{theme}-{stem}-v2.png'
 return QPixmap(str(path))
