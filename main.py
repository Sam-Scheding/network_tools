import network_tools as net


client = net.TCPClient(host="192.168.0.3", port=3000, identifier=1, wait=1)

while True:

    data = client.send("penis")
    print(data)

# server = net.TCPServer(blocking=False, identifier=1)
#
# while True:
#
#     data = server.listen()
#     print(data)
