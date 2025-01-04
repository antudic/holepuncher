import socket

def main():

    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0", 1337))

    print("UDP thread started")

    while True:
        _data, addr = sock.recvfrom(2048)

        # we reply with the port of the request in case the NAT changes the original port of the UDP
        # package. We don't reply with the IP since the client is listening to "0.0.0.0" either way. 
        sock.sendto(int.to_bytes(addr[1], 2, "big"), addr)

"""
import weakref

regularDict = {"one": 1}
weakReffable = lambda obj: type("", tuple(), {attr: getattr(obj, attr) for attr in obj.__dir__()})()

newDict = weakReffable(regularDict)
del regularDict

refDict = weakref.proxy(newDict)
refDict["two"] = 2

print(newDict) # {'one': 1, 'two': 2}
"""
