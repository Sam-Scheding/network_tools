import network_tools as net
import sys

def main():
    port = 12348
    if sys.argv[1] == '-s':
        server = net.UDPServer(port=port)

        while True:
            sender, data = server.listen()
            print(data)

    elif sys.argv[1] == '-c':
        client = net.UDPClient(port=port)
        client.send("Hello")

    if sys.argv[1] == '-s':
        server = net.TCPServer(port=port, ack='ACK')

        while True:
            sender, data = server.listen()
            print(data)

    elif sys.argv[1] == '-c':

        client = net.TCPClient(port=port)
        response = client.send("Hello")
        print(response)


if __name__ == '__main__':
    main()
