# Standard Lib
import socket, struct, os, pickle, sys, time, json

# 3rd Party
import requests

# Local Imports
import settings

class BaseConnection():

    suppress_output = False
    identifier = ""
    port = 10000
    wait = 1
    timeout = wait

    def __init__(self, *args, **kwargs):

        # Go through keyword arguments, and either save their values to our
        # instance, or raise an error.
        for key, value in kwargs.items():
            setattr(self, key, value)


class TCPServer(BaseConnection):

    try:
        host = socket.gethostbyname(socket.gethostname())
    except socket.gaierror:
        host = socket.gethostbyname('localhost')

    max_connections = 10
    blocking = True
    identifier = "Unnamed server"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            # Instantiate the socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.bind((self.host, self.port))
            self.socket.listen(self.max_connections)
            self.socket.setblocking(self.blocking)
        except OSError as e:
            print("{}Address {} could not be assigned.{}".format(settings.RED, self.host, settings.NORMAL))
            exit()

        if not self.suppress_output:
            print("{}{} opened on {}:{}{}".format(settings.GREEN, self.identifier, self.host, self.port, settings.NORMAL))

    def listen(self, unpickle_data=False):

        if self.blocking and not self.suppress_output:
            print("{} is blocking on {}:{}".format(self.identifier, self.host, self.port))

        try:

            connection, address = self.socket.accept()
            data = []

            while True:
                packet = connection.recv(4096)  # TODO: Known Issue. This fails if the packet is larger that 4096 bytes
                if not packet:
                    break
                data.append(packet)

            if unpickle_data:
                data = pickle.loads(b"".join(data))

            if not self.suppress_output:
                print("{}{} Received: {}{}".format(settings.GREEN, self.identifier, str(data)[:30], settings.NORMAL))

            return data, address

        except socket.error:
            return None, None

        finally:
            if not self.blocking:
                time.sleep(self.wait)


class TCPClient(BaseConnection):

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if 'host' not in kwargs.keys():
            raise InitialisationException("{}host is not set{}".format(settings.RED, settings.NORMAL))
        if 'port' not in kwargs.keys():
            raise InitialisationException("{}port is not set{}".format(settings.RED, settings.NORMAL))

        identifier = "Unnamed client"

    def send(self, data, pickle_data=False):

        if pickle_data:
            data = pickle.dumps(data)

        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.wait)
            self.socket.connect((self.host, self.port))
            self.socket.send(data)
            self.socket.close()
            return True

        except socket.timeout:
            print('{}{} timed out...{}'.format(settings.RED, self.identifier, settings.NORMAL))
            return False

        except OSError as e:
            print('{}ERROR: {}{}'.format(settings.RED, e, settings.NORMAL))
            return False

        finally:
            self.socket.close()

class MulticastServer():

    def __init__(self, **kwargs):

        super(MulticastServer,).__init__()

        try:
            # Look up multicast group address in name server and find out IP version
            addrinfo = socket.getaddrinfo(settings.IPV4_HOST, None)[0]

            # Create a socket
            self.server_socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)
            self.server_socket.setblocking(False)
            # Allow multiple copies of this program on one machine
            # (not strictly needed)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind it to the port
            self.server_socket.bind(('', settings.MULTICAST_SERVER_PORT))

            group_bin = socket.inet_pton(addrinfo[0], addrinfo[4][0])
            # Join MultiCast group
            if addrinfo[0] == socket.AF_INET:  # IPv4
                mreq = group_bin + struct.pack('=I', socket.INADDR_ANY)
                self.server_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            else:  # IPV6
                mreq = group_bin + struct.pack('@I', 0)
                self.server_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_JOIN_GROUP, mreq)
            print("Multicast server opened on: " + str(settings.MULTICAST_SERVER_PORT))
        except OSError:
            print("No Internet connection")
            print("Could not start Multicast Server")
            print("TODO: Give the user a retry button that restarts the MultiCast Server")

    def check_for_data(self):

        try:
            data, sender = self.server_socket.recvfrom(1500)

            while data[-1:] == '\0':
                data = data[:-1]  # Strip trailing \0's
            query_object = pickle.loads(data)
            # query_object.addr = sender
            # print("Got: " + str(query_object) + " from: " + str(sender))
            return query_object, sender

        except socket.error:
            return None, None


class MulticastClient():

    def send(self, data):
        addrinfo = socket.getaddrinfo(settings.IPV4_HOST, None)[0]

        server_socket = socket.socket(addrinfo[0], socket.SOCK_DGRAM)

        # Set Time-to-live (optional)
        ttl_bin = struct.pack('@i', settings.MULTICAST_TTL)
        if addrinfo[0] == socket.AF_INET:  # IPv4
            server_socket.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, ttl_bin)
            sock_type = socket.IPPROTO_IP
        else:
            server_socket.setsockopt(socket.IPPROTO_IPV6, socket.IPV6_MULTICAST_HOPS, ttl_bin)
            sock_type = socket.IPPROTO_IPV6

        # if not settings.LOCAL_DEBUG:  # Ignore packets sent from self
        #     server_socket.setsockopt(sock_type, socket.IP_MULTICAST_LOOP, 0)

        server_socket.sendto(pickle.dumps(data), (addrinfo[4][0], settings.MULTICAST_SERVER_PORT))
        print("Multicast query sent for: " + str(data))


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

        super(TorrentObject,).__init__()
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

"""
    Exceptions
"""
class InitialisationException(BaseException):
    pass
