"""
This module implements VideoClip (base class for video clips) and its
main subclasses:
- Animated clips:     VideofileClip, ImageSequenceClip
- Static image clips: ImageClip, ColorClip, TextClip,
"""
import os
import tempfile
import warnings

import numpy as np
import proglog
from imageio import imread  # imsave

from ..Clip import Clip
from ..compat import DEVNULL, string_types
from ..config import get_setting
from ..decorators import (
    apply_to_mask,
    convert_masks_to_RGB,
    outplace,
    requires_duration,
    use_clip_fps_by_default,
)
from ..tools import (
    deprecated_version_of,
    extensions_dict,
    find_extension,
    is_string,
    subprocess_call,
)
from .io.ffmpeg_writer import ffmpeg_write_video
from .tools.drawing import blit


class VideoClip(Clip):
    """Base class for video clips.
    """
    def __init__(
        self, make_frame=None, ismask=False, duration=None, has_constant_size=True
    ):
        Clip.__init__(self)
        self.mask = None
        self.audio = None
        self.pos = lambda t: (0, 0)
        self.relative_pos = False
        if make_frame:
            self.make_frame = make_frame
            self.size = self.get_frame(0).shape[:2][::-1]
        self.ismask = ismask
        self.has_constant_size = has_constant_size
        if duration is not None:
            self.duration = duration
            self.end = duration

    @property
    def w(self):
        return self.size[0]

    @property
    def h(self):
        return self.size[1]

    @property
    def aspect_ratio(self):
        return self.w / float(self.h)

    @requires_duration
    @use_clip_fps_by_default
    @convert_masks_to_RGB
    def write_videofile(
        self,
        filename,
        fps=None,
        codec=None,
        bitrate=None,
        audio=True,
        audio_fps=44100,
        preset="medium",
        audio_nbytes=4,
        audio_codec=None,
        audio_bitrate=None,
        audio_bufsize=2000,
        temp_audiofile=None,
        rewrite_audio=True,
        remove_temp=True,
        write_logfile=False,
        verbose=True,
        threads=None,
        ffmpeg_params=None,
        logger="bar",
    ):
        """Write the clip to a videofile.
        """
        name, ext = os.path.splitext(os.path.basename(filename))
        ext = ext[1:].lower()
        logger = proglog.default_bar_logger(logger)

        if codec is None:
            try:
                codec = extensions_dict[ext]["codec"][0]
            except KeyError:
                raise ValueError(
                    "MoviePy couldn't find the codec associated "
                    "with the filename. Provide the 'codec' "
                    "parameter in write_videofile."
                )

        if audio_codec is None:
            if ext in ["ogv", "webm"]:
                audio_codec = "libvorbis"
            else:
                audio_codec = "libmp3lame"
        elif audio_codec == "raw16":
            audio_codec = "pcm_s16le"
        elif audio_codec == "raw32":
            audio_codec = "pcm_s32le"

        audiofile = audio if is_string(audio) else None
        make_audio = (
            (audiofile is None) and (audio == True) and (self.audio is not None)
        )

        if make_audio and temp_audiofile:
            audiofile = temp_audiofile
        elif make_audio:
            audio_ext = find_extension(audio_codec)
            audiofile = name + Clip._TEMP_FILES_PREFIX + "wvf_snd.%s" % audio_ext

        logger(message="Moviepy - Building video %s." % filename)
        if make_audio:
            self.audio.write_audiofile(
                audiofile,
                audio_fps,
                audio_nbytes,
                audio_bufsize,
                audio_codec,
                bitrate=audio_bitrate,
                write_logfile=write_logfile,
                verbose=verbose,
                logger=logger,
            )

        ffmpeg_write_video(
            self,
            filename,
            fps,
            codec,
            bitrate=bitrate,
            preset=preset,
            write_logfile=write_logfile,
            audiofile=audiofile,
            verbose=verbose,
            threads=threads,
            ffmpeg_params=ffmpeg_params,
            logger=logger,
        )

        if remove_temp and make_audio:
            if os.path.exists(audiofile):
                os.remove(audiofile)
        logger(message="Moviepy - video ready %s" % filename)

    def blit_on(self, picture, t):
        """
        Returns the result of the blit of the clip's frame at time `t`
        on the given `picture`, the position of the clip being given
        by the clip's ``pos`` attribute. Meant for compositing.
        """
        hf, wf = framesize = picture.shape[:2]

        if self.ismask and picture.max():
            return np.minimum(1, picture + self.blit_on(np.zeros(framesize), t))

        ct = t - self.start  # clip time

        img = self.get_frame(ct)
        mask = self.mask.get_frame(ct) if self.mask else None

        if mask is not None and (
            (img.shape[0] != mask.shape[0]) or (img.shape[1] != mask.shape[1])
        ):
            img = self.fill_array(img, mask.shape)

        hi, wi = img.shape[:2]

        pos = self.pos(ct)

        if isinstance(pos, str):
            pos = {
                "center": ["center", "center"],
                "left": ["left", "center"],
                "right": ["right", "center"],
                "top": ["center", "top"],
                "bottom": ["center", "bottom"],
            }[pos]
        else:
            pos = list(pos)

        if self.relative_pos:
            for i, dim in enumerate([wf, hf]):
                if not isinstance(pos[i], str):
                    pos[i] = dim * pos[i]

        if isinstance(pos[0], str):
            D = {"left": 0, "center": (wf - wi) / 2, "right": wf - wi}
            pos[0] = D[pos[0]]

        if isinstance(pos[1], str):
            D = {"top": 0, "center": (hf - hi) / 2, "bottom": hf - hi}
            pos[1] = D[pos[1]]

        pos = map(int, pos)

        return blit(img, picture, pos, mask=mask, ismask=self.ismask)

    def add_mask(self):
        """Add a mask VideoClip to the VideoClip.
        """
        if self.has_constant_size:
            mask = ColorClip(self.size, 1.0, ismask=True)
            return self.set_mask(mask.set_duration(self.duration))
        else:
            make_frame = lambda t: np.ones(self.get_frame(t).shape[:2], dtype=float)
            mask = VideoClip(ismask=True, make_frame=make_frame)
            return self.set_mask(mask.set_duration(self.duration))

    @outplace
    def set_audio(self, audioclip):
        self.audio = audioclip

    @outplace
    def set_mask(self, mask):
        assert mask is None or mask.ismask
        self.mask = mask

    @apply_to_mask
    @outplace
    def set_position(self, pos, relative=False):
        """Set the clip's position in compositions.
        """
        self.relative_pos = relative
        if hasattr(pos, "__call__"):
            self.pos = pos
        else:
            self.pos = lambda t: pos


class ImageClip(VideoClip):

    """Class for non-moving VideoClips.
    """

    def __init__(
        self, img, ismask=False, transparent=True, fromalpha=False, duration=None
    ):
        VideoClip.__init__(self, ismask=ismask, duration=duration)

        if isinstance(img, string_types):
            img = imread(img)

        if len(img.shape) == 3:  # img is (now) a RGB(a) numpy array
            if img.shape[2] == 4:
                if fromalpha:
                    img = 1.0 * img[:, :, 3] / 255
                elif ismask:
                    img = 1.0 * img[:, :, 0] / 255
                elif transparent:
                    self.mask = ImageClip(1.0 * img[:, :, 3] / 255, ismask=True)
                    img = img[:, :, :3]
            elif ismask:
                img = 1.0 * img[:, :, 0] / 255

        self.make_frame = lambda t: img
        self.size = img.shape[:2][::-1]
        self.img = img


VideoClip.set_pos = deprecated_version_of(VideoClip.set_position, "set_pos")
VideoClip.to_videofile = deprecated_version_of(
    VideoClip.write_videofile, "to_videofile"
)


class ColorClip(ImageClip):

    """An ImageClip showing just one color.
    """

    def __init__(self, size, color=None, ismask=False, duration=None, col=None):
        if col is not None:
            warnings.warn(
                "The `ColorClip` parameter `col` has been deprecated."
                " Please use `color` instead.",
                DeprecationWarning,
            )
            if color is not None:
                warnings.warn(
                    "The arguments `color` and `col` have both been "
                    "passed to `ColorClip` so `col` has been ignored.",
                    UserWarning,
                )
            else:
                color = col
        w, h = size
        shape = (h, w) if np.isscalar(color) else (h, w, len(color))
        ImageClip.__init__(
            self, np.tile(color, w * h).reshape(shape), ismask=ismask, duration=duration
        )


class TextClip(ImageClip):

    """Class for autogenerated text clips.
    """

    def __init__(
        self,
        txt=None,
        filename=None,
        size=None,
        color="black",
        bg_color="transparent",
        fontsize=None,
        font="Courier",
        stroke_color=None,
        stroke_width=1,
        method="label",
        kerning=None,
        align="center",
        interline=None,
        tempfilename=None,
        temptxt=None,
        transparent=True,
        remove_temp=True,
        print_cmd=False,
    ):
        if txt is not None:
            if temptxt is None:
                temptxt_fd, temptxt = tempfile.mkstemp(suffix=".txt")
                try:  # only in Python3 will this work
                    os.write(temptxt_fd, bytes(txt, "UTF8"))
                except TypeError:  # oops, fall back to Python2
                    os.write(temptxt_fd, txt)
                os.close(temptxt_fd)
            txt = "@" + temptxt
        else:
            txt = "@%" + filename

        if size is not None:
            size = (
                "" if size[0] is None else str(size[0]),
                "" if size[1] is None else str(size[1]),
            )

        cmd = [
            get_setting("IMAGEMAGICK_BINARY"),
            "-background",
            bg_color,
            "-fill",
            color,
            "-font",
            font,
        ]

        if fontsize is not None:
            cmd += ["-pointsize", "%d" % fontsize]
        if kerning is not None:
            cmd += ["-kerning", "%0.1f" % kerning]
        if stroke_color is not None:
            cmd += ["-stroke", stroke_color, "-strokewidth", "%.01f" % stroke_width]
        if size is not None:
            cmd += ["-size", "%sx%s" % (size[0], size[1])]
        if align is not None:
            cmd += ["-gravity", align]
        if interline is not None:
            cmd += ["-interline-spacing", "%d" % interline]

        if tempfilename is None:
            tempfile_fd, tempfilename = tempfile.mkstemp(suffix=".png")
            os.close(tempfile_fd)

        cmd += [
            "%s:%s" % (method, txt),
            "-type",
            "truecolormatte",
            "PNG32:%s" % tempfilename,
        ]

        if print_cmd:
            print(" ".join(cmd))

        try:
            subprocess_call(cmd, logger=None)
        except (IOError, OSError) as err:
            error = (
                "MoviePy Error: creation of %s failed because of the "
                "following error:\n\n%s.\n\n." % (filename, str(err))
                + (
                    "This error can be due to the fact that ImageMagick "
                    "is not installed on your computer, or (for Windows "
                    "users) that you didn't specify the path to the "
                    "ImageMagick binary in file conf.py, or that the path "
                    "you specified is incorrect"
                )
            )
            raise IOError(error)

        ImageClip.__init__(self, tempfilename, transparent=transparent)
        self.txt = txt
        self.color = color
        self.stroke_color = stroke_color

        if remove_temp:
            if os.path.exists(tempfilename):
                os.remove(tempfilename)
            if os.path.exists(temptxt):
                os.remove(temptxt)
