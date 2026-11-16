import struct
import sys
import zlib

USAGE = "Usage: png_pixels.py <png> <x,y>... (game coordinates, origin bottom left)"


def main():
    if len(sys.argv) < 3:
        sys.exit(USAGE)
    height, bytes_per_pixel, rows = decode_png(sys.argv[1])
    for point in sys.argv[2:]:
        x, y = (int(value) for value in point.split(","))
        row = rows[height - 1 - y]
        print(f"{x},{y} rgb={tuple(row[x * bytes_per_pixel:x * bytes_per_pixel + 3])}")


def decode_png(path):
    with open(path, "rb") as file:
        chunks = read_chunks(file.read()[8:])
    width, height, depth, color_type = struct.unpack(">IIBB", chunks["IHDR"][:10])
    channels = {2: 3, 3: 1, 6: 4}.get(color_type)
    allowed_depths = (1, 2, 4, 8) if color_type == 3 else (8,)
    if channels is None or depth not in allowed_depths:
        sys.exit(f"Expected an 8-bit RGB or RGBA PNG or a palette PNG, got depth {depth} color type {color_type}")
    stride = (width * channels * depth + 7) // 8
    # Filters work on whole pixels, or on single bytes when pixels are packed into bytes
    bytes_per_pixel = max(1, channels * depth // 8)
    rows = unfilter(zlib.decompress(chunks["IDAT"]), stride, height, bytes_per_pixel)
    # DragonRuby saves screenshots with at most 256 colors as palette PNGs, with
    # 1, 2, 4 or 8 bits per pixel depending on the number of colors
    if color_type == 3:
        rows = [expand_palette(palette_indices(row, width, depth), chunks["PLTE"]) for row in rows]
        bytes_per_pixel = 3
    return height, bytes_per_pixel, rows


def palette_indices(row, width, depth):
    pixels_per_byte = 8 // depth
    mask = (1 << depth) - 1
    return [
        (row[x // pixels_per_byte] >> (8 - depth * (x % pixels_per_byte + 1))) & mask
        for x in range(width)
    ]


def expand_palette(indices, palette):
    return bytearray(b"".join(palette[index * 3:index * 3 + 3] for index in indices))


def read_chunks(data):
    chunks = {"IDAT": b""}
    while data:
        length, kind = struct.unpack(">I4s", data[:8])
        body = data[8:8 + length]
        kind = kind.decode()
        chunks[kind] = chunks["IDAT"] + body if kind == "IDAT" else body
        data = data[12 + length:]
    return chunks


def unfilter(raw, stride, height, bytes_per_pixel):
    rows = []
    previous = bytearray(stride)
    position = 0
    for _ in range(height):
        filter_type = raw[position]
        line = bytearray(raw[position + 1:position + 1 + stride])
        position += 1 + stride
        for i in range(stride):
            left = line[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
            up = previous[i]
            upper_left = previous[i - bytes_per_pixel] if i >= bytes_per_pixel else 0
            line[i] = (line[i] + predictor(filter_type, left, up, upper_left)) & 0xFF
        rows.append(line)
        previous = line
    return rows


def predictor(filter_type, left, up, upper_left):
    if filter_type == 1:
        return left
    if filter_type == 2:
        return up
    if filter_type == 3:
        return (left + up) // 2
    if filter_type == 4:
        return paeth(left, up, upper_left)
    return 0


def paeth(left, up, upper_left):
    estimate = left + up - upper_left
    distance_left = abs(estimate - left)
    distance_up = abs(estimate - up)
    distance_upper_left = abs(estimate - upper_left)
    if distance_left <= distance_up and distance_left <= distance_upper_left:
        return left
    return up if distance_up <= distance_upper_left else upper_left


main()
