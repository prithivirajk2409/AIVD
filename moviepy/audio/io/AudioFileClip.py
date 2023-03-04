from __future__ import division
from moviepy.audio.AudioClip import AudioClip
from moviepy.audio.io.readers import FFMPEG_AudioReader

class AudioFileClip(AudioClip):
    def __init__(self, filename, buffersize=200000, nbytes=2, fps=44100):
        AudioClip.__init__(self)
        self.filename = filename
        self.reader = FFMPEG_AudioReader(filename, fps=fps, nbytes=nbytes, buffersize=buffersize)
        self.fps = fps
        self.duration = self.reader.duration
        self.end = self.reader.duration
        self.buffersize = self.reader.buffersize
        self.make_frame = lambda t: self.reader.get_frame(t)
        self.nchannels = self.reader.nchannels
