import os
import numpy as np
import proglog
from tqdm import tqdm
from moviepy.audio.io.ffmpeg_audiowriter import ffmpeg_audiowrite
from moviepy.Clip import Clip
from moviepy.decorators import requires_duration
# from moviepy.tools import extensions_dict

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
