#!/usr/bin/env python3
"""Generate Chrome Web Store promotional tile (440x280) for TrueVoice for Reddit.
Uses only stdlib - no external dependencies."""

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
    return tuple(int(a + (b - a) * max(0, min(1, t))) for a, b in zip(c1, c2))


# Brand colors
BRAND_PRIMARY = (59, 130, 246)
BRAND_SECONDARY = (139, 92, 246)
BG_DARK = (20, 24, 48)
BG_MID = (35, 40, 70)
WHITE = (255, 255, 255)
TRUST_GREEN = (70, 209, 96)
TRUST_YELLOW = (240, 180, 41)
TRUST_RED = (229, 83, 75)


def draw_promo(width, height):
    """Draw the 440x280 promotional tile."""
    pixels = [0] * (width * height * 4)

    def set_pixel(x, y, r, g, b, a=255):
        xi, yi = int(x), int(y)
        if 0 <= xi < width and 0 <= yi < height:
            idx = (yi * width + xi) * 4
            if pixels[idx + 3] == 0:
                pixels[idx] = r
                pixels[idx+1] = g
                pixels[idx+2] = b
                pixels[idx+3] = a
            else:
                fa = a / 255
                pixels[idx] = int(pixels[idx] * (1-fa) + r * fa)
                pixels[idx+1] = int(pixels[idx+1] * (1-fa) + g * fa)
                pixels[idx+2] = int(pixels[idx+2] * (1-fa) + b * fa)
                pixels[idx+3] = min(255, pixels[idx+3] + a)

    def fill_rect(x1, y1, x2, y2, r, g, b, a=255):
        for y in range(max(0, int(y1)), min(height, int(y2))):
            for x in range(max(0, int(x1)), min(width, int(x2))):
                set_pixel(x, y, r, g, b, a)

    def draw_circle_filled(cx, cy, r, red, green, blue, alpha=255):
        for y in range(max(0, int(cy-r-1)), min(height, int(cy+r+2))):
            for x in range(max(0, int(cx-r-1)), min(width, int(cx+r+2))):
                dist = math.sqrt((x - cx)**2 + (y - cy)**2)
                if dist <= r:
                    if dist > r - 1:
                        aa = max(0, min(255, int((r - dist) * 255)))
                        set_pixel(x, y, red, green, blue, int(alpha * aa / 255))
                    else:
                        set_pixel(x, y, red, green, blue, alpha)

    def draw_rounded_rect(x1, y1, x2, y2, radius, r, g, b, a=255):
        """Draw a filled rounded rectangle."""
        for y in range(max(0, int(y1)), min(height, int(y2))):
            for x in range(max(0, int(x1)), min(width, int(x2))):
                inside = False
                if x1 + radius <= x <= x2 - radius or y1 + radius <= y <= y2 - radius:
                    inside = True
                else:
                    corners = [
                        (x1 + radius, y1 + radius),
                        (x2 - radius, y1 + radius),
                        (x1 + radius, y2 - radius),
                        (x2 - radius, y2 - radius),
                    ]
                    for ccx, ccy in corners:
                        dist = math.sqrt((x - ccx)**2 + (y - ccy)**2)
                        if dist <= radius:
                            inside = True
                            break
                if inside:
                    set_pixel(x, y, r, g, b, a)

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
                        px, py = int(lx + dx), int(ly + dy)
                        if 0 <= px < width and 0 <= py < height:
                            set_pixel(px, py, r, g, b)

    # --- Background: dark gradient ---
    for y in range(height):
        for x in range(width):
            t = ((x / width) * 0.6 + (y / height) * 0.4)
            c = lerp_color(BG_DARK, BG_MID, t)
            set_pixel(x, y, c[0], c[1], c[2], 255)

    # Gradient accent stripe across top
    for y in range(0, 4):
        for x in range(width):
            t = x / width
            c = lerp_color(BRAND_PRIMARY, BRAND_SECONDARY, t)
            set_pixel(x, y, c[0], c[1], c[2], 255)

    # --- Icon (speech bubble with checkmark, left side) ---
    icon_cx = 100
    icon_cy = 115
    icon_r = 50

    # Icon background circle with gradient
    for y in range(max(0, int(icon_cy-icon_r-1)), min(height, int(icon_cy+icon_r+2))):
        for x in range(max(0, int(icon_cx-icon_r-1)), min(width, int(icon_cx+icon_r+2))):
            dist = math.sqrt((x - icon_cx)**2 + (y - icon_cy)**2)
            if dist <= icon_r:
                t = ((x + y) / (width))
                c = lerp_color(BRAND_PRIMARY, BRAND_SECONDARY, t)
                if dist > icon_r - 1:
                    aa = max(0, min(255, int((icon_r - dist) * 255)))
                    set_pixel(x, y, c[0], c[1], c[2], aa)
                else:
                    set_pixel(x, y, c[0], c[1], c[2], 255)

    # Speech bubble inside icon (white rounded rect)
    b_cx, b_cy = icon_cx, icon_cy - 4
    b_hw, b_hh = 28, 18
    b_r = 7
    for y in range(max(0, int(b_cy - b_hh - 1)), min(height, int(b_cy + b_hh + 12))):
        for x in range(max(0, int(b_cx - b_hw - 1)), min(width, int(b_cx + b_hw + 1))):
            px = x - b_cx
            py = y - b_cy
            inside = False
            if abs(px) <= b_hw - b_r and abs(py) <= b_hh:
                inside = True
            elif abs(px) <= b_hw and abs(py) <= b_hh - b_r:
                inside = True
            else:
                for ccx, ccy in [(b_cx - b_hw + b_r, b_cy - b_hh + b_r),
                                  (b_cx + b_hw - b_r, b_cy - b_hh + b_r),
                                  (b_cx - b_hw + b_r, b_cy + b_hh - b_r),
                                  (b_cx + b_hw - b_r, b_cy + b_hh - b_r)]:
                    if math.sqrt((x - ccx)**2 + (y - ccy)**2) <= b_r:
                        inside = True
                        break
            if inside:
                set_pixel(x, y, 255, 255, 255, 255)

    # Bubble tail
    for y in range(int(b_cy + b_hh), int(b_cy + b_hh + 8)):
        progress = (y - (b_cy + b_hh)) / 8
        left = b_cx - 8 - 4 * progress
        right = b_cx - 2 - 2 * progress
        for x in range(max(0, int(left)), min(width, int(right))):
            set_pixel(x, y, 255, 255, 255, 255)

    # Checkmark inside bubble
    draw_line(b_cx - 10, b_cy + 1, b_cx - 2, b_cy + 9, *TRUST_GREEN, 3.5)
    draw_line(b_cx - 2, b_cy + 9, b_cx + 12, b_cy - 7, *TRUST_GREEN, 3.5)

    # --- Text area (right side) ---
    text_x = 180
    text_y = 75

    # Title block - "TrueVoice for Reddit"
    fill_rect(text_x, text_y, text_x + 220, text_y + 18, 255, 255, 255, 240)
    fill_rect(text_x, text_y + 24, text_x + 130, text_y + 36, 255, 255, 255, 140)

    # Subtitle bar
    fill_rect(text_x, text_y + 50, text_x + 200, text_y + 58, 255, 255, 255, 80)

    # --- Trust dots (centered below icon) ---
    dots_y = 195
    dot_r = 8
    dot_gap = 28

    draw_circle_filled(icon_cx - dot_gap, dots_y, dot_r, *TRUST_GREEN, 255)
    draw_circle_filled(icon_cx, dots_y, dot_r, *TRUST_YELLOW, 255)
    draw_circle_filled(icon_cx + dot_gap, dots_y, dot_r, *TRUST_RED, 255)

    # Small label bars next to dots
    fill_rect(icon_cx + dot_gap + 18, dots_y - 3, icon_cx + dot_gap + 70, dots_y + 3, 255, 255, 255, 60)

    # --- Sample badge mockups on the right ---
    badge_x = 190
    badge_y = 155

    # Mock badge 1 (green)
    draw_rounded_rect(badge_x, badge_y, badge_x + 100, badge_y + 22, 11, 50, 60, 90, 180)
    draw_circle_filled(badge_x + 12, badge_y + 11, 4, *TRUST_GREEN, 255)
    fill_rect(badge_x + 22, badge_y + 8, badge_x + 90, badge_y + 14, 255, 255, 255, 150)

    # Mock badge 2 (yellow)
    draw_rounded_rect(badge_x + 110, badge_y, badge_x + 210, badge_y + 22, 11, 50, 60, 90, 180)
    draw_circle_filled(badge_x + 122, badge_y + 11, 4, *TRUST_YELLOW, 255)
    fill_rect(badge_x + 132, badge_y + 8, badge_x + 200, badge_y + 14, 255, 255, 255, 150)

    # Mock badge 3 (red)
    draw_rounded_rect(badge_x, badge_y + 32, badge_x + 80, badge_y + 54, 11, 50, 60, 90, 180)
    draw_circle_filled(badge_x + 12, badge_y + 43, 4, *TRUST_RED, 255)
    fill_rect(badge_x + 22, badge_y + 40, badge_x + 70, badge_y + 46, 255, 255, 255, 150)

    # --- Bottom accent line ---
    for y in range(height - 4, height):
        for x in range(width):
            t = x / width
            c = lerp_color(BRAND_PRIMARY, BRAND_SECONDARY, t)
            set_pixel(x, y, c[0], c[1], c[2], 255)

    return pixels


# Generate promotional tile
promo_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'store_assets')
os.makedirs(promo_dir, exist_ok=True)

w, h = 440, 280
px = draw_promo(w, h)
png_data = create_png(w, h, px)
path = os.path.join(promo_dir, 'promo_tile_440x280.png')
with open(path, 'wb') as f:
    f.write(png_data)
print(f'Generated {path} ({len(png_data)} bytes)')
