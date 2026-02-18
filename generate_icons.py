#!/usr/bin/env python3
"""Generate PNG icons for Reddit User Insight extension.
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

    # PNG signature
    sig = b'\x89PNG\r\n\x1a\n'

    # IHDR
    ihdr = struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0)  # 8-bit RGBA

    # IDAT - filter type 0 (none) for each row
    raw = b''
    for y in range(height):
        raw += b'\x00'  # filter type
        for x in range(width):
            idx = (y * width + x) * 4
            raw += bytes(pixels[idx:idx+4])

    compressed = zlib.compress(raw)

    return sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')


def draw_icon(size):
    """Draw the Reddit User Insight icon - a magnifying glass with a user silhouette."""
    pixels = [0] * (size * size * 4)

    cx, cy = size / 2, size / 2
    radius = size * 0.38

    def set_pixel(x, y, r, g, b, a=255):
        if 0 <= x < size and 0 <= y < size:
            idx = (int(y) * size + int(x)) * 4
            # Alpha blend
            old_a = pixels[idx + 3]
            if old_a == 0:
                pixels[idx] = r
                pixels[idx+1] = g
                pixels[idx+2] = b
                pixels[idx+3] = a
            else:
                # Simple over compositing
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
                    # Anti-alias at edges
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
                    # Anti-alias
                    edge_dist = min(dist - inner, outer - dist)
                    if edge_dist < 1:
                        aa = max(0, min(255, int(edge_dist * 255)))
                        set_pixel(x, y, red, green, blue, int(alpha * aa / 255))
                    else:
                        set_pixel(x, y, red, green, blue, alpha)

    # Background circle (Reddit orange)
    draw_circle_filled(cx, cy, size * 0.46, 255, 69, 0, 255)

    # Inner white circle (lens area)
    lens_cx = cx - size * 0.06
    lens_cy = cy - size * 0.06
    lens_r = size * 0.26
    draw_circle_filled(lens_cx, lens_cy, lens_r, 255, 255, 255, 255)

    # Lens border
    thickness = max(1.5, size * 0.04)
    draw_circle_ring(lens_cx, lens_cy, lens_r, thickness, 200, 40, 0, 255)

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
                    set_pixel(int(hx + dx * 0.5), int(hy + dy * 0.5), 200, 40, 0)

    # User silhouette (head) inside lens
    head_r = lens_r * 0.22
    head_cx = lens_cx
    head_cy = lens_cy - lens_r * 0.18
    draw_circle_filled(head_cx, head_cy, head_r, 80, 80, 80, 220)

    # User silhouette (body arc)
    body_cy = lens_cy + lens_r * 0.22
    body_r = lens_r * 0.35
    for y in range(size):
        for x in range(size):
            dist = math.sqrt((x - head_cx)**2 + (y - body_cy)**2)
            if dist <= body_r and y >= body_cy and y <= body_cy + body_r * 0.7:
                edge = min(dist, body_r - dist) if dist < body_r else 0
                if edge < 1:
                    set_pixel(x, y, 80, 80, 80, int(220 * edge))
                else:
                    set_pixel(x, y, 80, 80, 80, 220)

    # Small colored dots (green, yellow, red) at bottom right of icon
    dot_r = size * 0.06
    dot_spacing = size * 0.15

    # Green dot
    gx = cx + size * 0.15
    gy = cy + size * 0.30
    draw_circle_filled(gx, gy, dot_r, 70, 209, 96, 255)

    return pixels


for icon_size in [16, 48, 128]:
    px = draw_icon(icon_size)
    png_data = create_png(icon_size, icon_size, px)
    path = os.path.join(os.path.dirname(__file__), 'icons', f'icon{icon_size}.png')
    with open(path, 'wb') as f:
        f.write(png_data)
    print(f'Generated {path} ({len(png_data)} bytes)')
