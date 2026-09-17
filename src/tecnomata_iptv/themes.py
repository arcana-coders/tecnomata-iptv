"""Local theme palettes and original Qt illustrations; no downloads or secrets."""
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QPixmap, QPainter, QColor, QPen, QLinearGradient

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
 image=QPixmap(960,640); image.fill(QColor(THEMES[theme][3]))
 p=QPainter(image); p.setRenderHint(QPainter.RenderHint.Antialiasing)
 accent=QColor(THEMES[theme][2]); p.setPen(QPen(accent,4))
 if theme == 'mcfly':
  gradient=QLinearGradient(0,0,960,640); gradient.setColorAt(0,QColor('#102e48')); gradient.setColorAt(1,QColor('#060b13')); p.fillRect(image.rect(),gradient)
  # Clock tower, lightning, stainless silhouette and two trails.
  p.setBrush(QColor('#546477')); p.drawRect(360,180,240,310); p.drawPolygon([QPoint(x,y) for x,y in [(330,180),(480,95),(630,180)]])
  p.setBrush(QColor('#e0e9ed')); p.drawEllipse(425,195,110,110); p.setPen(QPen(QColor('#152338'),5)); p.drawLine(480,250,480,212); p.drawLine(480,250,514,266)
  p.setPen(QPen(QColor('#68dfff'),7)); p.drawPolyline([QPoint(x,y) for x,y in [(720,25),(650,120),(690,116),(580,240)]])
  p.setPen(QPen(accent,12)); p.drawLine(90,570,380,450); p.drawLine(230,610,570,450)
  p.setBrush(QColor('#aebdc6')); p.setPen(QPen(QColor('#d8e5eb'),3)); p.drawRoundedRect(220,380,470,94,16,16); p.drawPolygon([QPoint(x,y) for x,y in [(320,380),(390,310),(555,310),(610,380)]])
  p.setBrush(QColor('#080e18')); p.drawEllipse(280,445,70,70); p.drawEllipse(570,445,70,70)
  text={'live':'LIVE · 88 MPH','vod':'CINEMA · 1985','series':'TO BE CONTINUED…'}[kind]
 elif theme == 'retro':
  for x in range(-500,1500,100): p.drawLine(480,280,x,640)
  for y in range(330,641,45): p.drawLine(0,y,960,y)
  p.setBrush(QColor('#ffb85b')); p.setPen(Qt.PenStyle.NoPen); p.drawEllipse(330,60,300,300)
  p.setBrush(QColor('#142537')); p.setPen(QPen(accent,6)); p.drawRoundedRect(170,235,620,260,28,28)
  p.setBrush(QColor('#ecdee9')); p.drawRoundedRect(230,275,500,135,12,12)
  for x in (330,630):
   p.setBrush(QColor('#151b2b')); p.drawEllipse(x-45,305,90,90); p.setBrush(accent); p.drawEllipse(x-13,337,26,26)
  text={'live':'ON AIR · FM STEREO','vod':'VIDEO CLUB · VHS','series':'SIDE A / SIDE B'}[kind]
 else:
  p.fillRect(image.rect(),QColor('#dedede')); p.setBrush(QColor('#282828')); p.setPen(Qt.PenStyle.NoPen)
  p.drawEllipse(210,45,540,540); p.drawEllipse(180,65,180,290); p.drawEllipse(600,65,180,290)
  for x in (375,585):
   p.setBrush(QColor('white')); p.drawEllipse(x-65,215,130,130); p.setBrush(QColor('black')); p.drawEllipse(x-26,247,52,74)
  p.setBrush(QColor('white')); p.drawEllipse(350,340,260,180); p.setBrush(QColor('black')); p.drawEllipse(425,365,110,70)
  text={'live':'LIVE','vod':'CINEMA','series':'EPISODES'}[kind]
 p.end()
 return image
