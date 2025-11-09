import sys
import struct

def decompress_data_from_file(filename, start_offset):
    try:
        with open(filename, 'rb') as f:
            f.seek(start_offset)
            compressed_data = bytearray(f.read())
    except IOError as e:
        print(f"Error reading file: {e}")
        return None

    decompressed_buffer = bytearray()
    comp_idx = 0
    comp_len = len(compressed_data)
    original_offset = start_offset

    while comp_idx < comp_len:
        control_byte = compressed_data[comp_idx]

        if control_byte == 0x80:
            # 1. Terminator Block
            print(f"[0x{original_offset + comp_idx:x}] TERMINATOR (0x80) found. Stopping.")
            break
        elif control_byte == 0xfe:
            # 2. Fill command
            comp_idx += 1
            # Read 2 bytes for LSB-first (Little Endian) offset
            if comp_idx + 1 >= comp_len:
                print(f"Error: Unexpected end of data for 4-byte command at 0x{original_offset + comp_idx - 1:x}.")
                break

            # Use struct for reliable LE word reading
            length = struct.unpack('<H', compressed_data[comp_idx:comp_idx+2])[0]
            comp_idx += 2
            if comp_idx < comp_len:
                fill_byte = compressed_data[comp_idx]
            else:
                print(f"Error: Reached end of compressed data during raw copy at offset 0x{original_offset + comp_idx:x}.")
                break
            comp_idx += 1
            print(f"[0x{original_offset + comp_idx - 4:x}] FILL (0x7e) found. Value: 0x{fill_byte:x}, Len: 0x{length:x}")
            for _ in range(length):
                decompressed_buffer.append(fill_byte)
        elif control_byte == 0xff:
            # 2. Long copy
            comp_idx += 1

            # Read 2 bytes for LSB-first (Little Endian) offset
            if comp_idx + 1 >= comp_len:
                print(f"Error: Unexpected end of data for 5-byte command at 0x{original_offset + comp_idx - 1:x}.")
                break
            # Use struct for reliable LE word reading
            length = struct.unpack('<H', compressed_data[comp_idx:comp_idx+2])[0]
            comp_idx += 2

            # Read 2 bytes for LSB-first (Little Endian) offset
            if comp_idx + 1 >= comp_len:
                print(f"Error: Unexpected end of data for 5-byte command at 0x{original_offset + comp_idx - 1:x}.")
                break
            # Use struct for reliable LE word reading
            offset_absolute = struct.unpack('<H', compressed_data[comp_idx:comp_idx+2])[0]
            comp_idx += 2

            print(f"[0x{original_offset + comp_idx - 3:x}] LONG copy. Len: 0x{length:x}, Offset: {offset_absolute}")

            for _ in range(length):
                if offset_absolute < len(decompressed_buffer):
                    byte_to_copy = decompressed_buffer[offset_absolute]
                    decompressed_buffer.append(byte_to_copy)
                    offset_absolute += 1
                else:
                    print(f"Error: Absolute offset {offset_absolute} out of bounds at source index {offset_absolute}.")
                    break
        elif (control_byte & 0xc0) == 0xc0: 
            # Sub-mode B: Absolute Buffer Copy (Bit 6 is set: 0xEC, 0xFE, etc.)
            byte1 = control_byte
            length = (byte1 & 0x3F) + 3
            comp_idx += 1
                
            # Read 2 bytes for LSB-first (Little Endian) offset
            if comp_idx + 1 >= comp_len:
                print(f"Error: Unexpected end of data for 3-byte command at 0x{original_offset + comp_idx - 1:x}.")
                break

            # Use struct for reliable LE word reading
            offset_absolute = struct.unpack('<H', compressed_data[comp_idx:comp_idx+2])[0]
            comp_idx += 2
             
            print(f"[0x{original_offset + comp_idx - 3:x}] ABSOLUTE copy. Len: 0x{length:x}, Offset: {offset_absolute}")

            for _ in range(length):
                if offset_absolute < len(decompressed_buffer):
                    byte_to_copy = decompressed_buffer[offset_absolute]
                    decompressed_buffer.append(byte_to_copy)
                    offset_absolute += 1
                else:
                    print(f"Error: Absolute offset {offset_absolute} out of bounds at source index {offset_absolute}.")
                    break
        elif (control_byte & 0x80):
            # 2. Raw Bytes Block (High bit set)
            comp_idx += 1
            length = control_byte & 0x3F
            print(f"[0x{original_offset + comp_idx - 1:x}] RAW bytes block. Length: 0x{length:x}")
            for _ in range(length):
                if comp_idx < comp_len:
                    decompressed_buffer.append(compressed_data[comp_idx])
                    comp_idx += 1
                else:
                    print(f"Error: Reached end of compressed data during raw copy at offset 0x{original_offset + comp_idx:x}.")
                    break
        else:
            # 3. Copy from Previous Bytes Block (High bit clear)
            byte1 = control_byte
                
            if comp_idx + 1 >= comp_len:
                print(f"Error: Unexpected end of data for 2-byte command at 0x{original_offset + comp_idx:x}.")
                break
                    
            byte2 = compressed_data[comp_idx + 1]
            comp_idx += 2
                
            word = (byte1 << 8) | byte2
            length = ((word & 0x7000) >> 12) + 3
            offset_relative = word & 0x0FFF
                
            print(f"[0x{original_offset + comp_idx - 2:x}] RELATIVE copy. Len: 0x{length:x}, Rel Offset: {offset_relative}")

            start_pos = len(decompressed_buffer) - offset_relative
            for i in range(length):
                source_idx = start_pos + i
                if source_idx >= 0 and source_idx < len(decompressed_buffer):
                    byte_to_copy = decompressed_buffer[source_idx]
                    decompressed_buffer.append(byte_to_copy)
                else:
                    print(f"Error: Relative offset {offset_relative} resulted in out of bounds read at index {source_idx}.")
                    break
                        
    return decompressed_buffer

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script_name.py <filename> <hex_offset>")
        print("Example: python script_name.py data.bin 0x1A00")
        sys.exit(1)

    filename = sys.argv[1]
    offset_str = sys.argv[2]
    
    # Handle both '0x' prefixed and raw hex strings
    if offset_str.startswith('0x') or offset_str.startswith('0X'):
        offset = int(offset_str[2:], 16)
    else:
        offset = int(offset_str, 16)

    print(f"Attempting to decode '{filename}' starting from offset 0x{offset:X}...")
    decoded_bytes = decompress_data_from_file(filename, offset)
    
    if decoded_bytes is not None:
        print(f"\nDecompression complete.")
        print(f"Total decompressed bytes: {len(decoded_bytes)}")
        # Optional: write decoded_bytes to an output file
        with open("output.bin", "wb") as f_out:
            f_out.write(decoded_bytes)
            print("Wrote output to output.bin")


