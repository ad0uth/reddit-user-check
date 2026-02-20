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
TRUST_RED = (229, 83, 75)


def draw_icon(size):
    """Draw the TrueVoice icon — bot face with prohibited sign.
    Size-aware: simplifies details at small sizes for clarity."""
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

    def fill_rounded_rect(rcx, rcy, hw, hh, rad, r, g, b):
        """Draw a filled rounded rectangle."""
        for y in range(size):
            for x in range(size):
                px, py = abs(x - rcx), abs(y - rcy)
                inside = False
                edge_d = -999
                if px <= hw - rad and py <= hh:
                    inside = True
                    edge_d = min(hh - py, hw - rad - px)
                elif px <= hw and py <= hh - rad:
                    inside = True
                    edge_d = min(hw - px, hh - rad - py)
                elif px > hw - rad and py > hh - rad:
                    d = math.sqrt((px - (hw - rad))**2 + (py - (hh - rad))**2)
                    edge_d = rad - d
                    inside = edge_d >= 0
                if inside:
                    if edge_d < 1:
                        aa = max(0, min(255, int(edge_d * 255)))
                        set_pixel(x, y, r, g, b, aa)
                    else:
                        set_pixel(x, y, r, g, b, 255)

    def fill_circle(fcx, fcy, r, red, green, blue):
        for y in range(size):
            for x in range(size):
                d = math.sqrt((x - fcx)**2 + (y - fcy)**2)
                if d <= r:
                    a = 255 if d <= r - 1 else max(0, min(255, int((r - d) * 255)))
                    set_pixel(x, y, red, green, blue, a)

    BOT_BODY = (90, 105, 140)       # bot head — steel blue-gray
    BOT_DARK = (55, 65, 90)         # antenna/ear/mouth
    EYE_WHITE = (255, 255, 255)     # bright white eyes for contrast
    PROHIBIT_RED = (210, 40, 35)    # strong red

    # ============================================================
    # Bot face — centered, fills the middle of the icon
    # ============================================================
    # Head is a rounded rectangle, shifted slightly down for antenna room
    head_cy = cy + size * 0.05
    head_hw = size * 0.28   # half-width
    head_hh = size * 0.22   # half-height
    head_rad = size * 0.10  # generous rounding to look friendly/robotic

    fill_rounded_rect(cx, head_cy, head_hw, head_hh, head_rad, *BOT_BODY)

    # --- Eyes: two bright circles that read even at 16px ---
    eye_r = max(1.4, size * 0.065)
    eye_y = head_cy - size * 0.03
    eye_spacing = size * 0.135
    for side in [-1, 1]:
        fill_circle(cx + side * eye_spacing, eye_y, eye_r, *EYE_WHITE)

    # --- Details that only appear at larger sizes ---
    if size >= 32:
        # Antenna stalk
        ant_base_y = head_cy - head_hh
        ant_top_y = ant_base_y - size * 0.12
        ant_thick = max(1.0, size * 0.025)
        draw_line(cx, ant_base_y, cx, ant_top_y, *BOT_DARK, ant_thick)
        # Antenna ball
        fill_circle(cx, ant_top_y, max(1.5, size * 0.04), *EYE_WHITE)

        # Ears
        ear_w = max(1, size * 0.04)
        ear_hh = size * 0.09
        for side in [-1, 1]:
            ear_cx = cx + side * (head_hw + ear_w + 0.5)
            fill_rounded_rect(ear_cx, head_cy, ear_w, ear_hh, ear_w * 0.5, *BOT_DARK)

        # Mouth — simple horizontal bar
        mouth_y = head_cy + size * 0.10
        mouth_hw = size * 0.13
        mouth_thick = max(1.0, size * 0.02)
        draw_line(cx - mouth_hw, mouth_y, cx + mouth_hw, mouth_y, *BOT_DARK, mouth_thick)

    if size >= 64:
        # Mouth grill lines at large sizes
        mouth_y = head_cy + size * 0.10
        mouth_hw = size * 0.13
        for i in range(3):
            lx = cx - mouth_hw + (2 * mouth_hw) * (i + 1) / 4
            draw_line(lx, mouth_y - size * 0.025, lx, mouth_y + size * 0.025,
                      *BOT_DARK, max(0.8, size * 0.012))

    # ============================================================
    # Prohibited sign — red circle outline + diagonal slash
    # Drawn last so it's on top of everything
    # ============================================================
    ban_r = size * 0.43
    ban_thick = max(1.5, size * 0.055)

    # Red circle outline
    for y in range(size):
        for x in range(size):
            d = abs(math.sqrt((x - cx)**2 + (y - cy)**2) - ban_r)
            if d <= ban_thick:
                a = 255 if d <= ban_thick - 0.8 else max(0, min(255, int((ban_thick - d) / 0.8 * 255)))
                set_pixel(x, y, *PROHIBIT_RED, a)

    # Diagonal slash — from top-right to bottom-left
    slash_len = ban_r * 0.88
    angle = math.radians(45)
    sx1 = cx + slash_len * math.cos(angle)
    sy1 = cy - slash_len * math.sin(angle)
    sx2 = cx - slash_len * math.cos(angle)
    sy2 = cy + slash_len * math.sin(angle)
    draw_line(sx1, sy1, sx2, sy2, *PROHIBIT_RED, ban_thick)

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
