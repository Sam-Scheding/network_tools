import network_tools as net
import unittest


class TestNetworkTools(unittest.TestCase):

    def test_tcp_client(self):

        client = net.TCPClient(identifier='Unique Client', timeout=2, suppress_output=True)
        self.assertEqual(client.identifier, 'Unique Client')
        self.assertEqual(client.timeout, 2)
        self.assertEqual(client.blocking, True)
        self.assertEqual(client.port, 10000)


    def test_tcp_server(self):

        server = net.TCPServer(port=10001, blocking=False, identifier='New name', suppress_output=True, ack='Success')
        self.assertEqual(server.identifier, 'New name')
        self.assertEqual(server.timeout, 1)
        self.assertEqual(server.blocking, False)
        self.assertEqual(server.port, 10001)

        server = net.TCPServer(blocking=False, timeout=3, port=12345, suppress_output=True)
        self.assertEqual(server.identifier, 'Anonymous TCP Server')
        self.assertEqual(server.port, 12345)
        self.assertEqual(server.timeout, 3)

        # Test invalid timeouts
        kwargs = { 'timeout': -1, 'suppress_output': True, }
        server = net.TCPServer(**kwargs)
        self.assertRaises(ValueError, server.listen)

        # Test negative max_connections
        args = []
        kwargs = {'port': 12343, 'max_connections': 0, 'suppress_output': True, }
        server = net.TCPServer(**kwargs)
        self.assertRaises(ValueError, server.listen)

        # Test ack
        server = net.TCPServer(ack='bar')
        self.assertEqual(server.ack, 'bar')

        # Test buffer_size
        server = net.TCPServer(port=56544, timeout=1, blocking=False)
        server.buffer_size = -1
        self.assertRaises(ValueError, server.listen)
        server.buffer_size = 4097
        self.assertRaises(ValueError, server.listen)
        server.buffer_size = 0
        server.listen()

        # Assert succeeds
        server.buffer_size = 4096
        server.listen()

if __name__ == '__main__':
    unittest.main()
