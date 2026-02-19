#!/usr/bin/env python3
"""Generate bot-in-crosshairs icon for TrueVoice extension."""

import cairosvg
import os

SVG = '''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 128 128">
  <defs>
    <linearGradient id="scopeBg" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#1a1a2e"/>
      <stop offset="100%" stop-color="#16213e"/>
    </linearGradient>
    <linearGradient id="botFace" x1="0" y1="0" x2="0" y2="1">
      <stop offset="0%" stop-color="#8a8a9a"/>
      <stop offset="100%" stop-color="#6a6a7a"/>
    </linearGradient>
  </defs>

  <!-- Background circle (scope lens) -->
  <circle cx="64" cy="64" r="60" fill="url(#scopeBg)"/>

  <!-- Bot head (rounded rectangle) -->
  <rect x="38" y="36" width="52" height="44" rx="8" ry="8" fill="url(#botFace)" stroke="#555" stroke-width="1.5"/>

  <!-- Bot antenna -->
  <line x1="64" y1="36" x2="64" y2="26" stroke="#8a8a9a" stroke-width="3" stroke-linecap="round"/>
  <circle cx="64" cy="23" r="4" fill="#e5534b"/>

  <!-- Bot eyes (glowing red) -->
  <circle cx="51" cy="52" r="7" fill="#1a1a2e"/>
  <circle cx="77" cy="52" r="7" fill="#1a1a2e"/>
  <circle cx="51" cy="52" r="5" fill="#e5534b" opacity="0.9"/>
  <circle cx="77" cy="52" r="5" fill="#e5534b" opacity="0.9"/>
  <!-- Eye glow -->
  <circle cx="49" cy="50" r="2" fill="#ff8a80" opacity="0.7"/>
  <circle cx="75" cy="50" r="2" fill="#ff8a80" opacity="0.7"/>

  <!-- Bot mouth (grid/speaker) -->
  <rect x="48" y="63" width="32" height="10" rx="2" fill="#1a1a2e"/>
  <line x1="54" y1="63" x2="54" y2="73" stroke="#555" stroke-width="1"/>
  <line x1="60" y1="63" x2="60" y2="73" stroke="#555" stroke-width="1"/>
  <line x1="66" y1="63" x2="66" y2="73" stroke="#555" stroke-width="1"/>
  <line x1="72" y1="63" x2="72" y2="73" stroke="#555" stroke-width="1"/>

  <!-- Bot ears -->
  <rect x="30" y="46" width="8" height="14" rx="3" fill="#6a6a7a" stroke="#555" stroke-width="1"/>
  <rect x="90" y="46" width="8" height="14" rx="3" fill="#6a6a7a" stroke="#555" stroke-width="1"/>

  <!-- Scope ring (outer) -->
  <circle cx="64" cy="64" r="58" fill="none" stroke="#333" stroke-width="4"/>
  <circle cx="64" cy="64" r="56" fill="none" stroke="#111" stroke-width="1"/>

  <!-- Crosshairs -->
  <line x1="64" y1="4" x2="64" y2="30" stroke="#e5534b" stroke-width="2" opacity="0.85"/>
  <line x1="64" y1="98" x2="64" y2="124" stroke="#e5534b" stroke-width="2" opacity="0.85"/>
  <line x1="4" y1="64" x2="30" y2="64" stroke="#e5534b" stroke-width="2" opacity="0.85"/>
  <line x1="98" y1="64" x2="124" y2="64" stroke="#e5534b" stroke-width="2" opacity="0.85"/>

  <!-- Centre crosshair marks (small ticks) -->
  <line x1="64" y1="30" x2="64" y2="36" stroke="#e5534b" stroke-width="2.5" opacity="0.9"/>
  <line x1="64" y1="80" x2="64" y2="86" stroke="#e5534b" stroke-width="2.5" opacity="0.9"/>
  <line x1="30" y1="64" x2="38" y2="64" stroke="#e5534b" stroke-width="2.5" opacity="0.9"/>
  <line x1="90" y1="64" x2="98" y2="64" stroke="#e5534b" stroke-width="2.5" opacity="0.9"/>

  <!-- Scope rim highlight -->
  <circle cx="64" cy="64" r="60" fill="none" stroke="rgba(255,255,255,0.08)" stroke-width="2"/>
</svg>'''

os.makedirs('/home/user/reddit-user-check/icons', exist_ok=True)

for size in [16, 48, 128]:
    output = f'/home/user/reddit-user-check/icons/icon{size}.png'
    cairosvg.svg2png(bytestring=SVG.encode(), write_to=output,
                     output_width=size, output_height=size)
    print(f'Generated {output} ({size}x{size})')

# Also save the SVG source for reference
with open('/home/user/reddit-user-check/icons/icon.svg', 'w') as f:
    f.write(SVG)
print('Saved SVG source')
