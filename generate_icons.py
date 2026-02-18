#!/usr/bin/env python3
"""Generate PNG icons for User Insight for Reddit extension.
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
BRAND_PRIMARY = (74, 144, 217)    # #4A90D9 - trustworthy blue
BRAND_SECONDARY = (108, 92, 231)  # #6C5CE7 - insight purple
BRAND_DARK = (45, 55, 120)        # dark accent for handle/borders
TRUST_GREEN = (70, 209, 96)
TRUST_YELLOW = (240, 180, 41)
TRUST_RED = (229, 83, 75)


def draw_icon(size):
    """Draw the extension icon — shield with magnifying glass motif."""
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

    def draw_circle_ring(cx, cy, r, thickness, red, green, blue, alpha=255):
        for y in range(size):
            for x in range(size):
                dist = math.sqrt((x - cx)**2 + (y - cy)**2)
                inner = r - thickness/2
                outer = r + thickness/2
                if inner <= dist <= outer:
                    edge_dist = min(dist - inner, outer - dist)
                    if edge_dist < 1:
                        aa = max(0, min(255, int(edge_dist * 255)))
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

    # Inner white circle (lens area)
    lens_cx = cx - size * 0.06
    lens_cy = cy - size * 0.06
    lens_r = size * 0.26
    draw_circle_filled(lens_cx, lens_cy, lens_r, 255, 255, 255, 255)

    # Lens border
    thickness = max(1.5, size * 0.04)
    draw_circle_ring(lens_cx, lens_cy, lens_r, thickness, BRAND_DARK[0], BRAND_DARK[1], BRAND_DARK[2], 255)

    # Handle of magnifying glass
    handle_start_x = lens_cx + lens_r * 0.65
    handle_start_y = lens_cy + lens_r * 0.65
    handle_len = size * 0.22
    handle_thickness = max(2, size * 0.07)

    for t in range(int(handle_len * 3)):
        frac = t / (handle_len * 3)
        hx = handle_start_x + handle_len * frac
        hy = handle_start_y + handle_len * frac
        for dx in range(-int(handle_thickness), int(handle_thickness) + 1):
            for dy in range(-int(handle_thickness), int(handle_thickness) + 1):
                if dx*dx + dy*dy <= handle_thickness * handle_thickness:
                    set_pixel(int(hx + dx * 0.5), int(hy + dy * 0.5),
                              BRAND_DARK[0], BRAND_DARK[1], BRAND_DARK[2])

    # User silhouette (head) inside lens
    head_r = lens_r * 0.22
    head_cx = lens_cx
    head_cy = lens_cy - lens_r * 0.18
    draw_circle_filled(head_cx, head_cy, head_r, 74, 85, 120, 220)

    # User silhouette (body arc)
    body_cy = lens_cy + lens_r * 0.22
    body_r = lens_r * 0.35
    for y in range(size):
        for x in range(size):
            dist = math.sqrt((x - head_cx)**2 + (y - body_cy)**2)
            if dist <= body_r and y >= body_cy and y <= body_cy + body_r * 0.7:
                edge = min(dist, body_r - dist) if dist < body_r else 0
                if edge < 1:
                    set_pixel(x, y, 74, 85, 120, int(220 * edge))
                else:
                    set_pixel(x, y, 74, 85, 120, 220)

    # Three trust dots at bottom
    dot_r = size * 0.055
    dot_y = cy + size * 0.32
    dot_gap = size * 0.12

    draw_circle_filled(cx - dot_gap, dot_y, dot_r, *TRUST_GREEN, 255)
    draw_circle_filled(cx, dot_y, dot_r, *TRUST_YELLOW, 255)
    draw_circle_filled(cx + dot_gap, dot_y, dot_r, *TRUST_RED, 255)

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
