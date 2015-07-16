# !python3
#

# Source: https://wiki.python.org/moin/UdpCommunication
#

# This code sends a message to another script running at the UDP_IP destination
# the script receive_udp.py
#

import socket

# Setup connection to other Pi
# Prompt for IP. Default localhost if null input
#
UDP_IP = input("Enter the IP of the client machine you will be communicating with. (Default: '127.0.0.1')>> ") or '127.0.0.1'

# Prompt for PORT. Default 65104 if null input
#
while True: 
    try:
        UDP_PORT = int(input("Enter the PORT you will be communicating over. (Default. 65104)>> ") or '65104')
    except ValueError:
        print("You need to type in a valid PORT number!")
        continue
    else:
        if UDP_PORT in range(65535):
            break
        else:
            print("Port must be in range 0-65535!")
            continue
# Bind the socket
#
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # Send over internet using UDP


# Run the program forever
while True:
    # Prompt the user for a keystroke or message to send
    #
    MESSAGE = input("What would you like to send (keyboard input)>> ")
    
    # Let the user know what IP and Port we are using to communicate with
    #
    print ('Sending message to UDP target: {}:{}' .format(str(UDP_IP), UDP_PORT))
    
    # Send the message using the socket opened
    #
    sock.sendto(bytes(MESSAGE, 'UTF-8'), (UDP_IP, UDP_PORT))
    
    # Confirm with the user the message sent succesfully
    #
    print ("Successfully sent message: {}" .format(str(MESSAGE)))