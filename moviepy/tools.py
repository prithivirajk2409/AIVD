import os, sys, warnings, proglog
import subprocess as sp
from .compat import DEVNULL

def subprocess_call(cmd, logger="bar", errorprint=True):
    logger = proglog.default_bar_logger(logger)
    logger(message='Moviepy - Running:\n>>> "+ " ".join(cmd)')

    popen_params = {"stdout": DEVNULL, "stderr": sp.PIPE, "stdin": DEVNULL}

    if os.name == "nt":
        popen_params["creationflags"] = 0x08000000

    proc = sp.Popen(cmd, **popen_params)

    out, err = proc.communicate()  # proc.wait()
    proc.stderr.close()

    if proc.returncode:
        if errorprint:
            logger(message="Moviepy - Command returned an error")
        raise IOError(err.decode("utf8"))
    else:
        logger(message="Moviepy - Command successful")

    del proc


def is_string(obj):
    try:
        return isinstance(obj, basestring)
    except NameError:
        return isinstance(obj, str)


def cvsecs(time):
    factors = (1, 60, 3600)

    if is_string(time):
        time = [float(f.replace(",", ".")) for f in time.split(":")]

    if not isinstance(time, (tuple, list)):
        return time

    return sum(mult * part for mult, part in zip(factors, reversed(time)))


def deprecated_version_of(f, oldname, newname=None):
    if newname is None:
        newname = f.__name__

    warning = (
        "The function ``%s`` is deprecated and is kept temporarily "
        "for backwards compatibility.\nPlease use the new name, "
        "``%s``, instead."
    ) % (oldname, newname)

    def fdepr(*a, **kw):
        warnings.warn("MoviePy: " + warning, PendingDeprecationWarning)
        return f(*a, **kw)

    fdepr.__doc__ = warning

    return fdepr


extensions_dict = {
    "mp4": {"type": "video", "codec": ["libx264", "libmpeg4", "aac"]},
    "ogv": {"type": "video", "codec": ["libtheora"]},
    "webm": {"type": "video", "codec": ["libvpx"]},
    "avi": {"type": "video"},
    "mov": {"type": "video"},
    "ogg": {"type": "audio", "codec": ["libvorbis"]},
    "mp3": {"type": "audio", "codec": ["libmp3lame"]},
    "wav": {"type": "audio", "codec": ["pcm_s16le", "pcm_s24le", "pcm_s32le"]},
    "m4a": {"type": "audio", "codec": ["libfdk_aac"]},
}

for ext in ["jpg", "jpeg", "png", "bmp", "tiff"]:
    extensions_dict[ext] = {"type": "image"}


def find_extension(codec):
    if codec in extensions_dict:
        return codec

    for ext, infos in extensions_dict.items():
        if codec in infos.get("codec", []):
            return ext
    raise ValueError(
        "The audio_codec you chose is unknown by MoviePy. "
        "You should report this. In the meantime, you can "
        "specify a temp_audiofile with the right extension "
        "in write_videofile."
    )
