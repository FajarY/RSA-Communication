import RSA
import socket
import select
import os

receive_buffer = {}

server_public_key, server_private_key = RSA.generate_rsa_key(2048)
clients_public_key = {}
clients_socket_by_session_id = {}
clients_session_id_by_sock = {}
free_client_session_id = 0

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

class Message:
    type: int
    position: int
    buffer: bytearray

    def create(self, type: int):
        self.type = type
        self.position = 0
        self.buffer = bytearray()
        self.write_int(type)

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

def parse_message(socket: socket.socket):
    messages = []

    while True:
        buffer: bytearray = receive_buffer[socket]
        if(len(buffer) < 4):
            break
        
        size = int.from_bytes(buffer[0:4], "big")
        if(len(buffer) < (4 + size)):
            break
        
        message = Message()
        message.input(buffer[4:4+size])

        buffer = buffer[4+size:]
        receive_buffer[socket] = buffer
        messages.append(message)

    return messages

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
    if(send_reliable(socket, int.to_bytes(message.position, 4, "big")) == False):
        return False
    
    if(send_reliable(socket, message.buffer[0:message.position]) == False):
        return False
    
    return True

def run_select_server():
    global receive_buffer, server_public_key, server_private_key, clients_public_key, free_client_session_id

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    ip_prompt = input("Listen IP: ")
    port_prompt = input("Listen Port: ")
    server_address = (ip_prompt, int(port_prompt))

    server_socket.bind(server_address)
    server_socket.listen(5)
    
    print(f"Server started on {server_address[0]}:{server_address[1]}")

    inputs = [server_socket]
    
    try:
        while inputs:
            readable, _, exceptional = select.select(inputs, [], inputs, 0.001)

            for sock in readable:
                if sock is server_socket:
                    incoming_socket, incoming_address = server_socket.accept()
                    print(f"New client connected: {incoming_address}")
                    inputs.append(incoming_socket)
                    receive_buffer[incoming_socket] = bytearray()

                else:
                    data = None
                    try:
                        data = sock.recv(MAXIMUM_TRANSMISSION_UNIT)
                        if not data:
                            print(f"Connection closed by {sock.getpeername()}")
                            inputs.remove(sock)
                            receive_buffer.pop(sock)
                            continue
                    except (ConnectionResetError, ConnectionAbortedError):
                        print(f"Connection closed by {sock.getpeername()}")
                        inputs.remove(sock)
                        receive_buffer.pop(sock)
                        continue

                    socket_buffer: bytearray = receive_buffer[sock]
                    socket_buffer += data
                    receive_buffer[sock] = socket_buffer

                    messages = parse_message(sock)

                    for i in range(len(messages)):
                        message: Message = messages[i]
                        if(message.type == SERVER_REGISTER_MESSAGE):
                            current_client_public_key = message.read_rsa_key()

                            print(f"Received new client registering with public key {current_client_public_key}")
                            print(f"Free session id is {free_client_session_id}, sending it now...")

                            clients_public_key[free_client_session_id] = current_client_public_key
                            clients_socket_by_session_id[free_client_session_id] = sock
                            clients_session_id_by_sock[sock] = free_client_session_id

                            register_message = Message()
                            register_message.create(CLIENT_REGISTER_DONE_MESSAGE)
                            register_message.write_rsa_key(server_public_key)
                            register_message.write_int(free_client_session_id)

                            free_client_session_id += 1
                            send_message(sock, register_message)
                        elif(message.type == SERVER_REQUEST_ESTABILISH_SECRET_MESSAGE):
                            target_id = message.read_int()

                            target_public_key = clients_public_key.get(target_id)

                            if(target_public_key == None):
                                error_message = Message()
                                error_message.create(CLIENT_REQUEST_ESTABILISH_FAILED_MESSAGE)
                                error_message.write_int(target_id)
                                send_message(sock, error_message)
                                continue

                            target_e, target_n = target_public_key

                            key_message = Message()
                            key_message.create(CLIENT_REQUEST_ESTABILISH_SECRET_GO_MESSAGE)
                            signature = RSA.rsa_get_signature(server_private_key, f"{target_e};{target_n}")

                            key_message.write_string(signature)
                            key_message.write_int(target_id)
                            key_message.write_rsa_key(target_public_key)

                            send_message(sock, key_message)

                        elif(message.type == SERVER_SEND_ESTABILISH_SECRET_MESSAGE):
                            target_id = message.read_int()
                            client_secret_signature = message.read_string()
                            client_des_encrypted = message.read_string()

                            target_sock = clients_socket_by_session_id.get(target_id)
                            if(target_sock == None):
                                error_message = Message()
                                error_message.create(CLIENT_REQUEST_ESTABILISH_FAILED_MESSAGE)
                                error_message.write_int(target_id)
                                send_message(sock, error_message)
                                continue

                            from_id = clients_session_id_by_sock[sock]
                            from_public_key = clients_public_key[from_id]
                            from_public_key_e, from_public_key_a = from_public_key
                            from_public_key_signature = RSA.rsa_get_signature(server_private_key, f"{from_public_key_e};{from_public_key_a}")

                            secret_message = Message()
                            secret_message.create(CLIENT_REQUEST_ESTABILISH_INCOMING_SECRET_MESSAGE)
                            secret_message.write_int(from_id)
                            secret_message.write_string(from_public_key_signature)
                            secret_message.write_rsa_key(from_public_key)
                            secret_message.write_string(client_secret_signature)
                            secret_message.write_string(client_des_encrypted)

                            send_message(target_sock, secret_message)
                        
                        elif(message.type == SERVER_CHAT_MESSAGE):
                            target_id = message.read_int()
                            encrypted_string = message.read_string()

                            from_id = clients_session_id_by_sock[sock]
                            target_sock = clients_socket_by_session_id[target_id]

                            print(f"Incoming from {from_id}, target {target_id}, with message : {encrypted_string}")

                            chat_message = Message()
                            chat_message.create(CLIENT_INCOMING_CHAT_MESSAGE)
                            chat_message.write_int(from_id)
                            chat_message.write_string(encrypted_string)
                            send_message(target_sock, chat_message)
            
            for sock in exceptional:
                print(f"Handling exceptional condition for {sock.getpeername()}")
                inputs.remove(sock)
                receive_buffer.pop(sock)

    except KeyboardInterrupt:
        print("Server shutting down...")
    finally:
        server_socket.close()
        
if __name__ == "__main__":
    run_select_server()