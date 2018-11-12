# Standard Lib
import socket, struct, os, sys, time
import pickle as pickl
from ipaddress import ip_network, ip_address

# 3rd Party
import requests

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
            data = pickl.loads(b''.join(data))
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

            if unpickle_data:
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


class HTTPRequest():

    def __init__(self, url, method):

        self.url = url
        self.headers = {'content-type': 'application/json'}
        self.method = method

    def send(self, data):

        data = json.dumps(data)
        resp = None
        try:
            resp = requests.request(self.method, self.url, data=data, headers=self.headers)
            resp.raise_for_status()  # Raises exception for 404, etc
            return resp
        except requests.exceptions.ConnectionError:
            print('{}Failed to make a connection with {}'.format(settings.RED, self.url))
            print('Are you sure the server is up and running?{}'.format(settings.NORMAL))

        except requests.exceptions.HTTPError:
            print('{}The server responded with a status code {} for {}'.format(settings.RED, resp.status_code, self.url))
            print('{}{}'.format(resp.content, settings.NORMAL))
        return resp

class BitTorrentClient():


    def __init__(self, **kwargs):

        super(BitTorrentClient,).__init__()
        self.ses = lt.session()
        self.ses.listen_on(6881, 6891)


    def download(self, torrent):

        if not self.isValidTorrent(torrent):
            return

        torrent_file = os.path.join(settings.DOWNLOADS_DIR, torrent.file_name)
        torrent_contents = open(torrent_file, 'rb').read()
        e = lt.bdecode(torrent_contents)
        info = lt.torrent_info(e)
        params = {
            'save_path': settings.DOWNLOADS_DIR,
            'storage_mode': lt.storage_mode_t.storage_mode_sparse,
            'ti': info
        }
        self.h = self.ses.add_torrent(params)
        self.s = self.h.status()


    def pause(self, torrent):

        self.h.status().pause()

    def isValidTorrent(self, torrent):
        stats = os.stat(os.path.join(settings.DOWNLOADS_DIR, torrent.file_name))
        if stats.st_size == 0:
            print("file_size was 0")
            return False
        return True

    def updateStatus(self, torrent):

        status = ("Progress: {progress} complete\n"
        + "Download Rate: {download_rate}kb/s\n"
        + "Upload Rate: {upload_rate}Kb/s\n"
        + "Peers: {peers}\n"
        + "State: {download_rate}\n\n")
        torrent.status = self.h.status()
        # print(status.format(progress=torrent.status.progress * 100,
        #     download_rate=torrent.status.download_rate / 1000,
        #     upload_rate=torrent.status.upload_rate / 1000,
        #     peers=torrent.status.num_peers,
        #     state=torrent.status.state))
        return self.h.status()

class EmptyFileError(Exception):
     def __init__(self):
         self.message = "File size was 0"

class ResponseObject():

    def __init__(self, **kwargs):

        super(ResponseObject,).__init__()
        self.addr = kwargs['addr']
        self.query = kwargs['query']  # The response also needs to contain the query, so that the original client can filter multiple searches
        self.results = kwargs['results']

    def __str__(self):

        return str(self.addr) + " query: " + self.query + " returned " + str(self.results)


class TorrentObject():

    def __init__(self, **kwargs):

        super().__init__()
        self.title = kwargs['title']
        self.file_name = kwargs['file_name']
        self.file_size = 0
        self.status = None  # status object from libtorrent library
        self.row = None  # Row that the torrent will be displayed on in the downloads table
        self.total_seeders = 0
        self.total_peers = 0
        self.host = None

class QueryObject():

    def __init__(self, **kwargs):

        super(QueryObject,).__init__()
        self.query = kwargs['query']

    def __str__(self):

        string = "QUERY: " + self.query
        return string


class FTPServer():

    """
    Read permissions:
        "e" = change directory (CWD, CDUP commands)
        "l" = list files (LIST, NLST, STAT, MLSD, MLST, SIZE commands)
        "r" = retrieve file from the server (RETR command)
    Write permissions:
        "a" = append data to an existing file (APPE command)
        "d" = delete file or directory (DELE, RMD commands)
        "f" = rename file or directory (RNFR, RNTO commands)
        "m" = create directory (MKD command)
        "w" = store a file to the server (STOR, STOU commands)
        "M" = change file mode / permission (SITE CHMOD command) New in 0.7.0
        "T" = change file modification time (SITE MFMT command) New in 1.5.3
    """

    def __init__(self):

        authorizer = DummyAuthorizer()
        authorizer.add_anonymous(settings.FTP_SERVED_DIR, perm="elr")

        handler = FTPHandler
        handler.authorizer = authorizer

        self.server = FTP((settings.FTP_HOST, settings.FTP_SERVER_PORT), handler)

    def serve(self):
        self.server.serve_forever()


class FTPClient():

    def __init__(self):
        super(FTPClient, self).__init__()

    def download(self, torrent):

        ftp = ftplib.FTP()
        ftp.connect(torrent.host, settings.FTP_SERVER_PORT)
        ftp.login()
        remote_file = torrent.file_name
        torrent.file_name = self.getUniqueFileName(torrent.file_name)
        print("Downloading:", torrent.file_name)
        try:
            ftp.retrbinary("RETR " + remote_file ,open(os.path.join(settings.DOWNLOADS_DIR, torrent.file_name), 'wb').write)
        except ConnectionRefusedError:
            print("ConnectionRefusedError: Could not download file")

        ftp.quit()


    def getUniqueFileName(self, filename):
        """
            This is mainly for testing, though will not hurt to have it in production
            When testing, the FTP server and client are often reading and writing to the
            same file, causing undefined behaviour (usually the file would end up as a
            0 byte file)
        """
        local_file = os.path.join(settings.DOWNLOADS_DIR, filename)
        if os.path.isfile(local_file):
            x = 1
            local_file = os.path.splitext(local_file)[0] + " (" + str(x) + ")" + os.path.splitext(local_file)[1]
            while os.path.isfile(local_file):
                x += 1
                local_file = os.path.isfile(os.path.splitext(local_file)[0] + " (" + str(x) + ")" + os.path.splitext(local_file)[1])
        return local_file


class InitialisationException(BaseException):
    pass
