import numpy as np

from moviepy.audio.AudioClip import CompositeAudioClip
from moviepy.tools import deprecated_version_of
from moviepy.video.compositing.CompositeVideoClip import CompositeVideoClip
from moviepy.video.VideoClip import ColorClip, VideoClip

try:  # Python 2
    reduce
except NameError:  # Python 3
    from functools import reduce


def concatenate_videoclips(
    clips, method="chain", transition=None, bg_color=None, ismask=False, padding=0
):
    tt = np.cumsum([0] + [c.duration for c in clips])

    sizes = [v.size for v in clips]

    w = max(r[0] for r in sizes)
    h = max(r[1] for r in sizes)

    tt = np.maximum(0, tt + padding * np.arange(len(tt)))

    result = CompositeVideoClip(
        [c.set_start(t).set_position("center") for (c, t) in zip(clips, tt)],
        size=(w, h),
        bg_color=bg_color,
        ismask=ismask,
    )

    result.tt = tt

    result.start_times = tt[:-1]
    result.start, result.duration, result.end = 0, tt[-1], tt[-1]

    audio_t = [(c.audio, t) for c, t in zip(clips, tt) if c.audio is not None]
    if audio_t:
        result.audio = CompositeAudioClip([a.set_start(t) for a, t in audio_t])

    fpss = [c.fps for c in clips if getattr(c, "fps", None) is not None]
    result.fps = max(fpss) if fpss else None
    return result


concatenate = deprecated_version_of(concatenate_videoclips, oldname="concatenate")
