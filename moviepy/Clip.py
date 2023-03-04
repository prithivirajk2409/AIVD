from copy import copy

import numpy as np
import proglog

from moviepy.decorators import (
    apply_to_audio,
    apply_to_mask,
    convert_to_seconds,
    outplace,
    requires_duration,
    use_clip_fps_by_default,
)


class Clip:
    _TEMP_FILES_PREFIX = "TEMP_MPY_"

    def __init__(self):
        self.start = 0
        self.end = None
        self.duration = None

        self.memoize = False
        self.memoized_t = None
        self.memoize_frame = None

    def copy(self):
        newclip = copy(self)
        if hasattr(self, "audio"):
            newclip.audio = copy(self.audio)
        if hasattr(self, "mask"):
            newclip.mask = copy(self.mask)

        return newclip

    @convert_to_seconds(["t"])
    def get_frame(self, t):
        if self.memoize:
            if t == self.memoized_t:
                return self.memoized_frame
            else:
                frame = self.make_frame(t)
                self.memoized_t = t
                self.memoized_frame = frame
                return frame
        else:
            return self.make_frame(t)

    @apply_to_mask
    @apply_to_audio
    @convert_to_seconds(["t"])
    @outplace
    def set_start(self, t, change_end=True):

        self.start = t
        if (self.duration is not None) and change_end:
            self.end = t + self.duration
        elif self.end is not None:
            self.duration = self.end - self.start

    @apply_to_mask
    @apply_to_audio
    @convert_to_seconds(["t"])
    @outplace
    def set_end(self, t):
        self.end = t
        if self.end is None:
            return
        if self.start is None:
            if self.duration is not None:
                self.start = max(0, t - newclip.duration)
        else:
            self.duration = self.end - self.start

    @apply_to_mask
    @apply_to_audio
    @convert_to_seconds(["t"])
    @outplace
    def set_duration(self, t, change_end=True):
        self.duration = t

        if change_end:
            self.end = None if (t is None) else (self.start + t)
        else:
            if self.duration is None:
                raise Exception("Cannot change clip start when new" "duration is None")
            self.start = self.end - t

    @convert_to_seconds(["t"])
    def is_playing(self, t):

        if isinstance(t, np.ndarray):
            tmin, tmax = t.min(), t.max()

            if (self.end is not None) and (tmin >= self.end):
                return False

            if tmax < self.start:
                return False

            result = 1 * (t >= self.start)
            if self.end is not None:
                result *= t <= self.end
            return result

        else:
            return (t >= self.start) and ((self.end is None) or (t < self.end))

    @requires_duration
    @use_clip_fps_by_default
    def iter_frames(self, fps=None, with_times=False, logger=None, dtype=None):
        logger = proglog.default_bar_logger(logger)
        for t in logger.iter_bar(t=np.arange(0, self.duration, 1.0 / fps)):
            frame = self.get_frame(t)
            if (dtype is not None) and (frame.dtype != dtype):
                frame = frame.astype(dtype)
            if with_times:
                yield t, frame
            else:
                yield frame
