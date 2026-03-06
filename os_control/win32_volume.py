from pycaw.pycaw import AudioUtilities

def _get_volume_interface():
    device = AudioUtilities.GetSpeakers()
    volume = device.EndpointVolume

    return volume


def set_volume(percent: int):
    """
    Set master volume 0-100
    """
    volume = _get_volume_interface()

    level = max(0, min(percent, 100)) / 100
    volume.SetMasterVolumeLevelScalar(level, None)
    return True


def get_volume():
    volume = _get_volume_interface()
    return int(volume.GetMasterVolumeLevelScalar() * 100)


def increase_volume(step=10):
    volume = _get_volume_interface()

    current = volume.GetMasterVolumeLevelScalar()
    new = min(1.0, current + step / 100)

    volume.SetMasterVolumeLevelScalar(new, None)
    return int(new * 100)


def decrease_volume(step=10):
    volume = _get_volume_interface()

    current = volume.GetMasterVolumeLevelScalar()
    new = max(0.0, current - step / 100)

    volume.SetMasterVolumeLevelScalar(new, None)
    return int(new * 100)


def mute():
    volume = _get_volume_interface()
    volume.SetMute(1, None)
    return True


def unmute():
    volume = _get_volume_interface()
    volume.SetMute(0, None)
    return True