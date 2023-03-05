import numpy as np

def blit(im1, im2, pos=None, mask=None, ismask=False):
    if pos is None:
        pos = [0, 0]

    xp, yp = pos
    x1 = max(0, -xp)
    y1 = max(0, -yp)
    h1, w1 = im1.shape[:2]
    h2, w2 = im2.shape[:2]
    xp2 = min(w2, xp + w1)
    yp2 = min(h2, yp + h1)
    x2 = min(w1, w2 - xp)
    y2 = min(h1, h2 - yp)
    xp1 = max(0, xp)
    yp1 = max(0, yp)

    if (xp1 >= xp2) or (yp1 >= yp2):
        return im2

    blitted = im1[y1:y2, x1:x2]

    new_im2 = +im2

    if mask is None:
        new_im2[yp1:yp2, xp1:xp2] = blitted
    else:
        mask = mask[y1:y2, x1:x2]
        if len(im1.shape) == 3:
            mask = np.dstack(3 * [mask])
        blit_region = new_im2[yp1:yp2, xp1:xp2]
        new_im2[yp1:yp2, xp1:xp2] = 1.0 * mask * blitted + (1.0 - mask) * blit_region

    return new_im2.astype("uint8") if (not ismask) else new_im2
