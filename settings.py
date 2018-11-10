from uuid import getnode as get_mac
from urllib import parse as urlparse
import socket, os
import netifaces
from datetime import timedelta

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEBUG = True

# Terminal Colours
RED = '\033[01;31m'
NORMAL = '\033[00m'
GREEN = '\033[0;32m'

# This computer's WiFi interface MAC Address
def get_mac_address(interface):

    success = False
    try:
        w_if = netifaces.ifaddresses(interface)[netifaces.AF_LINK][0]
        success = True
    except ValueError:
        print("{}Couldn't find {}.{}".format(RED, interface, NORMAL))

    if not success:
        print('{}There were no wireless interfaces that were valid for the mesh. Call Pete for help.{}'.format(RED, NORMAL))
        print("{}Are you sure the WiFi dongle is plugged in to the VM and you are running start mesh?{}".format(RED, NORMAL))
        exit()

    print('{}Successfully bound to {}{}!'.format(GREEN, w_if['addr'], NORMAL))
    return w_if['addr']
