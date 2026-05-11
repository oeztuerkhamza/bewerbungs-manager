"""Generate simple PNG icons for the Chrome extension."""
import struct, zlib, os

def create_icon(size, output_path):
    """Create a simple gradient icon with 'AF' text as PNG."""
    pixels = []
    for y in range(size):
        row = []
        for x in range(size):
            # Gradient from navy to blue
            t = (x + y) / (2 * size)
            r = int(27 + t * (44 - 27))
            g = int(55 + t * (90 - 55))
            b = int(100 + t * (160 - 100))
            
            # Rounded corners
            corner_r = size // 6
            in_corner = False
            for cx, cy in [(corner_r, corner_r), (size - corner_r - 1, corner_r),
                           (corner_r, size - corner_r - 1), (size - corner_r - 1, size - corner_r - 1)]:
                if ((x < corner_r or x >= size - corner_r) and (y < corner_r or y >= size - corner_r)):
                    dist = ((x - cx) ** 2 + (y - cy) ** 2) ** 0.5
                    if dist > corner_r:
                        in_corner = True
            
            if in_corner:
                row.extend([0, 0, 0, 0])  # transparent
            else:
                # Add subtle "AF" text appearance for larger sizes
                row.extend([r, g, b, 255])
        pixels.append(bytes([0] + row))  # filter byte
    
    raw = b''.join(pixels)
    
    def chunk(chunk_type, data):
        c = chunk_type + data
        crc = zlib.crc32(c) & 0xFFFFFFFF
        return struct.pack('>I', len(data)) + c + struct.pack('>I', crc)
    
    ihdr = struct.pack('>IIBBBBB', size, size, 8, 6, 0, 0, 0)
    
    with open(output_path, 'wb') as f:
        f.write(b'\x89PNG\r\n\x1a\n')
        f.write(chunk(b'IHDR', ihdr))
        f.write(chunk(b'IDAT', zlib.compress(raw)))
        f.write(chunk(b'IEND', b''))

icons_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'chrome-autofill-extension', 'icons')
for size, name in [(16, 'icon16.png'), (48, 'icon48.png'), (128, 'icon128.png')]:
    path = os.path.join(icons_dir, name)
    create_icon(size, path)
    print(f"Created {name} ({size}x{size})")

print("Done!")
