#!/usr/bin/env python3
"""Generate Chrome Web Store promotional tile (440x280) for TrueVoice for Reddit.
Shows a realistic Reddit thread mockup with TrueVoice badges in action.
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

    compressed = zlib.compress(raw, 6)
    return sig + chunk(b'IHDR', ihdr) + chunk(b'IDAT', compressed) + chunk(b'IEND', b'')


def lerp_color(c1, c2, t):
    t = max(0.0, min(1.0, t))
    return tuple(int(a + (b - a) * t) for a, b in zip(c1, c2))


# Brand / UI colors
BRAND_PRIMARY   = (59, 130, 246)    # #3B82F6 blue
BRAND_SECONDARY = (139, 92, 246)    # #8B5CF6 purple
TRUST_GREEN     = (70, 209, 96)
TRUST_YELLOW    = (240, 180, 41)
TRUST_RED       = (229, 83, 75)

# Reddit-light UI palette
BG_PAGE    = (246, 247, 248)   # Reddit light background
BG_CARD    = (255, 255, 255)   # white card
BG_CARD2   = (249, 250, 251)   # slight off-white for thread bg
BORDER     = (237, 239, 241)
TEXT_MAIN  = (26, 26, 27)
TEXT_DIM   = (120, 124, 126)
TEXT_LINK  = (0, 121, 211)
VOTE_UP    = (255, 69, 0)      # Reddit orange upvote


def draw_promo(W, H):
    pixels = bytearray(W * H * 4)

    def sp(x, y, r, g, b, a=255):
        xi, yi = int(round(x)), int(round(y))
        if 0 <= xi < W and 0 <= yi < H:
            idx = (yi * W + xi) * 4
            oa = pixels[idx + 3]
            if oa == 0:
                pixels[idx] = r; pixels[idx+1] = g; pixels[idx+2] = b; pixels[idx+3] = a
            else:
                fa = a / 255.0
                pixels[idx]   = int(pixels[idx]   * (1 - fa) + r * fa)
                pixels[idx+1] = int(pixels[idx+1] * (1 - fa) + g * fa)
                pixels[idx+2] = int(pixels[idx+2] * (1 - fa) + b * fa)
                pixels[idx+3] = min(255, oa + int(a * (1 - oa / 255.0)))

    def fill_rect(x1, y1, x2, y2, r, g, b, a=255):
        for y in range(max(0, int(y1)), min(H, int(y2))):
            for x in range(max(0, int(x1)), min(W, int(x2))):
                sp(x, y, r, g, b, a)

    def draw_circle_filled(cx, cy, radius, r, g, b, alpha=255):
        for y in range(max(0, int(cy - radius - 1)), min(H, int(cy + radius + 2))):
            for x in range(max(0, int(cx - radius - 1)), min(W, int(cx + radius + 2))):
                dist = math.sqrt((x - cx) ** 2 + (y - cy) ** 2)
                if dist <= radius:
                    if dist > radius - 1:
                        aa = max(0, min(255, int((radius - dist) * 255)))
                        sp(x, y, r, g, b, int(alpha * aa / 255))
                    else:
                        sp(x, y, r, g, b, alpha)

    def draw_rounded_rect(x1, y1, x2, y2, radius, r, g, b, a=255):
        for y in range(max(0, int(y1)), min(H, int(y2))):
            for x in range(max(0, int(x1)), min(W, int(x2))):
                inside = False
                if x1 + radius <= x <= x2 - radius or y1 + radius <= y <= y2 - radius:
                    inside = True
                else:
                    for ccx, ccy in [(x1 + radius, y1 + radius), (x2 - radius, y1 + radius),
                                     (x1 + radius, y2 - radius), (x2 - radius, y2 - radius)]:
                        if math.sqrt((x - ccx) ** 2 + (y - ccy) ** 2) <= radius:
                            inside = True; break
                if inside:
                    sp(x, y, r, g, b, a)

    def draw_line(x1, y1, x2, y2, r, g, b, thick):
        length = math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
        if length == 0:
            return
        steps = int(length * 3) + 1
        for i in range(steps + 1):
            t = i / steps
            lx = x1 + (x2 - x1) * t
            ly = y1 + (y2 - y1) * t
            for dy in range(-int(thick) - 1, int(thick) + 2):
                for dx in range(-int(thick) - 1, int(thick) + 2):
                    if dx * dx + dy * dy <= thick * thick:
                        sp(int(lx + dx), int(ly + dy), r, g, b)

    # =========================================================
    # 1. PAGE BACKGROUND — subtle gradient
    # =========================================================
    for y in range(H):
        for x in range(W):
            t = y / H * 0.3
            c = lerp_color((240, 242, 248), (230, 232, 245), t)
            pixels[(y * W + x) * 4    ] = c[0]
            pixels[(y * W + x) * 4 + 1] = c[1]
            pixels[(y * W + x) * 4 + 2] = c[2]
            pixels[(y * W + x) * 4 + 3] = 255

    # =========================================================
    # 2. TOP ACCENT STRIPE (brand gradient)
    # =========================================================
    for y in range(4):
        for x in range(W):
            t = x / W
            c = lerp_color(BRAND_PRIMARY, BRAND_SECONDARY, t)
            sp(x, y, c[0], c[1], c[2], 255)

    # =========================================================
    # 3. REDDIT THREAD CARD (left ~55% of tile)
    # =========================================================
    card_x1, card_y1 = 12, 14
    card_x2, card_y2 = 255, H - 14

    draw_rounded_rect(card_x1, card_y1, card_x2, card_y2, 8,
                      *BG_CARD, 255)
    # thin border
    for y in range(int(card_y1), int(card_y2)):
        for x in [int(card_x1), int(card_x2) - 1]:
            sp(x, y, *BORDER, 255)
    for x in range(int(card_x1), int(card_x2)):
        for y in [int(card_y1), int(card_y2) - 1]:
            sp(x, y, *BORDER, 255)

    # --- Post title area ---
    fill_rect(card_x1 + 1, card_y1 + 1, card_x2 - 1, card_y1 + 32, *BG_CARD2, 255)

    # Subreddit + meta bar: colored dot + text bars
    draw_circle_filled(card_x1 + 10, card_y1 + 10, 4, *BRAND_PRIMARY, 255)
    fill_rect(card_x1 + 18, card_y1 + 7, card_x1 + 70, card_y1 + 13, *TEXT_DIM, 120)  # r/subreddit
    fill_rect(card_x1 + 76, card_y1 + 7, card_x1 + 110, card_y1 + 13, *TEXT_DIM, 60)  # · posted by

    # Post title (two lines of text bars)
    fill_rect(card_x1 + 8, card_y1 + 18, card_x2 - 8, card_y1 + 25, *TEXT_MAIN, 200)
    fill_rect(card_x1 + 8, card_y1 + 27, card_x1 + 150, card_y1 + 32, *TEXT_MAIN, 130)

    # Divider
    fill_rect(card_x1 + 1, card_y1 + 35, card_x2 - 1, card_y1 + 36, *BORDER, 255)

    # =========================================================
    # 4. COMMENT ROWS
    # =========================================================
    # Each comment row: avatar circle, username, badge, comment lines

    def draw_comment_row(row_y, username_w, badge_color, badge_text, dot_class,
                         line1_w, line2_w, indent=0, highlighted=False, show_hover=False):
        """Draw a single comment row."""
        rx = card_x1 + 8 + indent
        ry = row_y

        if highlighted:
            fill_rect(card_x1 + 1, ry - 3, card_x2 - 1, ry + 45, 245, 248, 255, 200)

        # Avatar circle
        av_r = 8
        draw_circle_filled(rx + av_r, ry + av_r, av_r, *TEXT_DIM, 80)
        # small person silhouette hint
        draw_circle_filled(rx + av_r, ry + av_r - 3, 3, 255, 255, 255, 120)
        fill_rect(rx + av_r - 4, ry + av_r + 1, rx + av_r + 4, ry + av_r + 7, 255, 255, 255, 100)

        # Username
        ux = rx + av_r * 2 + 6
        fill_rect(ux, ry + 5, ux + username_w, ry + 12, *TEXT_LINK, 200)

        # ---- TrueVoice inline badge ----
        bx = ux + username_w + 5
        badge_w = len(badge_text) * 5 + 16
        badge_h = 13

        # Badge pill background
        draw_rounded_rect(bx, ry + 4, bx + badge_w, ry + 4 + badge_h, 6,
                          128, 128, 128, 22)

        # Dot color
        dot_colors = {
            'green':  TRUST_GREEN,
            'yellow': TRUST_YELLOW,
            'red':    TRUST_RED,
        }
        dc = dot_colors.get(dot_class, TEXT_DIM)
        draw_circle_filled(bx + 6, ry + 4 + badge_h // 2, 3, *dc, 255)

        # Badge text bars (simulate text as a bar)
        text_bar_w = badge_w - 16
        fill_rect(bx + 13, ry + 8, bx + 13 + text_bar_w, ry + 13, *TEXT_DIM, 160)

        # Score / karma row (placeholder bars)
        fill_rect(ux, ry + 16, ux + 18, ry + 20, *VOTE_UP, 180)    # upvote count
        fill_rect(ux + 22, ry + 16, ux + 60, ry + 20, *TEXT_DIM, 80)  # · X hours

        # Comment text lines
        if line1_w > 0:
            fill_rect(rx, ry + 24, rx + line1_w, ry + 29, *TEXT_MAIN, 170)
        if line2_w > 0:
            fill_rect(rx, ry + 32, rx + line2_w, ry + 37, *TEXT_MAIN, 110)

    # Row 1 — green (established)
    draw_comment_row(card_y1 + 42, 45, TRUST_GREEN, '6y · 5.2k', 'green',
                     line1_w=190, line2_w=155)

    # Row 2 — yellow (limited), highlighted (hovered)
    draw_comment_row(card_y1 + 100, 38, TRUST_YELLOW, '8mo · 312', 'yellow',
                     line1_w=180, line2_w=140, highlighted=True)

    # Row 3 — red (suspicious, indented reply)
    draw_comment_row(card_y1 + 158, 42, TRUST_RED, '14d · 0', 'red',
                     line1_w=150, line2_w=120, indent=16)

    # Row 4 — green (another established)
    draw_comment_row(card_y1 + 213, 50, TRUST_GREEN, '3y · 18k', 'green',
                     line1_w=185, line2_w=160)

    # =========================================================
    # 5. HOVER CARD (right side, overlapping slightly)
    # =========================================================
    hc_x1 = 248
    hc_y1 = 52
    hc_x2 = W - 10
    hc_y2 = H - 10
    hc_w = hc_x2 - hc_x1
    hc_h = hc_y2 - hc_y1

    # Card shadow
    draw_rounded_rect(hc_x1 + 2, hc_y1 + 2, hc_x2 + 2, hc_y2 + 2, 10,
                      0, 0, 0, 18)
    # Card body
    draw_rounded_rect(hc_x1, hc_y1, hc_x2, hc_y2, 10, *BG_CARD, 255)
    # thin border
    for y in range(int(hc_y1), int(hc_y2)):
        for x in [int(hc_x1), int(hc_x2) - 1]:
            sp(x, y, *BORDER, 255)
    for x in range(int(hc_x1), int(hc_x2)):
        for y in [int(hc_y1), int(hc_y2) - 1]:
            sp(x, y, *BORDER, 255)

    # Connector nub pointing left
    nub_y = hc_y1 + 20
    for i in range(8):
        sp(hc_x1 - i, nub_y + i, *BG_CARD, 230)
        sp(hc_x1 - i, nub_y - i, *BG_CARD, 230)

    hx = hc_x1 + 10  # left margin inside card
    hy = hc_y1 + 10

    # --- Header: username + trust pill ---
    fill_rect(hx, hy, hx + 68, hy + 10, *TEXT_MAIN, 210)  # username bar

    # "LOOKS GENUINE" green pill
    pill_x = hc_x1 + hc_w - 10 - 72
    pill_y = hy - 1
    draw_rounded_rect(pill_x, pill_y, pill_x + 72, pill_y + 13, 6,
                      70, 209, 96, 30)
    # pill text bar
    fill_rect(pill_x + 8, pill_y + 4, pill_x + 64, pill_y + 9, 26, 127, 55, 200)

    hy += 16

    # Divider
    fill_rect(hx, hy, hc_x2 - 10, hy + 1, *BORDER, 255)
    hy += 8

    # --- Metric rows ---
    def metric_row(label_w, value_w, bar_pct=None, bar_color=None, y_off=0):
        nonlocal hy
        # label
        fill_rect(hx, hy + y_off, hx + label_w, hy + y_off + 7, *TEXT_DIM, 160)
        # value
        fill_rect(hx, hy + y_off + 9, hx + value_w, hy + y_off + 15, *TEXT_MAIN, 200)
        if bar_pct is not None and bar_color is not None:
            bar_total = hc_x2 - 10 - hx
            fill_rect(hx, hy + y_off + 17, hx + bar_total, hy + y_off + 20, *BORDER, 255)
            fill_rect(hx, hy + y_off + 17, hx + int(bar_total * bar_pct), hy + y_off + 20,
                      *bar_color, 255)
            hy += 25
        else:
            hy += 20

    metric_row(50, 80)              # Account Age
    metric_row(35, 55)              # Karma
    metric_row(60, 70, 0.82, TRUST_GREEN)   # Subreddit Diversity
    metric_row(55, 65, 0.78, TRUST_GREEN)   # Comment Variety

    # Divider
    fill_rect(hx, hy, hc_x2 - 10, hy + 1, *BORDER, 255)
    hy += 6

    # Flags section (none for "genuine" user — just a faint label)
    fill_rect(hx, hy, hx + 30, hy + 7, *TEXT_DIM, 100)
    hy += 10

    # Top subreddits (tag pills)
    sub_colors = [(59, 130, 246), (139, 92, 246), (70, 209, 96)]
    sx = hx
    for i, sc in enumerate(sub_colors):
        pw = 38 + i * 6
        draw_rounded_rect(sx, hy, sx + pw, hy + 12, 6, *sc, 20)
        fill_rect(sx + 6, hy + 4, sx + pw - 6, hy + 8, *sc, 160)
        sx += pw + 5

    hy += 18

    # Footer: trust score
    fill_rect(hx, hy, hc_x2 - 10, hy + 1, *BORDER, 255)
    hy += 5
    fill_rect(hx, hy, hx + 45, hy + 7, *TEXT_DIM, 130)   # "Trust Score"
    # Score bar — high score (green)
    score_bar_w = hc_x2 - 10 - hx
    fill_rect(hx + 55, hy + 1, hx + 55 + score_bar_w - 55, hy + 6, *BORDER, 255)
    fill_rect(hx + 55, hy + 1, hx + 55 + int((score_bar_w - 55) * 0.84), hy + 6,
              *TRUST_GREEN, 220)

    # =========================================================
    # 6. EXTENSION LOGO (top-left corner)
    # =========================================================
    logo_cx = card_x1 + 14
    logo_cy = 8
    logo_r = 7

    for y in range(max(0, int(logo_cy - logo_r - 1)), min(H, int(logo_cy + logo_r + 2))):
        for x in range(max(0, int(logo_cx - logo_r - 1)), min(W, int(logo_cx + logo_r + 2))):
            dist = math.sqrt((x - logo_cx) ** 2 + (y - logo_cy) ** 2)
            if dist <= logo_r:
                t = (x + y) / (W * 0.5)
                c = lerp_color(BRAND_PRIMARY, BRAND_SECONDARY, t)
                aa = max(0, min(255, int((logo_r - dist) * 255))) if dist > logo_r - 1 else 255
                sp(x, y, c[0], c[1], c[2], aa)

    # mini checkmark inside logo
    draw_line(logo_cx - 3, logo_cy + 1, logo_cx, logo_cy + 3, 255, 255, 255, 1.2)
    draw_line(logo_cx, logo_cy + 3, logo_cx + 4, logo_cy - 2, 255, 255, 255, 1.2)

    # Extension name next to logo
    fill_rect(logo_cx + 10, logo_cy - 3, logo_cx + 80, logo_cy + 3, *TEXT_MAIN, 200)
    fill_rect(logo_cx + 10, logo_cy + 5, logo_cx + 55, logo_cy + 9, *TEXT_DIM, 120)

    # =========================================================
    # 7. BOTTOM ACCENT STRIPE
    # =========================================================
    for y in range(H - 4, H):
        for x in range(W):
            t = x / W
            c = lerp_color(BRAND_PRIMARY, BRAND_SECONDARY, t)
            sp(x, y, c[0], c[1], c[2], 255)

    return list(pixels)


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
