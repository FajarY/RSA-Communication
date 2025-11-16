import random
import hashlib

def is_prime_number_miller(n, miller_test_count):
    if (n <= 1):
        return False
    if (n <= 3):
        return True

    q = n - 1
    k = 0

    while q % 2 == 0:
        k += 1
        q //= 2

    for i in range(miller_test_count):
        a = random.randint(2, n - 2)

        x = pow(a, q, n)
        if(x == 1 or x == n - 1):
            continue

        maybe_prime = False
        for j in range(k - 1):
            x = pow(x, 2, n)
            if(x == (n - 1)):
                maybe_prime = True
                break

        if(maybe_prime == False):
            return False
        
    return True

def egcd(a, b):
    if(a == 0):
        return b, 0, 1
    
    val, x, y = egcd(b % a, a)

    return val, y - (b // a) * x, x
        

def mod_inverse(a, m):
    g, x, y = egcd(a, m)
    if g != 1:
        raise Exception("Inverse doesn't exist")
    return (x % m + m) % m

def gcd(a, b):
    while b != 0:
        a_temp = a

        a = b
        b = a_temp % b

    return a

def generate_prime_number(bits_count):
    while True:
        val = random.getrandbits(bits_count) | (1 << (bits_count - 1)) | 1

        if(is_prime_number_miller(val, 5)):
            return val

def generate_rsa_key(bits):
    while True:
        p = generate_prime_number(bits // 2)
        q = generate_prime_number(bits // 2)
        n = p * q

        o_n = (p - 1) * (q - 1)

        e = 65537
        check = gcd(e, o_n)
        if(check != 1):
            continue
        
        d = mod_inverse(e, o_n)

        public_key = (e, n)
        private_key = (d, n)

        return public_key, private_key
    
def rsa_encrypt(public_key, plain_text):
    plain_text_as_int = int.from_bytes(plain_text.encode(), 'big')

    e, n = public_key

    if(plain_text_as_int >= n):
        raise Exception("Cannot encrypt since it is larger or equals n")
    
    return str(pow(plain_text_as_int, e, n))

def rsa_decrypt(private_key, chiper_text):
    chiper_text_int = int(chiper_text)

    d, n = private_key

    plain_text_int = pow(chiper_text_int, d, n)
    plain_text_len = (plain_text_int.bit_length() + 7) // 8
    plain_text = int.to_bytes(plain_text_int, plain_text_len, 'big')

    return plain_text.decode()

def hash(plain_text):
    return hashlib.sha256(plain_text.encode()).digest()

def rsa_get_signature(private_key, plain_text):
    d, n = private_key

    hash_as_int = int.from_bytes(hash(plain_text), 'big') % n
    signature = pow(hash_as_int, d, n)

    return str(signature)

def rsa_verify_signature(public_key, signature, plain_text):
    e, n = public_key

    hash_as_int = int.from_bytes(hash(plain_text), 'big') % n
    encrypted_hash_as_int = int(signature)
    decrypted_hash_as_int = pow(encrypted_hash_as_int, e, n)

    return hash_as_int == decrypted_hash_as_int