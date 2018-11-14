import network_tools as net


# Example TCP Client
client = net.TCPClient()

while True:

    data = client.send("dummy data")
    print(data)

"""
    Example TCP Servers
"""

# If no parameters are set, the server defaults to 127.0.0.1:10000
server = net.TCPServer()

# Or you can create a server with the host and port set like this:
server = net.TCPServer(host="0.0.0.0", port=12345)

# There are other parameters you can set as well:
#   - blocking <bool>: If True, listen() will hang until it receives data, then return the data.
#     If blocking is False, listen() will wait for a specified number of seconds before timing out.
#   - wait <None or positive int>: If blocking == False, a wait time in seconds to specify how long
#     listen() should wait for a packet before returning.
#   - identifier: A name for the server
#   - ack: If set, the server will respond to all requests with the ack value (the return value of
#     listen() is still the request data).
#   - buffer_size <int:[0->4096]>: The size, in bytes of the buffer. Default is 4096
#   - suppress_output <bool>: If True, info and debugging output will not print. Errors are unaffected.
kwargs = {
    'blocking': False,
    'identifier': 'My Server',
    'ack': 'bar',
    'buffer_size': 2048,
    'suppress_output': False,
}
server = net.TCPServer(**kwargs)


# Blocking example
server = net.TCPServer()  # default blocking value is True
request = server.listen()
print(request)

# Non-blocking example
server = net.TCPServer(timeout=2)

while True:

    request = server.listen()

    if request:
        print(data)
    else:
        print('Still no data')
