import sys
import struct

# --- Configuration ---
MINIMUM_SPAN = 3
MAX_RELATIVE_OFFSET = 0x0fff
MAX_RELATIVE_LENGTH = 0x07+3
MAX_ABSOLUTE_LENGTH = 0x3d+3
MAX_RAW_LENGTH = 0x3F # 63 bytes
# Max relative length is 10 bytes

def compress_fill(input_bytes, i):
    length = 1
    value = input_bytes[i]
    for b in input_bytes[i+1:]:
        if value != b:
            break
        length += 1
    if length < 4:
        return []
    return [[[0xfe, length & 0xff, length >> 8, value], length]]

def compress_copy(input_bytes, i):
    best_short = [[], 0]
    best_long = [[], 0]
    for index in range(0,i):
        if input_bytes[index] == input_bytes[i]:
            buffer = list(input_bytes[0:i])
            j = i
            k = index
            length = 0
            while (j < len(input_bytes)) and (input_bytes[j] == buffer[k]):
                length += 1
                buffer.append(input_bytes[j])
                j += 1
                k += 1
            if length < MINIMUM_SPAN:
                continue # do nothing
            if length > MAX_ABSOLUTE_LENGTH:
                if length > best_long[1]:
                    best_long = [[0xff, length & 0xff, length >> 8, index & 0xff, index >> 8], length]
            # Long copy is long. Specifically, it is two bytes longer than the normal absolute copy.
            # This means there is an edge case at MAX_RELATVIE_LENGTH + 1 where it is not optimal.
            # Return a short/medium copy as well and let the caller decide between them.
            length = min(length, MAX_ABSOLUTE_LENGTH)
            if length > best_short[1]:
                if length <= MAX_RELATIVE_LENGTH:
                    best_short = [[((length-3)<<4) | ((i - index) >> 8), ((i - index) & 0xff)], length]
                else:
                    best_short = [[0xc0 | length - 3, index & 0xff, index >> 8], length]
    ret = []
    if best_long[1] != 0:
        ret.append(best_long)
    if best_short[1] != 0:
        ret.append(best_short)
    return ret

def compress_raw(b):
    ret = [0x80 | len(b)]
    ret.extend(b)
    return ret

def compress_relative_orig(input_bytes):
    search_start = max(0, current_idx - MAX_RELATIVE_OFFSET)
    
    for search_idx in range(search_start, current_idx):
        length = 0
        max_possible_len = min(10, input_len - current_idx)
            
        while length < max_possible_len and input_bytes[current_idx + length] == input_bytes[search_idx + length]:
            length += 1
           
        if length >= minimum_span:
            offset = current_idx - search_idx
            len_encoded = length - 3
            word = (len_encoded << 12) | offset
            byte1 = (word >> 8) & 0xFF
            byte2 = word & 0xFF
                
            cmd_bytes = bytearray([byte1, byte2])
            cmd_cost = 2
                
            # Cost is current command size + cost of remaining file starting after the match
            cost = cmd_cost + min_cost[current_idx + length]
                
            if cost < best_cost_for_idx:
                best_cost_for_idx = cost
                best_cmd_for_idx = cmd_bytes

def compress_optimal(input_bytes, minimum_span=MINIMUM_SPAN):
    input_len = len(input_bytes)
    
    # DP table: min_cost[i] stores the minimum cost (length of compressed data) 
    # to compress the input starting from index 'i'.
    min_cost = [0] * (input_len + 1)
    # best_command[i] stores the command bytes that achieve the min_cost[i]
    best_command = [None] * (input_len + 1)

    raw = []
    compressed_data = bytearray()
    
    current_idx = 0
    while current_idx < len(input_bytes):
        
        # Initialize min cost for this position to infinity
        best_cost_for_idx = float('inf')
        best_cmd_for_idx = None

        cmds = []
        
        # --- 1. Try Fill (0xff) ---

        cmds.extend(compress_fill(input_bytes, current_idx))

        # --- 2. Try Copy(s) ---

        cmds.extend(compress_copy(input_bytes, current_idx))

        # --- 3. Calculate the winner ---
        winner = [[], -1]
        for cmd in cmds:
            if (cmd[1] - len(cmd[0])) > (winner[1] - len(winner[0])):
                winner = cmd

        # Are we currently building a raw command? If so then there isn't a cost to adding to it.
        if len(raw) > 0:
            threshold = 2
        else:
            threshold = 1

        if (winner[1] - len(winner[0])) >= threshold:
            if len(raw):
                compressed_data.extend(compress_raw(raw))
                raw = []
            compressed_data.extend(winner[0])
            current_idx += winner[1]
        else:
            raw.append(input_bytes[current_idx])
            current_idx += 1
            if len(raw) == MAX_RAW_LENGTH:
                compressed_data.extend(compress_raw(raw))
                raw = []

    if len(raw):
        compressed_data.extend(compress_raw(raw))
    compressed_data.append(0x80)
            
    return compressed_data

def run_compressor(filename, minimum_span):
    try:
        with open(filename, 'rb') as f:
            input_bytes = f.read()
    except IOError as e:
        print(f"Error reading file: {e}")
        sys.exit(1)
    
    print(f"Read {len(input_bytes)} bytes from {filename}. Compressing with min_span={minimum_span}...")
    compressed_data = compress_optimal(input_bytes, minimum_span)

    output_filename = filename
    if output_filename.lower().endswith('.bin'):
        output_filename = output_filename[:-4]

    output_filename += '.compressed'
    
    with open(output_filename, "wb") as f_out:
        f_out.write(compressed_data)
        
    print(f"\nCompression complete.")
    print(f"Original size: {len(input_bytes)} bytes")
    print(f"Compressed size: {len(compressed_data)} bytes")
    print(f"Wrote output to {output_filename}")


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python script_name.py <filename> [minimum_span]")
        print("Example: python script_name.py level1.bin 4")
        sys.exit(1)

    input_filename = sys.argv[1]
    span = MINIMUM_SPAN
    if len(sys.argv) == 3:
        try:
            span = int(sys.argv[2])
            if span < 3 or span > 10:
                raise ValueError("Minimum span must be between 3 and 10.")
        except ValueError as e:
            print(f"Invalid span argument: {e}")
            sys.exit(1)

    run_compressor(input_filename, span)

