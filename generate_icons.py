#!/usr/bin/env python3
"""Generate PNG icons for TrueVoice for Reddit extension.
Uses only stdlib (struct, zlib) - no external dependencies."""

import struct
import zlib
import os
import math


def create_png(width, height, pixels):
    """Create a PNG file from RGBA pixel data."""
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(c) & 0xffffffff)
        return struct.pack('>I', len(data)) + c + crc

    sig = b'\x89PNG\r\n\x1a\n'
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)

    raw = b''
    for y in range(height):
        raw += b'\x00'
        for x in range(width):
            idx = (y * width + x) * 4
            raw += bytes(pixels[idx:idx+4])

    compressed = zlib.compress(raw)
    return sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')


def lerp_color(c1, c2, t):
    """Linearly interpolate between two RGB tuples."""
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# Brand colors
BRAND_PRIMARY = (59, 130, 246)    # #3B82F6 - vibrant blue
BRAND_SECONDARY = (139, 92, 246)  # #8B5CF6 - vivid purple
BRAND_DARK = (30, 41, 82)         # dark accent
TRUST_GREEN = (70, 209, 96)
TRUST_YELLOW = (240, 180, 41)
TRUST_RED = (229, 83, 75)


def draw_icon(size):
    """Draw the TrueVoice icon — speech bubble with checkmark."""
    pixels = [0] * (size * size * 4)
    cx, cy = size / 2, size / 2

    def set_pixel(x, y, r, g, b, a=255):
        if 0 <= x < size and 0 <= y < size:
            idx = (int(y) * size + int(x)) * 4
            old_a = pixels[idx + 3]
            if old_a == 0:
                pixels[idx] = r
                pixels[idx+1] = g
                pixels[idx+2] = b
                pixels[idx+3] = a
            else:
                fa = a / 255
                pixels[idx] = int(pixels[idx] * (1-fa) + r * fa)
                pixels[idx+1] = int(pixels[idx+1] * (1-fa) + g * fa)
                pixels[idx+2] = int(pixels[idx+2] * (1-fa) + b * fa)
                pixels[idx+3] = min(255, old_a + a)

    def draw_circle_filled(cx, cy, r, red, green, blue, alpha=255):
        for y in range(size):
            for x in range(size):
                dist = math.sqrt((x - cx)**2 + (y - cy)**2)
                if dist <= r:
                    if dist > r - 1:
                        aa = max(0, min(255, int((r - dist) * 255)))
                        set_pixel(x, y, red, green, blue, int(alpha * aa / 255))
                    else:
                        set_pixel(x, y, red, green, blue, alpha)

    # Background — gradient circle (blue to purple, top-left to bottom-right)
    bg_r = size * 0.46
    for y in range(size):
        for x in range(size):
            dist = math.sqrt((x - cx)**2 + (y - cy)**2)
            if dist <= bg_r:
                t = ((x + y) / (size * 2))  # diagonal gradient
                c = lerp_color(BRAND_PRIMARY, BRAND_SECONDARY, t)
                if dist > bg_r - 1:
                    aa = max(0, min(255, int((bg_r - dist) * 255)))
                    set_pixel(x, y, c[0], c[1], c[2], aa)
                else:
                    set_pixel(x, y, c[0], c[1], c[2], 255)

    # --- Speech bubble (white, rounded rectangle with tail) ---
    bubble_cx = cx
    bubble_cy = cy - size * 0.06
    bubble_w = size * 0.52   # half-width
    bubble_h = size * 0.34   # half-height
    bubble_r = size * 0.12   # corner radius

    # Draw rounded rectangle for speech bubble
    for y in range(size):
        for x in range(size):
            px = x - bubble_cx
            py = y - bubble_cy

            # Check if inside the rounded rectangle
            inside = False
            edge_dist = 999

            # Inner rectangle areas (no rounding needed)
            if abs(px) <= bubble_w - bubble_r and abs(py) <= bubble_h:
                inside = True
                edge_dist = min(bubble_h - abs(py), bubble_w - bubble_r - abs(px))
            elif abs(px) <= bubble_w and abs(py) <= bubble_h - bubble_r:
                inside = True
                edge_dist = min(bubble_w - abs(px), bubble_h - bubble_r - abs(py))
            else:
                # Check corner circles
                corners = [
                    (bubble_cx - bubble_w + bubble_r, bubble_cy - bubble_h + bubble_r),
                    (bubble_cx + bubble_w - bubble_r, bubble_cy - bubble_h + bubble_r),
                    (bubble_cx - bubble_w + bubble_r, bubble_cy + bubble_h - bubble_r),
                    (bubble_cx + bubble_w - bubble_r, bubble_cy + bubble_h - bubble_r),
                ]
                for ccx, ccy in corners:
                    d = math.sqrt((x - ccx)**2 + (y - ccy)**2)
                    if d <= bubble_r:
                        inside = True
                        edge_dist = bubble_r - d
                        break

            if inside:
                if edge_dist < 1:
                    aa = max(0, min(255, int(edge_dist * 255)))
                    set_pixel(x, y, 255, 255, 255, aa)
                else:
                    set_pixel(x, y, 255, 255, 255, 255)

    # Speech bubble tail (small triangle pointing down-left)
    tail_x = bubble_cx - size * 0.12
    tail_y = bubble_cy + bubble_h
    tail_w = size * 0.10
    tail_h = size * 0.10

    for y in range(max(0, int(tail_y)), min(size, int(tail_y + tail_h + 1))):
        for x in range(max(0, int(tail_x - tail_w)), min(size, int(tail_x + tail_w))):
            # Triangle: narrows as y increases, shifts left
            progress = (y - tail_y) / tail_h if tail_h > 0 else 0
            if progress < 0 or progress > 1:
                continue
            left_edge = tail_x - tail_w * 0.3 - tail_w * 0.5 * progress
            right_edge = tail_x + tail_w * 0.3 - tail_w * 0.2 * progress
            if left_edge <= x <= right_edge:
                set_pixel(x, y, 255, 255, 255, 255)

    # --- Checkmark inside the bubble ---
    # Draw a bold checkmark
    check_cx = bubble_cx
    check_cy = bubble_cy
    check_scale = size * 0.015

    # Checkmark: short stroke going down-right, then long stroke going up-right
    # Short leg: from (-3, 0) to (0, 3)
    # Long leg: from (0, 3) to (5, -3)
    thickness = max(1.5, size * 0.05)

    def draw_line(x1, y1, x2, y2, r, g, b, thick):
        length = math.sqrt((x2-x1)**2 + (y2-y1)**2)
        if length == 0:
            return
        steps = int(length * 3) + 1
        for i in range(steps + 1):
            t = i / steps
            lx = x1 + (x2 - x1) * t
            ly = y1 + (y2 - y1) * t
            for dy in range(-int(thick)-1, int(thick)+2):
                for dx in range(-int(thick)-1, int(thick)+2):
                    if dx*dx + dy*dy <= thick * thick:
                        set_pixel(int(lx + dx), int(ly + dy), r, g, b)

    # Checkmark points (relative to bubble center)
    p1_x = check_cx - size * 0.12
    p1_y = check_cy + size * 0.01
    p2_x = check_cx - size * 0.02
    p2_y = check_cy + size * 0.12
    p3_x = check_cx + size * 0.16
    p3_y = check_cy - size * 0.12

    draw_line(p1_x, p1_y, p2_x, p2_y, TRUST_GREEN[0], TRUST_GREEN[1], TRUST_GREEN[2], thickness)
    draw_line(p2_x, p2_y, p3_x, p3_y, TRUST_GREEN[0], TRUST_GREEN[1], TRUST_GREEN[2], thickness)

    return pixels


# Generate extension icons
icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'icons')
os.makedirs(icons_dir, exist_ok=True)

for icon_size in [16, 48, 128]:
    px = draw_icon(icon_size)
    png_data = create_png(icon_size, icon_size, px)
    path = os.path.join(icons_dir, f'icon{icon_size}.png')
    with open(path, 'wb') as f:
        f.write(png_data)
    print(f'Generated {path} ({len(png_data)} bytes)')
