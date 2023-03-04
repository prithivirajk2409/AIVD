def crop(
    clip,
    x1=None,
    y1=None,
    x2=None,
    y2=None,
    width=None,
    height=None,
    x_center=None,
    y_center=None,
):


    if width and x1 is not None:
        x2 = x1 + width
    elif width and x2 is not None:
        x1 = x2 - width

    if height and y1 is not None:
        y2 = y1 + height
    elif height and y2 is not None:
        y1 = y2 - height

    if x_center:
        x1, x2 = x_center - width / 2, x_center + width / 2

    if y_center:
        y1, y2 = y_center - height / 2, y_center + height / 2

    x1 = x1 or 0
    y1 = y1 or 0
    x2 = x2 or clip.size[0]
    y2 = y2 or clip.size[1]

    return clip.fl_image(
        lambda pic: pic[int(y1) : int(y2), int(x1) : int(x2)], apply_to=["mask"]
    )
