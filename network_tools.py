# Standard Lib
import socket, struct, os, sys, time
import pickle
from ipaddress import ip_network, ip_address

# Local Imports
import settings

TEXT = 1
HTML = 2
JSON = 3
XML = 4

class _BaseConnection():

    """
        Base class for to build network connections from.
        :param host: Default hostname. An IP address to accept connections through.
        :type host: str

        :param port: Default 10000. A port to accept connections through.
        :type port: int

        :param blocking: Default True. If True, listen() will hang until it receives data, then return the data. If blocking is False, listen() will timeout for a specified number of seconds before timing out.
        :type blocking: bool

        :param identifier: A name for the server
        :type identifier: Union[str, int]

        :param buffer_size: Default 4096. The size, in bytes of the buffer. Must be between 0 and 4096
        :type buffer_size: int

    """
    try:  # TODO: This is a bit hacky
        host = socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        host = socket.gethostbyname('localhost')

    port = 10000
    blocking = True
    timeout = 1
    identifier = ""
    buffer_size = 4096

    def __init__(self, *args, **kwargs):

        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in kwargs.items():
            setattr(self, key, value)


    def decode(self, data, encoding):
        """
            Serialise the data
        """
        if not encoding:
            return data
        if encoding == JSON:
            data = pickle.loads(b''.join(data))
        elif encoding == TEXT:
            data = str(data)
        return data

    def host_in_range(self, ip_address: str, mask: str) -> str:

        ip_range = ip_network(mask)
        return ip_address(ip_address) in ip_range

class _BaseClient(_BaseConnection):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # _BaseConnection.super()

    def send(self, data, *args, **kwargs):
        pass

    def encode(self, data, encoding):

        if not encoding:
            data = bytearray(data, encoding='utf-8')

        elif encoding == JSON:
            data = pickle.dumps(data)

        return data

class _BaseServer(_BaseConnection):
    """
        The Base Server Class. All server classes inherit from this.

        :param peek: Default 0. The slice length of received packets to print
        :type peek: bool
    """
    peek = 0

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) # _BaseConnection.super()

        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in kwargs.items():
            setattr(self, key, value)

    def listen(self):
        if self.timeout and self.timeout < 0:
            raise ValueError("timeout must be a positive integer")

        if self.buffer_size < 0 or self.buffer_size > 4096:
            raise ValueError("buffer_size must be between 0 and 4096")


class TCPServer(_BaseServer):
    """
        :param max_connections: Default 10. The number of simultaneous connections the server can handle.
        :type max_connections: int

        :param ack: Default "". If set, the server will respond to all requests with the ack value (the return value of listen() is unaffected).
        :type ack: Union[str, int]

        :param identifier: Default 'Anonymous TCP Server'. A name for the server for cases where multiple servers are running simultaneously.
        :type identifier: Union[int, str]
    """
    max_connections = 10
    ack = ""
    identifier = "Anonymous TCP Server"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs) # _BaseServer.super()

        try:
            # Instantiate the socket as a TCP server
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind((self.host, self.port))
            self.socket.listen(self.max_connections)
            self.socket.setblocking(self.blocking)
            if self.peek > 0:
                print("{}{} opened on {}:{}{}".format(settings.GREEN, self.identifier, self.host, self.port, settings.NORMAL))
        except OSError as e:
            raise OSError("{}Address {}:{} could not be assigned.{}".format(settings.RED, self.host, self.port, settings.NORMAL))
            if hasattr(self, 'socket'):
                self.socket.close()

    def listen(self, *args, encoding=None, peek=30, **kwargs):
        """
            checks for data sent to the server.
            :param unpickle: Default False. If True, the server deserializes the data before returning it. Useful for sending JSON around.
            :type unpickle: bool

            :param peek: Default 30. Choose a preview size for the received packets.
            :type peek: int
        """
        super().listen(*args, **kwargs)

        if self.max_connections < 1:
            raise ValueError("max_connections must be at least 1")

        try:
            connection, address = self.socket.accept()
            data = []
            packet = connection.recv(self.buffer_size)
            data.append(packet)
            print(type(packet))
            connection.sendall(self.ack.encode()) # ACK the clients message
            data = self.decode(data, encoding)

            if self.peek > 0:
                print("{}{} received: {}...{}".format(settings.GREEN, self.identifier, str(data)[:peek], settings.NORMAL))

            return address, data

        except socket.error as e:
            print("{}{}{}".format(settings.RED, e, settings.NORMAL))
            return None, None

        finally:
            if not self.blocking:
                time.sleep(self.timeout)

    def setblocking(self, val):
        self.socket.setblocking(val)

    def __del__(self):

        # Close the socket so resources are not left open after the program terminates
        if hasattr(self, 'socket'):
            self.socket.close()


class TCPClient(_BaseClient):

    """
        TCP Client

        :param identifier: Default "Anonymous TCP Client". A name for the server for cases where multiple servers are running simultaneously.
        :type identifier: Union[int, str]

        :param timeout: Default None. Time to wait, in seconds, for a response from the server. If set to None, the client is set to blocking mode, and will not time out until the server responds, or an error is thrown.
        :type timeout: Union[int, None]
    """
    identifier = "Anonymous TCP Client"
    timeout = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)


    def send(self, data, encoding=None):
        """
            :param data: The data to send
        """
        data = self.encode(data, encoding)
        response = []

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.host, self.port))

            totalsent = 0
            while totalsent < len(data):
                packet = data[totalsent:]
                print('Sending...', packet)
                sent = self.socket.send(packet)
                if sent == 0:
                    raise RuntimeError("socket connection broken")
                totalsent = totalsent + sent
            chunks = []
            bytes_recd = 0

            while True:
                chunk = self.socket.recv(self.buffer_size)
                if chunk == b'':
                    break
                    # raise RuntimeError("socket connection broken")
                chunks.append(chunk)
                bytes_recd = bytes_recd + len(chunk)
            response = b''.join(chunks)

            self.socket.close()

            return True, response

        except socket.timeout as e:
            raise socket.timeout('{}{}: {}{}'.format(settings.RED, self.identifier, e, settings.NORMAL))
            return False, e

        finally:
            self.socket.close()

class UDPServer(_BaseServer):
    """
        A UDP Server

        :param identifier: Default "Anonymous UDP Server". A name for the server for cases where multiple servers are running simultaneously.
        :type identifier: Union[int, str]

    """
    identifier = "Anonymous UDP Server"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        try:
            # Instantiate the socket as a TCP server

            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            self.socket.setblocking(self.blocking)
            if self.peek > 0:
                print("{}{} opened on {}:{}{}".format(settings.GREEN, self.identifier, self.host, self.port, settings.NORMAL))

        except OSError as e:
            raise OSError("{}{} {}{}".format(settings.RED, self.identifier, e, settings.NORMAL))

    def listen(self, *args, **kwargs):
        super().listen(*args, **kwargs)

        data, sender = self.socket.recvfrom(self.buffer_size)
        return sender, data

class UDPClient(_BaseClient):
    """
        A UDP Client

        :param identifier: Default "Anonymous UDP Client". A name for the server for cases where multiple servers are running simultaneously.
        :type identifier: Union[int, str]

    """

    identifier = "Anonymous UDP Client"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

    def send(self, data, *args, **kwargs):
        """
            :param data: The data to send
        """

        super().send(data, *args, **kwargs)
        self.socket.sendto(data.encode(), (self.host, self.port))

class MulticastServer(_BaseServer):
    """
        A Multicast Client

        :param identifier: Default "Anonymous Multicast Client". A name for the server for cases where multiple servers are running simultaneously.
        :type identifier: Union[int, str]

    """

    identifier = "Anonymous Multicast Client"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Check if host was a valid multicast address
        if self.host_in_range(self.host, "224.0.0.0/4"):
            raise self.InvalidAddressException("Please choose an address in the range 224.0.0.0/4.")

        try:
            # Look up multicast group address in name server and find out IP version
            addrinfo = socket.getaddrinfo(self.host, None)[0]

            # Create a socket
            self.server_socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
            self.server_socket.setblocking(self.blocking)
            # Allow multiple copies of this program on one machine
            # (not strictly needed)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind it to the port
            self.server_socket.bind((self.host, self.port))

            group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
            # Join MultiCast group
            if addrinfo[0] == socket.AF_INET:  # IPv4
                mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
                self.server_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            else:  # IPV6
                mreq = group_bin + struct.pack('@I', 0)
                self.server_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
            if self.peek > 0:
                print("{}{} opened on {}:{}{}".format(settings.GREEN, self.identifier, self.host, self.port, settings.NORMAL))

        except OSError as e:
            raise OSError("{}{} {}{}".format(settings.RED, self.identifier, e, settings.NORMAL))


    def listen(self, encoding=None):

        try:
            data, sender = self.server_socket.recvfrom(self.buffer_size)

            while data[-1:] == '\0':
                data = data[:-1]  # Strip trailing \0's

            if encoding:
                data = self.decode(data)

            return address, data

        except socket.error:
            return None, None

    class InvalidAddressException(BaseException):
        pass

class MulticastClient(_BaseClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    """
        :param data: The data to send
    """
    def send(self, data):

        addrinfo = socket.getaddrinfo(self.host, None)[0]
        self.socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)

        # Set Time-to-live (optional)
        ttl_bin = struct.pack('@i', self.timeout)
        if addrinfo[0] == socket.AF_INET:  # IPv4
            socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl_bin)
            sock_type = socket.IPPROTO_IP
        else: # IPv6
            socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
            sock_type = socket.IPPROTO_IPV6

        # Ignore packets sent from self TODO: make this an option
        socket.setsockopt(sock_type, socket.IP_MULTICAST_LOOP, 0)
        socket.sendto(pickle.dumps(data), (addrinfo[4][0], self.port))

class InitialisationException(BaseException):
    pass
