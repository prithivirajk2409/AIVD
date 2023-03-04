import decorator
from moviepy.tools import cvsecs

@decorator.decorator
def outplace(f, clip, *a, **k):
    newclip = clip.copy()
    f(newclip, *a, **k)
    return newclip


@decorator.decorator
def convert_masks_to_RGB(f, clip, *a, **k):
    if clip.ismask:
        clip = clip.to_RGB()
    return f(clip, *a, **k)


@decorator.decorator
def apply_to_mask(f, clip, *a, **k):
    newclip = f(clip, *a, **k)
    if getattr(newclip, "mask", None):
        newclip.mask = f(newclip.mask, *a, **k)
    return newclip


@decorator.decorator
def apply_to_audio(f, clip, *a, **k):
    newclip = f(clip, *a, **k)
    if getattr(newclip, "audio", None):
        newclip.audio = f(newclip.audio, *a, **k)
    return newclip


@decorator.decorator
def requires_duration(f, clip, *a, **k):
    if clip.duration is None:
        raise ValueError("Attribute 'duration' not set")
    else:
        return f(clip, *a, **k)


def preprocess_args(fun, varnames):
    def wrapper(f, *a, **kw):
        if hasattr(f, "func_code"):
            func_code = f.func_code  # Python 2
        else:
            func_code = f.__code__  # Python 3

        names = func_code.co_varnames
        new_a = [
            fun(arg) if (name in varnames) else arg for (arg, name) in zip(a, names)
        ]
        new_kw = {k: fun(v) if k in varnames else v for (k, v) in kw.items()}
        return f(*new_a, **new_kw)

    return decorator.decorator(wrapper)


def convert_to_seconds(varnames):
    return preprocess_args(cvsecs, varnames)


@decorator.decorator
def use_clip_fps_by_default(f, clip, *a, **k):
    def fun(fps):
        if fps is not None:
            return fps
        elif getattr(clip, "fps", None):
            return clip.fps
        raise AttributeError(
            "No 'fps' (frames per second) attribute specified"
            " for function %s and the clip has no 'fps' attribute. Either"
            " provide e.g. fps=24 in the arguments of the function, or define"
            " the clip's fps with `clip.fps=24`" % f.__name__
        )

    if hasattr(f, "func_code"):
        func_code = f.func_code  # Python 2
    else:
        func_code = f.__code__  # Python 3

    names = func_code.co_varnames[1:]

    new_a = [fun(arg) if (name == "fps") else arg for (arg, name) in zip(a, names)]
    new_kw = {k: fun(v) if k == "fps" else v for (k, v) in k.items()}

    return f(clip, *new_a, **new_kw)
