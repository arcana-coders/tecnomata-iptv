"""Track preferences without media URLs; matching tolerates changed track IDs."""


def track_choice(info, kind):
    selected = info.get('aid' if kind == 'audio' else 'sid')
    if kind == 'sub' and (selected is False or selected in ('no',None)):
        return 'no'
    return next((dict(track) for track in info.get(kind,[]) if track['id'] == selected),None)


def resolve_track(choice, tracks):
    if choice == 'no':
        return 'no'
    if not isinstance(choice,dict):
        return None
    identity = next((track for track in tracks if track['id'] == choice.get('id')),None)
    descriptors = {key:choice[key] for key in ('lang','codec','title') if choice.get(key)}
    if descriptors:
        matches = [track for track in tracks if all(track.get(key) == value for key,value in descriptors.items())]
        if identity in matches:
            return identity['id']
        if len(matches) == 1:
            return matches[0]['id']
        return None  # Do not silently pick another language if the provider changed tracks.
    return identity['id'] if identity else None
