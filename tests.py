import network_tools as net
import unittest


class TestNetworkTools(unittest.TestCase):

    def test_tcp_client(self):

        client = net.TCPClient(identifier='Unique Client', wait=2, suppress_output=True)
        self.assertEqual(client.identifier, 'Unique Client')
        self.assertEqual(client.wait, 2)
        self.assertEqual(client.timeout, 2)
        self.assertEqual(client.blocking, False)
        self.assertEqual(client.timeout, client.wait)
        self.assertEqual(client.port, 10000)
        self.assertEqual(client.port, 10000)
        success, response = client.send('asfsf')
        print(response)

    def test_tcp_server(self):

        server = net.TCPServer(blocking=False, identifier='Unique Server', suppress_output=True, ack='Success')
        self.assertEqual(server.identifier, 'Unique Server')
        self.assertEqual(server.wait, 1)
        self.assertEqual(server.timeout, server.wait)
        self.assertEqual(server.blocking, False)
        self.assertEqual(server.port, 10000)

        del server

        server = net.TCPServer(blocking=False, wait=3, port=12345, suppress_output=True)
        self.assertEqual(server.identifier, 'Unnamed server')
        self.assertEqual(server.port, 12345)
        self.assertEqual(server.wait, 3)
        self.assertEqual(server.timeout, server.wait)

if __name__ == '__main__':
    unittest.main()
