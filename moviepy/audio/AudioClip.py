import os

import numpy as np
import proglog
from tqdm import tqdm

from moviepy.audio.io.ffmpeg_audiowriter import ffmpeg_audiowrite
from moviepy.Clip import Clip
from moviepy.decorators import requires_duration
from moviepy.tools import extensions_dict


class AudioClip(Clip):
    def __init__(self, make_frame=None, duration=None, fps=None):
        Clip.__init__(self)

        if fps is not None:
            self.fps = fps

    @requires_duration
    def iter_chunks(
        self,
        chunksize=None,
        chunk_duration=None,
        fps=None,
        quantize=False,
        nbytes=2,
        logger=None,
    ):
        """Iterator that returns the whole sound array of the clip by chunks"""

        totalsize = int(fps * self.duration)

        nchunks = totalsize // chunksize + 1

        pospos = np.linspace(0, totalsize, nchunks + 1, endpoint=True, dtype=int)

        for i in logger.iter_bar(chunk=list(range(nchunks))):
            size = pospos[i + 1] - pospos[i]
            assert size <= chunksize
            tt = (1.0 / fps) * np.arange(pospos[i], pospos[i + 1])
            yield self.to_soundarray(
                tt, nbytes=nbytes, quantize=quantize, fps=fps, buffersize=chunksize
            )

    @requires_duration
    def to_soundarray(
        self, tt=None, fps=None, quantize=False, nbytes=2, buffersize=50000
    ):

        snd_array = self.get_frame(tt)

        if quantize:
            snd_array = np.maximum(-0.99, np.minimum(0.99, snd_array))
            inttype = {1: "int8", 2: "int16", 4: "int32"}[nbytes]
            snd_array = (2 ** (8 * nbytes - 1) * snd_array).astype(inttype)

        return snd_array

    @requires_duration
    def write_audiofile(
        self,
        filename,
        fps=None,
        nbytes=2,
        buffersize=2000,
        codec=None,
        bitrate=None,
        ffmpeg_params=None,
        write_logfile=False,
        verbose=True,
        logger="bar",
    ):
        """Writes an audio file from the AudioClip.


        Parameters
        -----------

        filename
          Name of the output file

        fps
          Frames per second. If not set, it will try default to self.fps if
          already set, otherwise it will default to 44100

        nbytes
          Sample width (set to 2 for 16-bit sound, 4 for 32-bit sound)

        codec
          Which audio codec should be used. If None provided, the codec is
          determined based on the extension of the filename. Choose
          'pcm_s16le' for 16-bit wav and 'pcm_s32le' for 32-bit wav.

        bitrate
          Audio bitrate, given as a string like '50k', '500k', '3000k'.
          Will determine the size and quality of the output file.
          Note that it mainly an indicative goal, the bitrate won't
          necessarily be the this in the output file.

        ffmpeg_params
          Any additional parameters you would like to pass, as a list
          of terms, like ['-option1', 'value1', '-option2', 'value2']

        write_logfile
          If true, produces a detailed logfile named filename + '.log'
          when writing the file

        verbose
          Boolean indicating whether to print infomation

        logger
          Either 'bar' or None or any Proglog logger

        """

        return ffmpeg_audiowrite(
            self,
            filename,
            fps,
            nbytes,
            buffersize,
            codec=codec,
            bitrate=bitrate,
            write_logfile=write_logfile,
            verbose=verbose,
            ffmpeg_params=ffmpeg_params,
            logger=logger,
        )


class CompositeAudioClip(AudioClip):

    """Clip made by composing several AudioClips.

    An audio clip made by putting together several audio clips.

    Parameters
    ------------

    clips
      List of audio clips, which may start playing at different times or
      together. If all have their ``duration`` attribute set, the
      duration of the composite clip is computed automatically.

    """

    def __init__(self, clips):
        Clip.__init__(self)
        self.clips = clips

        ends = [c.end for c in self.clips]
        self.nchannels = max([c.nchannels for c in self.clips])
        if not any([(e is None) for e in ends]):
            self.duration = max(ends)
            self.end = max(ends)

        def make_frame(t):
            played_parts = [c.is_playing(t) for c in self.clips]

            sounds = [
                c.get_frame(t - c.start) * np.array([part]).T
                for c, part in zip(self.clips, played_parts)
                if (part is not False)
            ]

            if isinstance(t, np.ndarray):
                zero = np.zeros((len(t), self.nchannels))

            else:
                zero = np.zeros(self.nchannels)

            return zero + sum(sounds)

        self.make_frame = make_frame
