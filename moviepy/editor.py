import os

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"

from .video.io.VideoFileClip import VideoFileClip
from .video.VideoClip import VideoClip, ImageClip, TextClip
from .video.compositing.CompositeVideoClip import CompositeVideoClip
from .video.compositing.concatenate import concatenate_videoclips
from .audio.AudioClip import AudioClip
from .audio.io.AudioFileClip import AudioFileClip
