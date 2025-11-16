import sys
import random

log_level = "none"

def log(str):
    if(log_level == "verbose"):
        print(str)

hex_to_bin_map = {
    '0': "0000",
    '1': "0001",
    '2': "0010",
    '3': "0011",
    '4': "0100",
    '5': "0101",
    '6': "0110",
    '7': "0111",
    '8': "1000",
    '9': "1001",
    'A': "1010",
    'B': "1011",
    'C': "1100",
    'D': "1101",
    'E': "1110",
    'F': "1111"
}
bin_to_hex_map = {
    "0000": '0',
	"0001": '1',
	"0010": '2',
	"0011": '3',
	"0100": '4',
	"0101": '5',
	"0110": '6',
	"0111": '7',
	"1000": '8',
	"1001": '9',
	"1010": 'A',
	"1011": 'B',
	"1100": 'C',
	"1101": 'D',
	"1110": 'E',
	"1111": 'F'
}

initial_permutation_table = [
    57, 49, 41, 33, 25, 17, 9, 1,
    59, 51, 43, 35, 27, 19, 11, 3,
    61, 53, 45, 37, 29, 21, 13, 5,
    63, 55, 47, 39, 31, 23, 15, 7,
    56, 48, 40, 32, 24, 16, 8, 0,
    58, 50, 42, 34, 26, 18, 10, 2,
    60, 52, 44, 36, 28, 20, 12, 4,
    62, 54, 46, 38, 30, 22, 14, 6
]

final_permutation_table = [
    39, 7, 47, 15, 55, 23, 63, 31,
    38, 6, 46, 14, 54, 22, 62, 30,
    37, 5, 45, 13, 53, 21, 61, 29,
    36, 4, 44, 12, 52, 20, 60, 28,
    35, 3, 43, 11, 51, 19, 59, 27,
    34, 2, 42, 10, 50, 18, 58, 26,
    33, 1, 41, 9, 49, 17, 57, 25,
    32, 0, 40, 8, 48, 16, 56, 24
]

expansion_d_box_table = [
    31, 0, 1, 2, 3, 4, 3, 4,
    5, 6, 7, 8, 7, 8, 9, 10,
    11, 12, 11, 12, 13, 14, 15, 16,
    15, 16, 17, 18, 19, 20, 19, 20,
    21, 22, 23, 24, 23, 24, 25, 26,
    27, 28, 27, 28, 29, 30, 31, 0
]

straight_permutation_table = [
    15, 6, 19, 20,
    28, 11, 27, 16,
    0, 14, 22, 25,
    4, 17, 30, 9,
    1, 7, 23, 13,
    31, 26, 2, 8,
    18, 12, 29, 5,
    21, 10, 3, 24
]

sbox_table = [
    [[14, 4, 13, 1, 2, 15, 11, 8, 3, 10, 6, 12, 5, 9, 0, 7],
	[0, 15, 7, 4, 14, 2, 13, 1, 10, 6, 12, 11, 9, 5, 3, 8],
	[4, 1, 14, 8, 13, 6, 2, 11, 15, 12, 9, 7, 3, 10, 5, 0],
	[15, 12, 8, 2, 4, 9, 1, 7, 5, 11, 3, 14, 10, 0, 6, 13]],

	[[15, 1, 8, 14, 6, 11, 3, 4, 9, 7, 2, 13, 12, 0, 5, 10],
	[3, 13, 4, 7, 15, 2, 8, 14, 12, 0, 1, 10, 6, 9, 11, 5],
	[0, 14, 7, 11, 10, 4, 13, 1, 5, 8, 12, 6, 9, 3, 2, 15],
	[13, 8, 10, 1, 3, 15, 4, 2, 11, 6, 7, 12, 0, 5, 14, 9]],

	[[10, 0, 9, 14, 6, 3, 15, 5, 1, 13, 12, 7, 11, 4, 2, 8],
	[13, 7, 0, 9, 3, 4, 6, 10, 2, 8, 5, 14, 12, 11, 15, 1],
	[13, 6, 4, 9, 8, 15, 3, 0, 11, 1, 2, 12, 5, 10, 14, 7],
	[1, 10, 13, 0, 6, 9, 8, 7, 4, 15, 14, 3, 11, 5, 2, 12]],

	[[7, 13, 14, 3, 0, 6, 9, 10, 1, 2, 8, 5, 11, 12, 4, 15],
	[13, 8, 11, 5, 6, 15, 0, 3, 4, 7, 2, 12, 1, 10, 14, 9],
	[10, 6, 9, 0, 12, 11, 7, 13, 15, 1, 3, 14, 5, 2, 8, 4],
	[3, 15, 0, 6, 10, 1, 13, 8, 9, 4, 5, 11, 12, 7, 2, 14]],

	[[2, 12, 4, 1, 7, 10, 11, 6, 8, 5, 3, 15, 13, 0, 14, 9],
	[14, 11, 2, 12, 4, 7, 13, 1, 5, 0, 15, 10, 3, 9, 8, 6],
	[4, 2, 1, 11, 10, 13, 7, 8, 15, 9, 12, 5, 6, 3, 0, 14],
	[11, 8, 12, 7, 1, 14, 2, 13, 6, 15, 0, 9, 10, 4, 5, 3]],

	[[12, 1, 10, 15, 9, 2, 6, 8, 0, 13, 3, 4, 14, 7, 5, 11],
	[10, 15, 4, 2, 7, 12, 9, 5, 6, 1, 13, 14, 0, 11, 3, 8],
	[9, 14, 15, 5, 2, 8, 12, 3, 7, 0, 4, 10, 1, 13, 11, 6],
	[4, 3, 2, 12, 9, 5, 15, 10, 11, 14, 1, 7, 6, 0, 8, 13]],

	[[4, 11, 2, 14, 15, 0, 8, 13, 3, 12, 9, 7, 5, 10, 6, 1],
	[13, 0, 11, 7, 4, 9, 1, 10, 14, 3, 5, 12, 2, 15, 8, 6],
	[1, 4, 11, 13, 12, 3, 7, 14, 10, 15, 6, 8, 0, 5, 9, 2],
	[6, 11, 13, 8, 1, 4, 10, 7, 9, 5, 0, 15, 14, 2, 3, 12]],

	[[13, 2, 8, 4, 6, 15, 11, 1, 10, 9, 3, 14, 5, 0, 12, 7],
	[1, 15, 13, 8, 10, 3, 7, 4, 12, 5, 6, 11, 0, 14, 9, 2],
	[7, 11, 4, 1, 9, 12, 14, 2, 0, 6, 10, 13, 15, 3, 5, 8],
	[2, 1, 14, 7, 4, 10, 8, 13, 15, 12, 9, 0, 3, 5, 6, 11]]
]

key_parity_bit_drop = [
    56, 48, 40, 32, 24, 16, 8,
    0, 57, 49, 41, 33, 25, 17,
    9, 1, 58, 50, 42, 34, 26,
    18, 10, 2, 59, 51, 43, 35,
    62, 54, 46, 38, 30, 22, 14,
    6, 61, 53, 45, 37, 29, 21,
    13, 5, 60, 52, 44, 36, 28,
    20, 12, 4, 27, 19, 11, 3
]

shift_table = [
    1, 1, 2, 2,
	2, 2, 2, 2,
	1, 2, 2, 2,
	2, 2, 2, 1
]

key_compression_table = [
    13, 16, 10, 23, 0, 4,
    2, 27, 14, 5, 20, 9,
    22, 18, 11, 3, 25, 7,
    15, 6, 26, 19, 12, 1,
    40, 51, 30, 36, 46, 54,
    29, 39, 50, 44, 32, 47,
    43, 48, 38, 55, 33, 52,
    45, 41, 49, 35, 28, 31
]

def hex_to_bin(hexstr):
    bin = ""
    for i in range(len(hexstr)):
        bin += hex_to_bin_map[hexstr[i]]

    return bin

def bin_to_hex(binstr):
    hex = ""
    hexlen = len(binstr) // 4
    pos = 0

    for i in range(hexlen):
        key = binstr[pos]
        key += binstr[pos + 1]
        key += binstr[pos + 2]
        key += binstr[pos + 3]

        hex += bin_to_hex_map[key]
        pos += 4

    return hex

def permute(str, permutearr, n):
    permutation = ""
    for i in range(n):
        permutation += str[permutearr[i]]

    return permutation

def shift_left(binstr, shift_count):
    len_str = len(binstr)

    shifted_binstr = ""
    for i in range(len_str):
        pos = (i + shift_count) % len_str
        shifted_binstr += binstr[pos]

    return shifted_binstr

def binstr_xor(a, b):
    ans = ""
    for i in range(len(a)):
        if a[i] == b[i]:
            ans += "0"
        else:
            ans += "1"

    return ans

def generate_round_keys(left_key, right_key):
    round_keys = []
    for i in range(16):
        left_key = shift_left(left_key, shift_table[i])
        right_key = shift_left(right_key, shift_table[i])

        combine_str = left_key + right_key

        round_key = permute(combine_str, key_compression_table, 48)

        round_keys.append(round_key)

    return round_keys

def encrypt_block(hex_plain_text, round_keys):
    bin_plain_text = hex_to_bin(hex_plain_text)
    bin_plain_text = permute(bin_plain_text, initial_permutation_table, 64)

    left_bin_plain_text = bin_plain_text[0:32]
    right_bin_plain_text = bin_plain_text[32:64]
    for i in range(16):
        right_bin_plain_text_expanded = permute(right_bin_plain_text, expansion_d_box_table, 48)

        xor_x = binstr_xor(right_bin_plain_text_expanded, round_keys[i])

        sbox_str = ""
        for j in range(8):
            row = int(xor_x[j * 6] + xor_x[j * 6 + 5], 2)
            col = int(xor_x[j * 6 + 1: j * 6 + 5], 2)
            val = sbox_table[j][row][col]
            sbox_str += f"{val:04b}"

        sbox_str = permute(sbox_str, straight_permutation_table, 32)

        result = binstr_xor(left_bin_plain_text, sbox_str)
        left_bin_plain_text = result

        if(i != 15):
            left_bin_plain_text, right_bin_plain_text = right_bin_plain_text, left_bin_plain_text
            log(f"Round\t {i + 1}\t{bin_to_hex(left_bin_plain_text)}\t{bin_to_hex(right_bin_plain_text)}\t{bin_to_hex(round_keys[i])}")
    
    combine = left_bin_plain_text + right_bin_plain_text
    cipher_text = permute(combine, final_permutation_table, 64)

    return cipher_text

def encrypt_all(hex_plain_text, round_keys):
    hex_plain_text_len = len(hex_plain_text)
    hex_plain_text_chunk_len = hex_plain_text_len // 16

    if((hex_plain_text_len % 16) != 0):
        pad_count = ((hex_plain_text_len // 16) + 1) * 16 - hex_plain_text_len
        for i in range(pad_count):
            hex_plain_text += "0"

        hex_plain_text_chunk_len += 1
        hex_plain_text_len += pad_count

    chiper_text = ""
    for i in range(hex_plain_text_chunk_len):
        log(f"Chunk {i}")
        chiper_text += encrypt_block(hex_plain_text[i * 16: (i + 1) * 16], round_keys)

    return chiper_text

def encrypt(hex_plain_text, hex_key):
    key = hex_to_bin(hex_key)
    key = permute(key, key_parity_bit_drop, 56)

    left_key = key[0:28]
    right_key = key[28:56]

    round_keys = generate_round_keys(left_key, right_key)

    return encrypt_all(hex_plain_text, round_keys)

def decrypt(hex_cipher_text, hex_key):
    key = hex_to_bin(hex_key)
    key = permute(key, key_parity_bit_drop, 56)

    left_key = key[0:28]
    right_key = key[28:56]

    round_keys = generate_round_keys(left_key, right_key)
    round_keys = round_keys[::-1]

    return encrypt_all(hex_cipher_text, round_keys)

def encrypt_buffer(buffer, hex_key):
    hex_str = ""

    for i in range(len(buffer)):
        bin = f"{buffer[i]:08b}"
        left = bin_to_hex(bin[0:4])
        right = bin_to_hex(bin[4:8])

        hex_str += left
        hex_str += right
        
    return bin_to_hex(encrypt(hex_str, hex_key))

def decrypt_buffer(chipered_hexed_buffer, hex_key, strip_trailing):
    plain_hex_str = bin_to_hex(decrypt(chipered_hexed_buffer, hex_key))
    buffer = bytearray(len(plain_hex_str) // 2)

    pos = 0
    for i in range(0, len(plain_hex_str), 2):
        buffer[pos] = int(plain_hex_str[i], 16) << 4 | int(plain_hex_str[i + 1], 16)
        pos += 1

    if(strip_trailing):
        while buffer and buffer[-1] == 0:
            buffer.pop()

    return buffer

choose_string = [
    "0",
    "1",
    "2",
    "3",
    "4",
    "5",
    "6",
    "7",
    "8",
    "9",
    "A",
    "B",
    "C",
    "D",
    "E",
    "F"
]

def generate_random_des_key():
    key = ""

    for i in range(16):
        key += choose_string[random.randint(0, len(choose_string) - 1)]

    return key