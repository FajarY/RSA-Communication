import DES
import RSA
import socket
import threading
import os
import signal
import uuid

client_closed: object = False

client_public_key, client_private_key = RSA.generate_rsa_key(2048)
server_public_key = None
client_session_id = 0

other_clients_send_public_secret_key = {}
other_clients_receive_public_secret_key = {}

MAXIMUM_TRANSMISSION_UNIT = 1024

SERVER_REGISTER_MESSAGE = 0
SERVER_REQUEST_ESTABILISH_SECRET_MESSAGE = 1 #CLIENT_REQUEST_ESTABILISH_SECRET_GO_MESSAGE
SERVER_SEND_ESTABILISH_SECRET_MESSAGE = 2 #CLIENT_REQUEST_ESTABILISH_INCOMING_SECRET_MESSAGE
SERVER_CHAT_MESSAGE = 3

CLIENT_REGISTER_DONE_MESSAGE = 0
CLIENT_REQUEST_ESTABILISH_SECRET_GO_MESSAGE = 1
CLIENT_REQUEST_ESTABILISH_INCOMING_SECRET_MESSAGE = 2
CLIENT_REQUEST_ESTABILISH_FAILED_MESSAGE = 3
CLIENT_INCOMING_CHAT_MESSAGE = 4
CLIENT_TARGET_CHAT_LEFT_MESSAGE = 5

estabilish_wait_semaphore = threading.Semaphore(0)
send_lock = threading.Lock()

class Message:
    type: int
    position: int
    buffer: bytearray

    def create(self, type: int):
        self.type = type
        self.position = 0
        self.buffer = bytearray()
        self.write_int(type)

    def create_for_read(self, type: int):
        self.type = type
        self.position = 0
        self.buffer = bytearray()

    def input(self, socket_buffer: bytearray):
        self.position = 0
        self.buffer = socket_buffer
        self.type = self.read_int()

    def read_bytes(self, count:int):
        data = self.buffer[self.position:self.position+count]
        self.position += count
        return data

    def write_bytes(self, buffer):
        self.buffer += buffer
        self.position += len(buffer)

    def read_int(self):
        return int.from_bytes(self.read_bytes(4), byteorder="big", signed=True)
    
    def write_int(self, number: int):
        self.write_bytes(number.to_bytes(4, "big", signed=True))

    def read_string(self):
        size = self.read_int()
        buffer = self.read_bytes(size)

        return buffer.decode()

    def write_string(self, string:str):
        buffer = string.encode()
        self.write_int(len(buffer))
        self.write_bytes(buffer)

    def write_rsa_key(self, key):
        e, n = key
        e_as_str = str(e)
        n_as_str = str(n)

        self.write_string(e_as_str)
        self.write_string(n_as_str)

    def read_rsa_key(self):
        e_as_str = self.read_string()
        n_as_str = self.read_string()

        return (int(e_as_str), int(n_as_str))

    def write_string_encrypted(self, string: str, key: str):
        encrypted_string = DES.encrypt_buffer(string.encode(), key)
        self.write_string(encrypted_string)

    def read_string_decrypted(self, key: str):
        encrypted_string = self.read_string()
        decrypted_string = DES.decrypt_buffer(encrypted_string, key, True)

        return decrypted_string.decode()
        
def recv_reliable(socket: socket.socket, size: int):
    buffer = bytearray()

    while True:
        data = socket.recv(size)

        data_len = len(data)
        if(data_len == 0):
            return None
        
        buffer += data
        size -= data_len
        if(size == 0):
            break

    return buffer

def recv_message(socket:socket.socket):
    buffer = recv_reliable(socket, 4)
    if (buffer == None):
        return None

    size = int.from_bytes(buffer, byteorder="big")
    buffer = recv_reliable(socket, size)
    if(buffer == None):
        return None

    message = Message()
    message.input(buffer)

    return message

def send_reliable(socket:socket.socket, buffer:bytearray):
    position = 0
    length = len(buffer)

    while length > 0:
        send_size = min(length, MAXIMUM_TRANSMISSION_UNIT)
        sent = socket.send(buffer[position:position+send_size])

        if(sent == 0):
            return False
            
        position += sent
        length -= sent
            
    return True

def send_message(socket:socket.socket, message:Message):
    with send_lock:
        if(send_reliable(socket, int.to_bytes(message.position, 4, "big")) == False):
            return False
        if(send_reliable(socket, message.buffer[0:message.position]) == False):
            return False
        
        return True

def receive_messages(client_socket: socket):
    global client_public_key, client_private_key, client_closed, server_public_key, client_session_id, other_clients_send_public_secret_key, other_clients_receive_public_secret_key, estabilish_wait_semaphore
    while True:
        try:
            message = None

            try:
                message = recv_message(client_socket)
            except ConnectionAbortedError:
                message = None

            if (message is None):
                if client_closed == False:
                    print("Connection closed by server")
                    client_closed = True
                    os._exit(1)
                break

            if(message.type == CLIENT_REGISTER_DONE_MESSAGE):
                server_public_key = message.read_rsa_key()
                client_session_id = message.read_int()

                print(f"Register done with session id {client_session_id}")
                print(f"Received server public key: {server_public_key}")
                estabilish_wait_semaphore.release()

            elif(message.type == CLIENT_REQUEST_ESTABILISH_SECRET_GO_MESSAGE):
                signature = message.read_string()
                target_id = message.read_int()
                target_public_key = message.read_rsa_key()

                target_e, target_n = target_public_key
                target_test_hash = f"{target_e};{target_n}"
                
                if(RSA.rsa_verify_signature(server_public_key, signature, target_test_hash) == False):
                    print("There was an error when verifying server signature, possible attack?")
                    estabilish_wait_semaphore.release()
                    continue

                des_key = DES.generate_random_des_key()
                des_encrypted = RSA.rsa_encrypt(target_public_key, des_key)
                signature_key = RSA.rsa_get_signature(client_private_key, des_encrypted)

                estabilish_message = Message()
                estabilish_message.create(SERVER_SEND_ESTABILISH_SECRET_MESSAGE)
                estabilish_message.write_int(target_id)
                estabilish_message.write_string(signature_key)
                estabilish_message.write_string(des_encrypted)

                other_clients_send_public_secret_key[target_id] = (target_public_key, des_key)

                print(f"Sending DES Key: {des_key} to {target_id}")
                send_message(client_socket, estabilish_message)
                estabilish_wait_semaphore.release()
                
            elif(message.type == CLIENT_REQUEST_ESTABILISH_INCOMING_SECRET_MESSAGE):
                from_id = message.read_int()
                from_public_key_signature = message.read_string()
                from_public_key = message.read_rsa_key()
                from_public_key_e, from_public_key_n = from_public_key

                from_secret_signature = message.read_string()
                from_des_encrypted = message.read_string()

                if(RSA.rsa_verify_signature(server_public_key, from_public_key_signature, f"{from_public_key_e};{from_public_key_n}") == False):
                    print("There was an error when verifying server signature for incoming secret, possible attack?")
                    continue
                if(RSA.rsa_verify_signature(from_public_key, from_secret_signature, from_des_encrypted) == False):
                    print("There was an error when verifying authenticity for incoming secret, possible attack?")
                    continue
                from_des = RSA.rsa_decrypt(client_private_key, from_des_encrypted)
                other_clients_receive_public_secret_key[from_id] = (from_public_key, from_des)
                print(f"Received DES key for {from_id}: {from_des}")

            elif(message.type == CLIENT_REQUEST_ESTABILISH_FAILED_MESSAGE):
                target_id = message.read_int()
                print(f"Getting failed for {target_id} from server")
                estabilish_wait_semaphore.release()

            elif(message.type == CLIENT_INCOMING_CHAT_MESSAGE):
                from_id = message.read_int()
                from_public_key, from_secret_key = other_clients_receive_public_secret_key[from_id]

                chat = message.read_string_decrypted(from_secret_key)
                print(f"Reveived message from {from_id}: {chat}")

            elif(message.type == CLIENT_TARGET_CHAT_LEFT_MESSAGE):
                target_id = message.read_int()

                print(f"Failed when sending message to {target_id}, client already left the room")
        
        except Exception as e:
            if client_closed == False:
                print(f"Error receiving message: {e}")
                client_closed = True
                os._exit(1)
            break

def run_chat_client():
    global client_public_key, client_private_key, client_closed, server_public_key, client_session_id, other_clients_send_public_secret_key, other_clients_receive_public_secret_key, estabilish_wait_semaphore
    client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    server_ip = input("Server ip: ")
    server_port = input("Server port: ")

    server_address = (server_ip, int(server_port))
    try:
        client_socket.connect(server_address)
    except Exception as e:
        print(f"There was an error when trying to connect to {server_address}, {e}")
        return
    
    print(f"Connected to {server_address[0]}:{server_address[1]}")

    receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
    receive_thread.start()

    try:
        register_message = Message()
        register_message.create(SERVER_REGISTER_MESSAGE)
        register_message.write_rsa_key(client_public_key)

        print("Waiting for session...")

        send_message(client_socket, register_message)

        estabilish_wait_semaphore.acquire()
        print("/quit to exit the chat")
        print("To send message use the format {other_client_session_id}:{message}")

        while True:
            message = input()

            if message.lower() == '/quit':
                client_closed = True
                break
            elif len(message) != 0:
                parsed = message.split(":", 1)
                if(len(parsed) != 2):
                    print("Error chat format!")
                    continue

                target_id = int(parsed[0])

                if(target_id == client_session_id):
                    print("Cannot send message to itself!")
                    continue

                target_data = other_clients_send_public_secret_key.get(target_id)
                if(target_data == None):
                    print(f"Target has not handshaked yet, making handshake for {target_id}")
                    estabilish_message = Message()
                    estabilish_message.create(SERVER_REQUEST_ESTABILISH_SECRET_MESSAGE)
                    estabilish_message.write_int(target_id)

                    send_message(client_socket, estabilish_message)

                    estabilish_wait_semaphore.acquire()

                    target_data = other_clients_send_public_secret_key.get(target_id)
                    if(target_data == None):
                        print(f"There was an error when handshaking {target_id}, probably target not found, skipping message")
                        continue

                target_public_key, target_des_key = target_data
                chat_message = Message()
                chat_message.create(SERVER_CHAT_MESSAGE)
                chat_message.write_int(target_id)
                chat_message.write_string_encrypted(parsed[1], target_des_key)
                send_message(client_socket, chat_message)

    except KeyboardInterrupt:
        if client_closed == False:
            print("Exiting...")
            client_closed = True
    finally:
        client_socket.close()
        receive_thread.join()
    
if __name__ == "__main__":
    run_chat_client()