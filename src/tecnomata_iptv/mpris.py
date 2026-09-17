"""Session-bus MPRIS bridge. Publishes catalog titles, never stream URLs."""
import asyncio
import os
import threading
from dbus_fast import Variant
from dbus_fast.aio import MessageBus
from dbus_fast.constants import PropertyAccess
from dbus_fast.service import ServiceInterface, dbus_property, dbus_method
from PySide6.QtCore import QObject, Signal

PATH = '/org/mpris/MediaPlayer2'
READ = PropertyAccess.READ


class Root(ServiceInterface):
    def __init__(self, dispatch):
        super().__init__('org.mpris.MediaPlayer2')
        self.dispatch = dispatch

    @dbus_method()
    def Raise(self): self.dispatch('raise', None)
    @dbus_method()
    def Quit(self): pass
    @dbus_property(access=READ)
    def CanQuit(self) -> 'b': return False
    @dbus_property(access=READ)
    def CanRaise(self) -> 'b': return True
    @dbus_property(access=READ)
    def HasTrackList(self) -> 'b': return False
    @dbus_property(access=READ)
    def Identity(self) -> 's': return 'Tecnomata IPTV'
    @dbus_property(access=READ)
    def DesktopEntry(self) -> 's': return 'tecnomata-iptv'
    @dbus_property(access=READ)
    def SupportedUriSchemes(self) -> 'as': return []
    @dbus_property(access=READ)
    def SupportedMimeTypes(self) -> 'as': return []


class Player(ServiceInterface):
    def __init__(self, dispatch):
        super().__init__('org.mpris.MediaPlayer2.Player')
        self.dispatch = dispatch
        self.values = {'PlaybackStatus':'Stopped', 'Metadata':{}, 'Volume':.65,
                       'Position':0, 'CanSeek':False, 'CanPlay':False, 'CanPause':False}

    def update(self, snapshot):
        changed = {k:v for k,v in snapshot.items() if k != 'Position' and self.values.get(k) != v}
        self.values.update(snapshot)
        if changed: self.emit_properties_changed(changed)

    @dbus_method()
    def PlayPause(self): self.dispatch('toggle', None)
    @dbus_method()
    def Pause(self): self.dispatch('pause', None)
    @dbus_method()
    def Play(self): self.dispatch('play', None)
    @dbus_method()
    def Stop(self): self.dispatch('stop', None)
    @dbus_method()
    def Next(self): pass
    @dbus_method()
    def Previous(self): pass
    @dbus_method()
    def Seek(self, Offset: 'x'):
        if self.CanSeek: self.dispatch('seek', (self.Position + Offset)/1_000_000)
    @dbus_method()
    def SetPosition(self, TrackId: 'o', Position: 'x'):
        track = self.Metadata.get('mpris:trackid')
        if self.CanSeek and track and track.value == TrackId and Position >= 0:
            self.dispatch('seek', Position/1_000_000)
    @dbus_method()
    def OpenUri(self, Uri: 's'): pass
    @dbus_property(access=READ)
    def PlaybackStatus(self) -> 's': return self.values['PlaybackStatus']
    @dbus_property(access=READ)
    def Metadata(self) -> 'a{sv}': return self.values['Metadata']
    @dbus_property(access=READ)
    def Position(self) -> 'x': return self.values['Position']
    @dbus_property(access=READ)
    def CanSeek(self) -> 'b': return self.values['CanSeek']
    @dbus_property(access=READ)
    def CanPlay(self) -> 'b': return self.values['CanPlay']
    @dbus_property(access=READ)
    def CanPause(self) -> 'b': return self.values['CanPause']
    @dbus_property(access=READ)
    def CanControl(self) -> 'b': return True
    @dbus_property(access=READ)
    def CanGoNext(self) -> 'b': return False
    @dbus_property(access=READ)
    def CanGoPrevious(self) -> 'b': return False
    @dbus_property(access=READ)
    def Rate(self) -> 'd': return 1.
    @dbus_property(access=READ)
    def MinimumRate(self) -> 'd': return 1.
    @dbus_property(access=READ)
    def MaximumRate(self) -> 'd': return 1.
    @dbus_property()
    def Volume(self) -> 'd': return self.values['Volume']
    @Volume.setter
    def Volume(self, value: 'd'): self.dispatch('volume', max(0.,min(1.,value)))


class MprisBridge(QObject):
    requested = Signal(str, object)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.name = f'org.mpris.MediaPlayer2.tecnomata_iptv.instance{os.getpid()}'
        self.loop = asyncio.new_event_loop()
        self.player = None
        self.bus = None
        self.available = False
        self.latest = {}
        self.closed = False
        self.thread = threading.Thread(target=self.run, daemon=True, name='iptv-mpris')
        self.thread.start()

    def run(self):
        asyncio.set_event_loop(self.loop)
        async def connect():
            self.bus = await MessageBus().connect()
            self.player = Player(self.requested.emit)
            self.bus.export(PATH, Root(self.requested.emit))
            self.bus.export(PATH, self.player)
            await self.bus.request_name(self.name)
            self.player.update(self.latest)
            self.available = True
        try:
            self.loop.run_until_complete(connect())
            if not self.closed: self.loop.run_forever()
        except Exception:
            pass  # Missing session bus must not prevent playback; no raw errors.
        finally:
            self.available = False
            if self.bus: self.bus.disconnect()
            self.loop.close()

    def publish(self, title='', state='Stopped', position=0, duration=0, seekable=False, volume=.65, track=0):
        metadata = {} if not title else {
            'mpris:trackid':Variant('o',f'/tecnomata/iptv/track/{track}'),
            'xesam:title':Variant('s',title),
            'xesam:artist':Variant('as',[])}
        if title and duration > 0: metadata['mpris:length'] = Variant('x',round(duration*1_000_000))
        snapshot = {'Metadata':metadata,'PlaybackStatus':state,'Position':round(position*1_000_000),
                    'CanSeek':bool(seekable),'CanPlay':bool(title),'CanPause':bool(title),'Volume':float(volume)}
        self.latest = snapshot
        if self.available and not self.closed:
            self.loop.call_soon_threadsafe(self.player.update, snapshot)

    def close(self):
        self.closed = True
        if self.loop.is_running(): self.loop.call_soon_threadsafe(self.loop.stop)
        self.thread.join(timeout=1)
