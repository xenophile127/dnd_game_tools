import sys
import os

# --- Tile Definitions (Mapping Characters to Tile IDs) ---

CHAR_MAP = {
    'A': (0x02, 0x03, 0x2A, 0x2B), 'B': (0x04, 0x05, 0x2C, 0x2D), 'C': (0x06, 0x07, 0x2E, 0x2F),
    'D': (0x08, 0x09, 0x30, 0x31), 'E': (0x0A, 0x0B, 0x32, 0x33), 'F': (0x0C, 0x0D, 0x34, 0x35),
    'G': (0x0E, 0x0F, 0x36, 0x37), 'H': (0x10, 0x11, 0x38, 0x39), 'I': (0x12, 0x13, 0x3A, 0x3B),
    'J': (0x14, 0x15, 0x3C, 0x3D), 'K': (0x16, 0x17, 0x3E, 0x3F), 'L': (0x18, 0x19, 0x40, 0x41),
    'M': (0x1A, 0x1B, 0x42, 0x43), 'N': (0x1C, 0x1D, 0x44, 0x45), 'O': (0x1E, 0x1F, 0x46, 0x47),
    'P': (0x20, 0x21, 0x48, 0x49), 'Q': (0x22, 0x23, 0x4A, 0x4B), 'R': (0x24, 0x25, 0x4C, 0x4D),
    'S': (0x26, 0x27, 0x4E, 0x4F), 'T': (0x50, 0x51, 0x78, 0x79), 'U': (0x52, 0x53, 0x7A, 0x7B),
    'V': (0x54, 0x55, 0x7C, 0x7D),
    'X': (0x59, 0x5A, 0x81, 0x82), 
    'Y': (0x5B, 0x5C, 0x83, 0x84), 'Z': (0x5D, 0x5E, 0x85, 0x86),
    '0': (0x61, 0x62, 0x89, 0x8A), '1': (0x63, 0x64, 0x8B, 0x8C), '2': (0x65, 0x66, 0x8D, 0x8E),
    '3': (0x67, 0x68, 0x8F, 0x90), '4': (0x69, 0x6A, 0x91, 0x92), '5': (0x6B, 0x6C, 0x93, 0x94),
    '6': (0x6D, 0x6E, 0x95, 0x96), '7': (0x6F, 0x70, 0x97, 0x98), '8': (0x71, 0x72, 0x99, 0x9A),
    '9': (0x73, 0x74, 0x9B, 0x9C),
    '.': (0x00, None, 0x9d, None), 
    ',': (0x00, None, 0x9e, None), 
    '!': (0x77, None, 0x9f, None), 
    '\'': (0x00, 0x00, 0x00, 0x00), # Accent placeholder
    ' ': (0x00, None, 0x00, None), # Space is 1 tile wide blank
}

def get_char_tiles(char):
    char = char.upper()
    if char == 'W':
        top_tiles = [0x56, 0x57, 0x58]
        bottom_tiles = [0x7E, 0x7F, 0x80]
        return top_tiles, bottom_tiles, 3, True
    
    if char in CHAR_MAP:
        top_left, top_right, bottom_left, bottom_right = CHAR_MAP[char]
        
        top_tiles = [top_left]
        if top_right is not None: top_tiles.append(top_right)
            
        bottom_tiles = [bottom_left]
        if bottom_right is not None: bottom_tiles.append(bottom_right)
        
        width = 1 if top_right is None else 2
        # A character is multi-height if the bottom row has non-blank tiles
        is_double_height = any(t != 0x00 for t in bottom_tiles) 
        return top_tiles, bottom_tiles, width, is_double_height
    
    # Default to a space if character is not found
    return [0x00], [0x00], 1, False # Unknown char is a 1-wide blank space

def encode_text_to_tiles(text_lines):
    """
    Encodes text into a flat list of tile_id bytes only.
    Handles line breaks, variable character width, and vertical spacing.
    """
    SCREEN_WIDTH = 64
    SCREEN_HEIGHT = 32 # Adjusted height for 4096 bytes (2048 entries) if we ignore attributes
    VISIBLE_WIDTH = 40
    TOTAL_ENTRIES = SCREEN_WIDTH * SCREEN_HEIGHT # 2048 entries

    # Initialize the virtual screen with blank tile IDs (0x00)
    screen_tiles = [0x00] * TOTAL_ENTRIES 
    
    current_x = 0
    current_y = 0

    for line in text_lines:
        if line.startswith('#'):
            continue

        line_height_needed = 1 # Start assuming a single height line
        
        # Pre-check the line to determine if it contains any double-height characters
        for char in line:
            _, _, _, is_double_height = get_char_tiles(char)
            if is_double_height:
                line_height_needed = 2
                break
        
        # Process characters in the line
        for char in line:
            top_tiles, bottom_tiles, width, _ = get_char_tiles(char)

            if current_x + width > VISIBLE_WIDTH:
                # Wrap to the next line of required height
                current_x = 0
                current_y += line_height_needed
                if current_y >= SCREEN_HEIGHT: break 
            
            # Place top tiles in the current row
            for i, tile_id in enumerate(top_tiles):
                index = current_y * SCREEN_WIDTH + current_x + i
                if index < TOTAL_ENTRIES:
                    screen_tiles[index] = tile_id

            # If the line needs 2 tiles of vertical space, place bottom tiles in the row below
            if line_height_needed == 2:
                for i, tile_id in enumerate(bottom_tiles):
                    if current_y + 1 < SCREEN_HEIGHT:
                        index = (current_y + 1) * SCREEN_WIDTH + current_x + i
                        if index < TOTAL_ENTRIES:
                            screen_tiles[index] = tile_id
            
            current_x += width

        # After finishing an input line, move the cursor down
        current_x = 0
        current_y += line_height_needed
        if current_y >= SCREEN_HEIGHT: break

    return screen_tiles

def save_binary_file(input_filename, tile_ids):
    """Saves the list of tile_id bytes to a binary file, prepending an 0x00 attribute byte."""
    output_filename = input_filename
    if output_filename.lower().endswith('.txt'):
        output_filename = output_filename[:-4] + '.bin'
    else:
        output_filename += '.bin'
    
    # We must interleave the attribute byte (0x20 if visible, 0x00 if blank)
    # The current encode_text_to_tiles only returns tile IDs. 
    # Let's adjust this to recreate the required 2-byte structure for the *output*.
    
    # Wait, the user said the final file must be 4096 bytes long. 
    # That means we cannot interleave attribute bytes if the grid is 64x64. 
    # The only way to get a 4096 byte file is a 64x64 grid with 1 byte per tile, 
    # OR a 64x32 grid with 2 bytes per tile (attribute + tile ID).

    # The user is likely constrained by the 4096 byte *size* limit in their game memory slot. 
    # I'll stick with the 64x32 (2048 tile entries total) structure and interleave the attribute bytes to reach 4096 bytes total.

    byte_data = bytearray()
    for tile_id in tile_ids: # tile_ids is 2048 entries long
        attr = 0x20 if tile_id != 0x00 else 0x00
        byte_data.append(attr)
        byte_data.append(tile_id)

    with open(output_filename, 'wb') as f:
        f.write(byte_data)
    
    print(f"Successfully encoded text and saved to {output_filename}")
    print(f"Total bytes written: {len(byte_data)} (Targeting exactly 4096 bytes for a 64x32 grid)")

def main():
    if len(sys.argv) != 2:
        print(f"Usage: python {sys.argv[0]} <input_text_filename>")
        sys.exit(1)

    input_filename = sys.argv[1] # Corrected index access

    try:
        with open(input_filename, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            lines = [line.replace('\r', '').replace('\n', '') for line in lines]
    except FileNotFoundError:
        print(f"Error: Input file '{input_filename}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An error occurred reading the file: {e}")
        sys.exit(1)
    
    encoded_tile_ids = encode_text_to_tiles(lines)
    save_binary_file(input_filename, encoded_tile_ids)

if __name__ == "__main__":
    main()

