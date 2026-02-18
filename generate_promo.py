#!/usr/bin/env python3
"""Generate Chrome Web Store promotional tile (440x280) for User Insight for Reddit.
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
BRAND_PRIMARY = (74, 144, 217)
BRAND_SECONDARY = (108, 92, 231)
BG_DARK = (30, 33, 58)
BG_MID = (40, 45, 75)
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
                # Check if inside the rounded rect
                inside = False
                # Main body (excluding corners)
                if x1 + radius <= x <= x2 - radius or y1 + radius <= y <= y2 - radius:
                    inside = True
                else:
                    # Check corners
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

    # --- Background: dark gradient ---
    for y in range(height):
        for x in range(width):
            t = ((x / width) * 0.6 + (y / height) * 0.4)
            c = lerp_color(BG_DARK, BG_MID, t)
            set_pixel(x, y, c[0], c[1], c[2], 255)

    # Subtle gradient accent stripe across top
    for y in range(0, 4):
        for x in range(width):
            t = x / width
            c = lerp_color(BRAND_PRIMARY, BRAND_SECONDARY, t)
            set_pixel(x, y, c[0], c[1], c[2], 255)

    # --- Icon (smaller version, left side) ---
    icon_cx = 100
    icon_cy = 120
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

    # Lens circle (white)
    lens_cx = icon_cx - 5
    lens_cy = icon_cy - 5
    lens_r = 28
    draw_circle_filled(lens_cx, lens_cy, lens_r, 255, 255, 255, 255)

    # Lens border
    for y in range(max(0, int(lens_cy-lens_r-3)), min(height, int(lens_cy+lens_r+3))):
        for x in range(max(0, int(lens_cx-lens_r-3)), min(width, int(lens_cx+lens_r+3))):
            dist = math.sqrt((x - lens_cx)**2 + (y - lens_cy)**2)
            if lens_r - 2 <= dist <= lens_r + 1:
                edge = min(dist - (lens_r - 2), (lens_r + 1) - dist)
                a = min(255, int(edge * 200))
                set_pixel(x, y, 45, 55, 120, a)

    # User silhouette head
    draw_circle_filled(lens_cx, lens_cy - 8, 7, 74, 85, 120, 220)

    # User silhouette body
    for y in range(max(0, int(lens_cy + 2)), min(height, int(lens_cy + 16))):
        for x in range(max(0, int(lens_cx - 12)), min(width, int(lens_cx + 12))):
            dist = math.sqrt((x - lens_cx)**2 + (y - (lens_cy + 5))**2)
            if dist <= 12 and y >= lens_cy + 2:
                set_pixel(x, y, 74, 85, 120, 200)

    # Handle
    for t in range(60):
        frac = t / 60
        hx = lens_cx + lens_r * 0.6 + 22 * frac
        hy = lens_cy + lens_r * 0.6 + 22 * frac
        for dx in range(-3, 4):
            for dy in range(-3, 4):
                if dx*dx + dy*dy <= 9:
                    set_pixel(hx + dx, hy + dy, 45, 55, 120)

    # --- Text area (right side) ---
    # "User Insight" - draw as blocky pixel text
    # Since we can't render fonts, use colored rectangles to suggest text
    text_x = 180
    text_y = 75

    # Title block - bright white bar to suggest "User Insight for Reddit"
    fill_rect(text_x, text_y, text_x + 220, text_y + 18, 255, 255, 255, 240)
    fill_rect(text_x, text_y + 24, text_x + 150, text_y + 36, 255, 255, 255, 140)

    # Subtitle suggestion bar
    fill_rect(text_x, text_y + 50, text_x + 200, text_y + 58, 255, 255, 255, 80)

    # --- Trust dots (centered below icon) ---
    dots_y = 200
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

# Also generate a larger marquee tile (1400x560) by scaling 2x concept
# For now just the small tile is needed for initial submission
