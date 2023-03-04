from __future__ import division
import logging, os, re, warnings
import subprocess as sp
import numpy as np
from moviepy.compat import DEVNULL, PY3
from moviepy.config import get_setting  # ffmpeg, ffmpeg.exe, etc...
from moviepy.tools import cvsecs

logging.captureWarnings(True)


class FFMPEG_VideoReader:
    def __init__(
        self,
        filename,
        print_infos=False,
        bufsize=None,
        pix_fmt="rgb24",
        check_duration=True,
        target_resolution=None,
        resize_algo="bicubic",
        fps_source="tbr",
    ):
        self.filename = filename
        self.proc = None
        infos = ffmpeg_parse_infos(filename, print_infos, check_duration, fps_source)
        self.fps = infos["video_fps"]
        self.size = infos["video_size"]
        self.rotation = infos["video_rotation"]

        if target_resolution:
            target_resolution = target_resolution[1], target_resolution[0]

            if None in target_resolution:
                ratio = 1
                for idx, target in enumerate(target_resolution):
                    if target:
                        ratio = target / self.size[idx]
                self.size = (int(self.size[0] * ratio), int(self.size[1] * ratio))
            else:
                self.size = target_resolution
        self.resize_algo = resize_algo

        self.duration = infos["video_duration"]
        self.ffmpeg_duration = infos["duration"]
        self.nframes = infos["video_nframes"]

        self.infos = infos

        self.pix_fmt = pix_fmt
        self.depth = 4 if pix_fmt == "rgba" else 3

        if bufsize is None:
            w, h = self.size
            bufsize = self.depth * w * h + 100

        self.bufsize = bufsize
        self.initialize()

        self.pos = 1
        self.lastread = self.read_frame()

    def initialize(self, starttime=0):
        """Opens the file, creates the pipe."""

        self.close()  # if any

        if starttime != 0:
            offset = min(1, starttime)
            i_arg = [
                "-ss",
                "%.06f" % (starttime - offset),
                "-i",
                self.filename,
                "-ss",
                "%.06f" % offset,
            ]
        else:
            i_arg = ["-i", self.filename]

        cmd = (
            [get_setting("FFMPEG_BINARY")]
            + i_arg
            + [
                "-loglevel",
                "error",
                "-f",
                "image2pipe",
                "-vf",
                "scale=%d:%d" % tuple(self.size),
                "-sws_flags",
                self.resize_algo,
                "-pix_fmt",
                self.pix_fmt,
                "-vcodec",
                "rawvideo",
                "-",
            ]
        )
        popen_params = {
            "bufsize": self.bufsize,
            "stdout": sp.PIPE,
            "stderr": sp.PIPE,
            "stdin": DEVNULL,
        }

        if os.name == "nt":
            popen_params["creationflags"] = 0x08000000

        self.proc = sp.Popen(cmd, **popen_params)

    def skip_frames(self, n=1):
        """Reads and throws away n frames"""
        w, h = self.size
        for i in range(n):
            self.proc.stdout.read(self.depth * w * h)
        self.pos += n

    def read_frame(self):
        w, h = self.size
        nbytes = self.depth * w * h

        s = self.proc.stdout.read(nbytes)
        if len(s) != nbytes:
            warnings.warn(
                "Warning: in file %s, " % (self.filename)
                + "%d bytes wanted but %d bytes read," % (nbytes, len(s))
                + "at frame %d/%d, at time %.02f/%.02f sec. "
                % (self.pos, self.nframes, 1.0 * self.pos / self.fps, self.duration)
                + "Using the last valid frame instead.",
                UserWarning,
            )

            if not hasattr(self, "lastread"):
                raise IOError(
                    (
                        "MoviePy error: failed to read the first frame of "
                        "video file %s. That might mean that the file is "
                        "corrupted. That may also mean that you are using "
                        "a deprecated version of FFMPEG. On Ubuntu/Debian "
                        "for instance the version in the repos is deprecated. "
                        "Please update to a recent version from the website."
                    )
                    % (self.filename)
                )

            result = self.lastread

        else:
            if hasattr(np, "frombuffer"):
                result = np.frombuffer(s, dtype="uint8")
            else:
                result = np.fromstring(s, dtype="uint8")
            result.shape = (h, w, len(s) // (w * h))  # reshape((h, w, len(s)//(w*h)))
            self.lastread = result

        return result

    def get_frame(self, t):
        pos = int(self.fps * t + 0.00001) + 1

        if not self.proc:
            self.initialize(t)
            self.pos = pos
            self.lastread = self.read_frame()

        if pos == self.pos:
            return self.lastread
        elif (pos < self.pos) or (pos > self.pos + 100):
            self.initialize(t)
            self.pos = pos
        else:
            self.skip_frames(pos - self.pos - 1)
        result = self.read_frame()
        self.pos = pos
        return result

    def close(self):
        if self.proc:
            self.proc.terminate()
            self.proc.stdout.close()
            self.proc.stderr.close()
            self.proc.wait()
            self.proc = None
        if hasattr(self, "lastread"):
            del self.lastread

    def __del__(self):
        self.close()


def ffmpeg_read_image(filename, with_mask=True):
    pix_fmt = "rgba" if with_mask else "rgb24"
    reader = FFMPEG_VideoReader(filename, pix_fmt=pix_fmt, check_duration=False)
    im = reader.lastread
    del reader
    return im


def ffmpeg_parse_infos(
    filename, print_infos=False, check_duration=True, fps_source="tbr"
):

    is_GIF = filename.endswith(".gif")
    cmd = [get_setting("FFMPEG_BINARY"), "-i", filename]
    if is_GIF:
        cmd += ["-f", "null", "/dev/null"]

    popen_params = {
        "bufsize": 10**5,
        "stdout": sp.PIPE,
        "stderr": sp.PIPE,
        "stdin": DEVNULL,
    }

    if os.name == "nt":
        popen_params["creationflags"] = 0x08000000

    proc = sp.Popen(cmd, **popen_params)
    (output, error) = proc.communicate()
    infos = error.decode("utf8")

    del proc

    if print_infos:
        print(infos)

    lines = infos.splitlines()
    if "No such file or directory" in lines[-1]:
        raise IOError(
            (
                "MoviePy error: the file %s could not be found!\n"
                "Please check that you entered the correct "
                "path."
            )
            % filename
        )

    result = dict()

    result["duration"] = None

    if check_duration:
        try:
            keyword = "frame=" if is_GIF else "Duration: "
            index = -1 if is_GIF else 0
            line = [l for l in lines if keyword in l][index]
            match = re.findall("([0-9][0-9]:[0-9][0-9]:[0-9][0-9].[0-9][0-9])", line)[0]
            result["duration"] = cvsecs(match)
        except:
            raise IOError(
                (
                    "MoviePy error: failed to read the duration of file %s.\n"
                    "Here are the file infos returned by ffmpeg:\n\n%s"
                )
                % (filename, infos)
            )

    lines_video = [l for l in lines if " Video: " in l and re.search("\d+x\d+", l)]

    result["video_found"] = lines_video != []

    if result["video_found"]:
        try:
            line = lines_video[0]

            match = re.search(" [0-9]*x[0-9]*(,| )", line)
            s = list(map(int, line[match.start() : match.end() - 1].split("x")))
            result["video_size"] = s
        except:
            raise IOError(
                (
                    "MoviePy error: failed to read video dimensions in file %s.\n"
                    "Here are the file infos returned by ffmpeg:\n\n%s"
                )
                % (filename, infos)
            )

        def get_tbr():
            match = re.search("( [0-9]*.| )[0-9]* tbr", line)

            s_tbr = line[match.start() : match.end()].split(" ")[1]
            if "k" in s_tbr:
                tbr = float(s_tbr.replace("k", "")) * 1000
            else:
                tbr = float(s_tbr)
            return tbr

        def get_fps():
            match = re.search("( [0-9]*.| )[0-9]* fps", line)
            fps = float(line[match.start() : match.end()].split(" ")[1])
            return fps

        if fps_source == "tbr":
            try:
                result["video_fps"] = get_tbr()
            except:
                result["video_fps"] = get_fps()

        elif fps_source == "fps":
            try:
                result["video_fps"] = get_fps()
            except:
                result["video_fps"] = get_tbr()

        coef = 1000.0 / 1001.0
        fps = result["video_fps"]
        for x in [23, 24, 25, 30, 50]:
            if (fps != x) and abs(fps - x * coef) < 0.01:
                result["video_fps"] = x * coef

        if check_duration:
            result["video_nframes"] = int(result["duration"] * result["video_fps"]) + 1
            result["video_duration"] = result["duration"]
        else:
            result["video_nframes"] = 1
            result["video_duration"] = None

        try:
            rotation_lines = [
                l for l in lines if "rotate          :" in l and re.search("\d+$", l)
            ]
            if len(rotation_lines):
                rotation_line = rotation_lines[0]
                match = re.search("\d+$", rotation_line)
                result["video_rotation"] = int(
                    rotation_line[match.start() : match.end()]
                )
            else:
                result["video_rotation"] = 0
        except:
            raise IOError(
                (
                    "MoviePy error: failed to read video rotation in file %s.\n"
                    "Here are the file infos returned by ffmpeg:\n\n%s"
                )
                % (filename, infos)
            )

    lines_audio = [l for l in lines if " Audio: " in l]

    result["audio_found"] = lines_audio != []

    if result["audio_found"]:
        line = lines_audio[0]
        try:
            match = re.search(" [0-9]* Hz", line)
            hz_string = line[
                match.start() + 1 : match.end() - 3
            ]  # Removes the 'hz' from the end
            result["audio_fps"] = int(hz_string)
        except:
            result["audio_fps"] = "unknown"

    return result
