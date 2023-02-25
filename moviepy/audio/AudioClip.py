import os

import numpy as np
import proglog
from tqdm import tqdm

from moviepy.audio.io.ffmpeg_audiowriter import ffmpeg_audiowrite
from moviepy.Clip import Clip
from moviepy.decorators import requires_duration
from moviepy.tools import extensions_dict


class AudioClip(Clip):
    """Base class for audio clips.

    See ``AudioFileClip`` and ``CompositeSoundClip`` for usable classes.

    An AudioClip is a Clip with a ``make_frame``  attribute of
    the form `` t -> [ f_t ]`` for mono sound and
    ``t-> [ f1_t, f2_t ]`` for stereo sound (the arrays are Numpy arrays).
    The `f_t` are floats between -1 and 1. These bounds can be
    trespassed wihtout problems (the program will put the
    sound back into the bounds at conversion time, without much impact).

    Parameters
    -----------

    make_frame
      A function `t-> frame at time t`. The frame does not mean much
      for a sound, it is just a float. What 'makes' the sound are
      the variations of that float in the time.

    nchannels
      Number of channels (one or two for mono or stereo).

    Examples
    ---------

    >>> # Plays the note A (a sine wave of frequency 440HZ)
    >>> import numpy as np
    >>> make_frame = lambda t: 2*[ np.sin(440 * 2 * np.pi * t) ]
    >>> clip = AudioClip(make_frame, duration=5)
    >>> clip.preview()

    """

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
        """
        Transforms the sound into an array that can be played by pygame
        or written in a wav file. See ``AudioClip.preview``.

        Parameters
        ------------

        fps
          Frame rate of the sound for the conversion.
          44100 for top quality.

        nbytes
          Number of bytes to encode the sound: 1 for 8bit sound,
          2 for 16bit, 4 for 32bit sound.

        """

        """
        elif len(tt)> 1.5*buffersize:
            nchunks = int(len(tt)/buffersize+1)
            tt_chunks = np.array_split(tt, nchunks)
            return stacker([self.to_soundarray(tt=ttc, buffersize=buffersize, fps=fps,
                                        quantize=quantize, nbytes=nbytes)
                              for ttc in tt_chunks])
        """

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
