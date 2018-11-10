import network_tools as net


# Example TCP Client
client = net.TCPClient(identifier=1, wait=1)

while True:

    data = client.send("penis")
    print(data)


# Example TCP Server
server = net.TCPServer(blocking=False, identifier=1)

while True:

    data = server.listen()
    print(data)
