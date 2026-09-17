"""Local theme palettes and generated raster illustrations; no downloads or secrets."""
from PySide6.QtGui import QPixmap, QColor

THEMES = {
 'springfield': ('Springfield', 'Tu sofá en Springfield.', '#ffda45', '#111d30', '#17263d'),
 'mcfly': ('Mcfly', 'Tu próxima parada: 1985.', '#00f0ff', '#090b0e', '#12151b'),
 'retro': ('Retro 80s / 90s', 'Dale play a otra época.', '#ef4444', '#0c0a09', '#171412'),
 'dog-eyes': ('Dog Eyes', 'Todo se ve distinto en blanco y negro.', '#ffffff', '#101010', '#242424'),
}

def stylesheet(base, theme):
 _, _, accent, background, panel = THEMES[theme]
 replacements = {'#ffda45':accent, '#f5cc39':accent, '#f6cc3b':accent,
 '#111d30':background, '#17263d':panel, '#ffe681':accent}
 if theme in ('mcfly','retro'):
  replacements.update({'#20334f':panel, '#3b536e':'#2c3240' if theme == 'mcfly' else '#5b403e',
    '#314660':'#2c3240' if theme == 'mcfly' else '#5b403e', '#1e3049':panel,
    '#1f344b':'#1a1e26' if theme == 'mcfly' else '#221c19', '#1e3049':panel,
    '#0c0e14':'#090b0e' if theme == 'mcfly' else '#120f0e',
    '#e2e7f0':'#dce5f2' if theme == 'mcfly' else '#e8e1df',
    '#00e5ff':accent, '#ffe787':'#7df4ff' if theme == 'mcfly' else '#ffb3ad',
    '#2c4260':'#1a1e26' if theme == 'mcfly' else '#221c19',
    '#222838':'#2c3240' if theme == 'mcfly' else '#2a2320',
    '#0078d7':accent})
 if theme == 'dog-eyes':
  import re
  for color in set(re.findall(r'#[0-9a-fA-F]{6}', base)):
   q=QColor(color); value=round(.299*q.red()+.587*q.green()+.114*q.blue())
   replacements.setdefault(color, QColor(value,value,value).name())
  replacements['#00e5ff']='#ffffff'
 import re
 result = re.sub(r'#[0-9a-fA-F]{6}', lambda m: replacements.get(m[0],m[0]), base)
 if theme in ('mcfly','retro'):
  heading = 'Space Grotesk' if theme == 'mcfly' else 'Epilogue'
  body = 'Space Mono' if theme == 'mcfly' else 'Space Grotesk'
  radius = 4 if theme == 'mcfly' else 2
  result = re.sub(r'border-radius: \d+px', f'border-radius: {radius}px', result)
  result += f"""
  QWidget {{ font-family: '{body}'; font-size: 12px; }}
  QLabel#brand, QLabel#homeTitle, QPushButton#homeLive, QPushButton#homeMovies,
  QPushButton#homeSeries, QPushButton#homeFavorites, QPushButton#homeRecent {{ font-family: '{heading}'; }}
  QLabel#streamInfo, QLabel#controlCaption, QWidget#controlGroup QLabel {{ font-family: 'Space Mono'; }}
  QLabel#streamInfo {{ color: {'#ffb800' if theme == 'mcfly' else '#f59e0b'}; }}
  QPushButton#primaryPlayback {{ border: 1px solid {accent}; }}
  """
 return result

def illustration(theme, kind):
 from pathlib import Path
 stem = {'live':'tv', 'vod':'movies', 'series':'series'}[kind]
 path = Path(__file__).parent / f'assets/backgrounds/{theme}-{stem}-v2.png'
 return QPixmap(str(path))
