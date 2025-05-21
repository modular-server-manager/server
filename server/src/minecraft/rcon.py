import collections
import os
import socket
import struct
import subprocess
import sys
import traceback

from gamuLogger import Logger

Logger.set_module("minecraft.rcon socket")

Packet = collections.namedtuple("Packet", ["id", "type", "data"])

class RCON:
    def __init__(self, host: str, port: int, password: str):
        self.host = host
        self.port = port
        self.password = password
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

    def open(self):
        self.socket.connect((self.host, self.port))
        self.authenticate()

    def __send_packet(self, packet: Packet):
        packet_data = struct.pack("<ii", packet.id, packet.type) + packet.data.encode("utf-8") + b"\x00\x00"
        packet_data = struct.pack("<i", len(packet_data)) + packet_data
        self.socket.sendall(packet_data)

    def __receive_packet(self) -> Packet:
        data = b""
        while True:
            chunk = self.socket.recv(4096)
            if not chunk:
                break
            data += chunk
            if len(data) >= 4:
                length = struct.unpack("<i", data[:4])[0]
                if len(data) >= length + 4:
                    break
        if len(data) < 8:
            raise ValueError("Incomplete packet received")
        packet_id, packet_type = struct.unpack("<ii", data[4:12])
        packet_data = data[12:-2].decode("utf-8")
        return Packet(packet_id, packet_type, packet_data)

    def authenticate(self):
        auth_packet = Packet(0, 3, self.password)
        self.__send_packet(auth_packet)
        response = self.__receive_packet()
        return response.id == 0

    def send_command(self, command: str) -> str:
        p = Packet(0, 2, command)
        Logger.debug(f"Sending packet: {p}")
        self.__send_packet(p)
        response = self.__receive_packet()
        Logger.debug(f"Received packet: {response}")
        if response.id == 0:
            return response.data
        else:
            raise ValueError(f"Command failed : {response.data}")

    def close(self):
        self.socket.close()


    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.close()
        if exc_type is not None:
            raise exc_type(exc_value)
        return True

if __name__ == "__main__":
    # Example usage

    try:
        with RCON("localhost", 25575, "toto") as rcon:
            running = True
            while running:
                cmd = input(">>> ")
                if cmd.lower() == "exit":
                    running = False
                else:
                    response = rcon.send_command(cmd)
                    print("Response:", response.strip())
    except Exception as e:
        print(f"Error: {e.__class__}: {e}")
        print(traceback.format_exc())
    finally:
        print("Server stopped.")
