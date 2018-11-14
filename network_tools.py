# Standard Lib
from __future__ import print_function
import socket, struct, os, sys, time
import pickle
from ipaddress import ip_network, ip_address
# Local Imports
import settings

class Transmission():
    """
        Successful connections will return a Transmission object. To print the content, simply print the Transmission object.

        :param content: The bytearray that was received
        :type content: bytearray

        :param sender: The (host:port) tuple of the socket that sent the data
        :type sender: tuple

        :param receiver: The (host:port) tuple of the socket that received the data
        :type receiver: tuple
    """
    content = None
    sender = None
    receiver = None

    def __init__(self, *args, **kwargs):

        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in kwargs.items():
            setattr(self, key, value)

    def __str__(self):
        return self.content

    def __repr__(self):
        return str(self.content)

class _BaseConnection():

    """
        Base class to build network connections from.

        :param host: Default hostname. An IP address to accept connections through.
        :type host: str

        :param port: Default 10000. A port to accept connections through.
        :type port: int

        :param timeout: Default None. If None the connection is in blocking mode. Otherwise, timeout specifies the number of seconds to wait before timing out.
        :type timeout: Union[None, int]

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
    timeout = None
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

    def __del__(self):

        # Close the socket so resources are not left open after the program terminates
        if hasattr(self, 'socket'):
            self.socket.close()


class _BaseClient(_BaseConnection):
    """
        The Base Client class. All client classes inherit from this.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)  # _BaseConnection.init()

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
        super().__init__(*args, **kwargs) # _BaseConnection.init()

        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in kwargs.items():
            setattr(self, key, value)

    def listen(self):
        if self.timeout and self.timeout < 0:
            raise ValueError("timeout must be a positive integer")

        if self.buffer_size <= 0 or self.buffer_size > 4096:
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

            if self.timeout is not None:
                self.socket.setblocking(False)

            if self.peek > 0:
                print("{}{} opened on {}:{}{}".format(settings.GREEN, self.identifier, self.host, self.port, settings.NORMAL))
        except OSError as e:
            raise OSError("{}Address {}:{} could not be assigned.{}".format(settings.RED, self.host, self.port, settings.NORMAL))
            if hasattr(self, 'socket'):
                self.socket.close()

    def listen(self, *args, **kwargs):
        """
            Checks for data sent to the server.

            :param peek: Default 30. Choose a preview size for the received packets.
            :type peek: int
        """
        super().listen(*args, **kwargs)
        peek = kwargs.get('peek', None)
        encoding = kwargs.get('encoding', None)

        if self.max_connections < 1:
            raise ValueError("max_connections must be at least 1")

        try:
            connection, address = self.socket.accept()
            data = []
            packet = connection.recv(self.buffer_size)
            data.append(packet)
            connection.sendall(self.ack.encode()) # ACK the clients message
            data = self.decode(data, encoding)

            if peek:
                print("{}{} received: {}...{}".format(settings.GREEN, self.identifier, str(data)[:peek], settings.NORMAL))

            request = Transmission(content=data, sender=address, receiver=(self.host,self.port))
            return request

        except socket.error as e:
            raise socket.error("{}{} reported {}{}".format(settings.RED, self.identifier, e, settings.NORMAL))

        finally:
            if self.timeout:
                time.sleep(self.timeout)


class TCPClient(_BaseClient):

    """
        TCP Client. The socket is instantiated in send() not __init__(), to make TCP Clients reusable.

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

            response = Transmission(content=b''.join(chunks), receiver=self.socket.getsockname(), sender=(self.host, self.port))
            return response

        except socket.timeout as e:
            raise socket.timeout('{}{}: {}{}'.format(settings.RED, self.identifier, e, settings.NORMAL))

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
            # Instantiate the socket as a UDP server
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.socket.bind((self.host, self.port))
            if self.timeout is not None:
                self.socket.setblocking(False)

            if self.peek > 0:
                print("{}{} opened on {}:{}{}".format(settings.GREEN, self.identifier, self.host, self.port, settings.NORMAL)[:self.peek])

        except OSError as e:
            if self.socket:
                self.socket.close()
            # raise OSError("{}{} {}{}".format(settings.RED, self.identifier, e, settings.NORMAL))

    def listen(self, *args, **kwargs):
        super().listen(*args, **kwargs)

        data, sender = self.socket.recvfrom(self.buffer_size)
        request = Transmission(content=data, sender=sender, receiver=(self.host, self.port))
        return request

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
    host = "224.0.0.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Check if host was a valid multicast address
        # if not self.host_in_range(self.host, "224.0.0.0/4"):
        #     raise self.InvalidAddressException("Please choose an address in the range 224.0.0.0/4.")

        try:
            # Look up multicast group address in name server and find out IP version
            addrinfo = socket.getaddrinfo(self.host, None)[0]

            # Create a socket
            self.socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)

            if self.timeout is not None:
                self.socket.setblocking(False)
            # Allow multiple copies of this program on one machine
            # (not strictly needed)
            self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind it to the port
            self.socket.bind((self.host, self.port))

            group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
            # Join MultiCast group
            if addrinfo[0] == socket.AF_INET:  # IPv4
                mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
                self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            else:  # IPV6
                mreq = group_bin + struct.pack('@I', 0)
                self.socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
            if self.peek > 0:
                print("{}{} opened on {}:{}{}".format(settings.GREEN, self.identifier, self.host, self.port, settings.NORMAL))

        except OSError as e:
            raise OSError("{}{} {}{}".format(settings.RED, self.identifier, e, settings.NORMAL))


    def listen(self, encoding=None):

        try:
            data, sender = self.socket.recvfrom(self.buffer_size)

            while data[-1:] == '\0':
                data = data[:-1]  # Strip trailing \0's

            if encoding:
                data = self.decode(data)

            request = Transmission(content=data, sender=sender, receiver=(self.host, self.port))
            return request

        except socket.error as e:
            if self.socket:
                self.socket.close()
            raise socket.error('{}{}: {}{}'.format(settings.RED, self.identifier, e, settings.NORMAL))

    def host_in_range(self, ip_address, mask):

        ip_range = ip_network(mask)
        return ip_address(ip_address) in ip_range

    class InvalidAddressException(BaseException):
        pass

class MulticastClient(_BaseClient):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    """
        :param data: The data to send
    """
    def send(self, data):

        try:
            addrinfo = socket.getaddrinfo(self.host, None)[0]
            self.socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)

            # Set Time-to-live (optional)
            if self.timeout:
                ttl_bin = struct.pack('@i', self.timeout)
            else:
                ttl_bin = struct.pack('@i', 0)  # self.timout is None if not set. TODO: This is unintuitive behaviour

            if addrinfo[0] == socket.AF_INET:  # IPv4
                self.socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl_bin)
                sock_type = socket.IPPROTO_IP
            else: # IPv6
                socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
                sock_type = socket.IPPROTO_IPV6

            # Ignore packets sent from self TODO: make this an option
            self.socket.setsockopt(sock_type, socket.IP_MULTICAST_LOOP, 0)
            self.socket.sendto(pickle.dumps(data), (addrinfo[4][0], self.port))

        except socket.error as e:
            raise socket.error('{}{}: {}{}'.format(settings.RED, self.identifier, e, settings.NORMAL))
        finally:
            if self.socket:
                self.socket.close()

class InitialisationException(BaseException):
    pass
