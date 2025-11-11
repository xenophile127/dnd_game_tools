import struct
import sys
import os

filename = None
fontoffset = 0
fontorder = None

def generate_sprite_table_and_tiles_flexible_spaces(text_content):
    """
    Generates a sprite table and ordered tileset string for Flow 1.
    Handles spaces dynamically for indentation and extra gaps.
    """
    
    tileset_chars_list = [] 
    sprite_entries = []
    current_y = 0x0000
    current_x = 0x0000 
    
    lines = text_content.split('\n')
    for line in lines:
        if line.lstrip().startswith('#'):
            continue

        line_content = line.split('#', 1)[0].rstrip() # Strip comments & trailing whitespace
        processed_line = line_content.lower()

        if processed_line.startswith('@filename'):
            global filename
            filename = processed_line.split('=', 1)[1].strip()
            continue
        if processed_line.startswith('@fontoffset'):
            global fontoffset
            fontoffset = int(processed_line.split('=', 1)[1].strip())
            continue
        if processed_line.startswith('@fontorder'):
            global fontorder
            fontorder = processed_line.split('=', 1)[1].strip()
            continue

        # Iterate through the line character by character
        temp_sprite_chars = []
        for char in processed_line:
            if char == ' ':
                # If we have characters buffered for a sprite, finalize that sprite first
                if temp_sprite_chars:
                    width = len(temp_sprite_chars)
                    start_tile_id = 0x03AF + len(tileset_chars_list) - width # Calculate start ID relative to current tileset end
                    
                    if width == 1: flags = 0x0000
                    elif width == 2: flags = 0x0400
                    elif width == 3: flags = 0x0800
                    elif width == 4: flags = 0x0C00
                    
                    entry = struct.pack('>HHHH', current_y, flags, start_tile_id, current_x - (width * 8)) # Use x pos where sprite started
                    sprite_entries.append(entry)
                    temp_sprite_chars = [] # Reset buffer

                # Increment X position for the space itself
                current_x += 8
            else:
                # If it's a non-space character
                
                # Check if we need to start a new sprite (either buffer is empty or full)
                if not temp_sprite_chars or len(temp_sprite_chars) == 4:
                    # Finalize current sprite if buffer is full (it shouldn't be here with per-char logic, but is safer)
                    if len(temp_sprite_chars) == 4:
                         width = 4
                         start_tile_id = 0x03AF + len(tileset_chars_list) - width
                         entry = struct.pack('>HHHH', current_y, 0x0C00, start_tile_id, current_x - (width * 8))
                         sprite_entries.append(entry)
                         temp_sprite_chars = []
                    
                    # Add character to buffer and tileset
                    temp_sprite_chars.append(char)
                    tileset_chars_list.append(char)
                    current_x += 8
                    
                else:
                    # Add character to existing sprite buffer and tileset
                    temp_sprite_chars.append(char)
                    tileset_chars_list.append(char)
                    current_x += 8
        
        # Finalize any remaining sprite characters at the end of the line
        if temp_sprite_chars:
            width = len(temp_sprite_chars)
            start_tile_id = 0x03AF + len(tileset_chars_list) - width
            if width == 1: flags = 0x0000
            elif width == 2: flags = 0x0400
            elif width == 3: flags = 0x0800
            elif width == 4: flags = 0x0C00
            entry = struct.pack('>HHHH', current_y, flags, start_tile_id, current_x - (width * 8))
            sprite_entries.append(entry)

        # Handle line breaks: reset X and increment Y for the next line
        current_y += 0x10
        current_x = 0x0000 

    # Summary
    tileset_string = "".join(tileset_chars_list)
    
    print(f"\n--- Generation Summary (Flow 1: No Reuse, Flexible Spacing) ---")
    print(f"Total tiles used in sequence: {len(tileset_string)}")
    print(f"Total sprites generated: {len(sprite_entries)}")
    
    if len(tileset_string) > 93:
        print(f"Warning: Total tiles ({len(tileset_string)}) exceeds 93-tile limit.")
    if len(sprite_entries) > 28:
        print(f"Warning: Total sprites ({len(sprite_entries)}) exceeds 28-sprite limit.")
        
    return sprite_entries, tileset_string

# --- Main Execution Block ---
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print(f"Usage: python {os.path.basename(sys.argv[0])} <input_text_file>")
        sys.exit(1)

    input_file_path = sys.argv[1] # Corrected index access

    try:
        with open(input_file_path, 'r') as f:
            file_content = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{input_file_path}' was not found.")
        sys.exit(1)

    sprite_data, tiles_needed_string = generate_sprite_table_and_tiles_flexible_spaces(file_content)

    print(f"\n--- Tileset Character Order (Spaces Skipped) ---")
    print(tiles_needed_string)

    print(f"\n--- Generating Tileset ---")

    try:
        with open(filename, 'rb') as f:
            tileset = f.read()
    except FileNotFoundError:
        print(f"Error: The file '{input_file_path}' was not found.")
        sys.exit(1)

    with open("tileset.bin", "wb") as f_out:
        for tile in tiles_needed_string:
             num = fontorder.find(tile)
             if num < 0:
                 print(f"Error: The tile for '{tile}' was not found in @fontorder.")
                 sys.exit(1)
             f_out.write(tileset[0x20*num:0x20*(num+1)])
        print("Wrote output to tileset.bin")
        print("Compress with `python compress tileset.bin")
        print("Ensure compressed size is less than or equal to 0x1c0 (448)")
        print("Insert at 0x6bdc2")

    print("\n--- Sprite Table Entries (Hex) ---")
    for entry in sprite_data:
        hex_repr = ' '.join(f'{b:02X}' for b in entry)
        print(f"{hex_repr}")
    print("\n Insert at 0x22872")


