 #!/usr/bin/env python

import socket

TCP_IP = raw_input('Enter IPv4 address of Recipient: ')
TCP_PORT = 5005


s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect((TCP_IP, TCP_PORT))

while True:

    MESSAGE = raw_input("Enter Message: ")
    s.send(MESSAGE)
