import discord
from discord.ext import commands

# misc imports
import numpy as np
import cv2
import concurrent.futures
import math
from functools import partial
from io import BytesIO


def apply_transform(transform, buffer, size, max_size, ext, is_png, *args):
    img_bytes = np.asarray(bytearray(buffer.read()), np.uint8)
    result = cv2.imdecode(img_bytes, cv2.IMREAD_UNCHANGED)
    ratio = (max_size / size) * 100 if size > max_size else None

    if ratio:
        _, buffer = cv2.imencode(f".{ext}", result,
                                 (cv2.CV_IMWRITE_PNG_COMPRESSION if is_png else
                                  cv2.IMWRITE_JPEG_QUALITY, ratio))
        result = cv2.imdecode(buffer, cv2.IMREAD_UNCHANGED)

    result = transform(result, *args)

    _, buffer = cv2.imencode(f".{ext}", result)

    return buffer


async def fitler_image(loop, transform, ctx, history_limit, max_size, *args):

    att = await get_attachment(ctx, history_limit)
    if att is None:
        await ctx.send("no image could be found (only attached image files"
                       " can be detected) or message could not be found")
        return

    await ctx.trigger_typing()
    buffer = BytesIO()
    await att.save(fp=buffer)

    original_name, ext = att.filename.rsplit(".", 1)
    ext = ext.lower()
    if ext in ("jpeg", "jpg"):
        is_png = False
    elif ext in ("png"):
        is_png = True
    else:
        await ctx.send("image format not supported.")
        return

    fn = f"{original_name}-{transform.__name__}.{ext}"

    try:
        with concurrent.futures.ProcessPoolExecutor() as pool:
            buffer = await loop.run_in_executor(
                pool,
                partial(apply_transform, transform, buffer, att.size, max_size,
                        ext, is_png, *args))

    except Exception as exc:    # TODO: Narrow the exception
        await ctx.send("an error has occurred.")
        raise exc

    else:
        await ctx.message.delete()
        await ctx.send(file=discord.File(fp=BytesIO(buffer), filename=fn))


async def get_attachment(ctx: commands.Context, lim: int):
    """
    Returns either the attachment of the message to which
    the invoking message is replying to, or, if that fails
    the attachment of the most recent of the last 100 messages.
    If no such message exists, returns None.
    """
    if (ctx.message.reference and ctx.message.reference.resolved
            and ctx.message.reference.resolved.attachments):
        return ctx.message.reference.resolved.attachments[0]
    async for msg in ctx.message.channel.history(limit=lim):
        if msg.attachments:
            return msg.attachments[0]
    return None


def cv_linear_polar(image, flags):
    h, w = image.shape[:2]
    r = math.sqrt(w**2 + h**2) / 2
    return cv2.linearPolar(image, (w / 2, h / 2), r, flags)


def polar(image):
    return np.rot90(
        cv_linear_polar(image, cv2.INTER_LINEAR + cv2.WARP_FILL_OUTLIERS), -1)


def cart(image):
    return cv_linear_polar(
        np.rot90(image),
        cv2.INTER_LINEAR + cv2.WARP_FILL_OUTLIERS + cv2.WARP_INVERSE_MAP)


def blur(image, iterations: int, max_iter: int):
    iterations = max(0, min(iterations, max_iter))
    for _ in range(iterations):
        image = cv2.GaussianBlur(image, (5, 5), 0)
    return image


def hblur(image, radius: int, max_rad: int):
    radius = max(1, min(radius, max_rad))
    image = cv2.blur(image, (radius, 1))
    return image


def vblur(image, radius: int, max_rad: int):
    radius = max(1, min(radius, max_rad))
    image = cv2.blur(image, (1, radius))
    return image


def rblur(image, radius: int, max_rad: int):
    radius = max(1, min(radius, max_rad))
    image = cv_linear_polar(image, cv2.INTER_LINEAR + cv2.WARP_FILL_OUTLIERS)
    image = cv2.blur(image, (radius, 1))
    image = cv_linear_polar(
        image,
        cv2.INTER_LINEAR + cv2.WARP_FILL_OUTLIERS + cv2.WARP_INVERSE_MAP)
    return image


def cblur(image, radius: int, max_rad: int):
    radius = max(1, min(radius, max_rad))
    half_radius = radius // 2

    # determine values for padding
    height, width = image.shape[:2]
    r = math.sqrt(width**2 + height**2) // 2
    v_pad = int(r - height / 2)
    h_pad = int(r - width / 2)

    # pad border to avoid black regions when transforming image back to
    # normal
    image = cv2.copyMakeBorder(image, v_pad, v_pad, h_pad, h_pad,
                               cv2.BORDER_REPLICATE)
    image = cv_linear_polar(image, cv2.INTER_LINEAR + cv2.WARP_FILL_OUTLIERS)

    # wrap border to avoid the sharp horizontal line when transforming
    # image back to normal
    image = cv2.copyMakeBorder(image, half_radius, half_radius, half_radius,
                               half_radius, cv2.BORDER_WRAP)
    image = cv2.blur(image, (1, radius))
    image = image[half_radius:-half_radius, half_radius:-half_radius]
    image = cv_linear_polar(
        image,
        cv2.INTER_LINEAR + cv2.WARP_FILL_OUTLIERS + cv2.WARP_INVERSE_MAP)
    image = image[v_pad:-v_pad, h_pad:-h_pad]

    return image


def deepfry(image, iterations: int, max_iter: int):
    iterations = max(0, min(iterations, max_iter))
    kernel = np.array([[0, 0, 0], [0, 1, 0], [
        0, 0, 0
    ]]) + np.array([[0, -1, 0], [-1, 4, -1], [0, -1, 0]]) * 0.3

    for _ in range(iterations):
        std = int(np.std(image))

        # Contrast
        image = cv2.addWeighted(image, 0.9, image, 0, std * 0.3)

        # Sharpness
        image = cv2.filter2D(image, 0, kernel)

        # Saturation
        image = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        image[:, :, 1:] = cv2.add(image[:, :, 1:], image[:, :, 1:])
        image = cv2.cvtColor(image, cv2.COLOR_HSV2BGR)

    return image


def noise(image, iterations: int, max_iter: int):
    iterations = max(0, min(iterations, max_iter))

    for _ in range(iterations):
        noised = np.std(image) * np.random.random(image.shape)
        image = cv2.add(image, noised.astype("uint8"))
        image = cv2.addWeighted(image, 1, image, 0, -np.std(image) * 0.49)

    return image
