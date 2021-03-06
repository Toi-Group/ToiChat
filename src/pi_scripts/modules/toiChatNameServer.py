#!/usr/bin/env python3

# 
# Python toiChat Front-End Runner
#   Script interacts with background services such as toiChatServer and
#   toiChatClient.
#
#
# Created on: 02/07/2016
# Author: Toi-Group
#


from modules.testSSH import testSSH # Used to automate SSH login
from modules.listen_router import listen_router # Used for accepting ARP
                                                # requests
from modules.protobuf import ToiChatProtocol_pb2 # Used for DnsMessage 
                                                 # Protocol
from modules.toiChatClient import toiChatClient # Used for replying to 
                                                # received messages
import time # Used for documenting the local time of the DNS register
from threading import Timer, Lock, Thread # Used for pining servers every
                                          # interval.
import pprint # for printing dns tables nicely
import socket, struct, fcntl # Used for resolving local IP address
from modules.conn_router import conn_router # Used for sending a request
                                            # mesh network lan info to 
                                            # local broadband hamnet router
from modules.gatewayIP import gatewayIP # Used for finding the address
                                        # of the local broadband hamnet
                                        # router
from modules.toiChatPing import * # Used for pinging machines in
                                  # the network.
import readline # Used for reading in stdout to print to console now.
import logging # Used for logging NameServer activities 

class toiChatNameServer():
    # Types of commands to expect
    #
    getCommand={
        0:"register",
        1:"request"
    }
    DNS_PING_INTERVAL = 20 # In seconds

    # -- START CLASS CONSTRUCTOR -- 
    #
    # Upon instantiation adds its own name, ipv4 address, 
    # and description to the dns lookup table
    #
    # -- END CLASS CONSTRUCTOR -- 
    def __init__(self, toiChatClient):
        # Logging instance where should we save nameserver logs to
        #
        self.logger = logging.getLogger(__name__)

        # Prompt for Router's root password
        #
        self.user_pwd = testSSH()

        # Make router listen for ARP requests
        #
        listen_router(self.user_pwd)    
    
        # Store ToiChatClient to used to send dns messages
        #
        self.myToiChatClient = toiChatClient

        # Variable to tell wait until next thread 
        #
        self.stopDNSPing = False
        self.dnsTableLock = Lock()

        # Define dictionary to hold values of user name
        # and key pairing of IP and other relevant information
        # User name will be keys of the dictionary while the values
        # will be the IPs of the user
        #
        # DICTIONARY FORMAT:
        # self.dns = {
        #     clientname0 = {
        #         clientId = IPv4 address
        #         dateAdded = <DATE CLIENT FIRST CONNECTED>
        #         description = <MISC INFOMATION OF CLIENT>
        #         lastPingVal = <PING VALUE> # Does not transmit in DNS Reg
        #     }
        #     clientname1 = {
        #         clientId = IPv4 address
        #         dateAdded = <DATE CLIENT FIRST CONNECTED>
        #         description = <MISC INFOMATION OF CLIENT>
        #     }
        #     clientname2 = {
        #         clientId = IPv4 address
        #         dateAdded = <DATE CLIENT FIRST CONNECTED>
        #         description = <MISC INFOMATION OF CLIENT>
        #     }
        #     ... LIST CAN GROW ...
        # }
        #
        #
        #
        self.dns = {}

        self.logger.info("Starting new toiChatNameServer instance.")

        # Register local machine in DNS replacing any old values
        #
        self.addToDNS(self.myToiChatClient.getName(), self.getMyIP(), \
            time.strftime("%Y%m%d - %H:%M:%S"), \
            self.myToiChatClient.getDescription())

        # Create thread to loop DNS Ping every 3 mins.
        #
        self.S = Thread(target=self.__loopPingDNS__)
        self.S.daemon = True
        self.S.start()

    # Print the current dns lookup table to the console
    #
    def printDNSTable(self):
        pp = pprint.PrettyPrinter(width=41)
        pp.pprint(self.dns)
        return 1
        
    # Print the current clients in the DNS table
    #
    def printClients(self):
        pp = pprint.PrettyPrinter(width=41)
        # To print all clients we first have to remove our name from the 
        # dns table
        #
        #myName = self.myToiChatClient.getName()
        #clientList = []
        #for key in self.dns.keys():
        #    if not key == myName:
        #        clientList.append(key)
        pp.pprint(self.getClients())
        return 1
    
    def getClients(self):
        myName = self.myToiChatClient.getName()
        clientList = []
        for key in self.dns.keys():
            if not key == myName:
                clientList.append(key)
        return(clientList)     

    # Returns the IPv4 address of the local machine for the given interface
    # 
    # Sourced from: http://stackoverflow.com/questions/166506/finding-local-ip-addresses-using-pythons-stdlib
    def getMyIP(self, iface = 'eth0'):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sockfd = sock.fileno()
        SIOCGIFADDR = 0x8915
        ifreq = struct.pack('16sH14s', iface.encode('utf-8'), \
            socket.AF_INET, b'\x00'*14)
        try:
            res = fcntl.ioctl(sockfd, SIOCGIFADDR, ifreq)
        except:
            return None
        ip = struct.unpack('16sH2x4s8x', res)[2]
        return socket.inet_ntoa(ip)

    # Adds one client to the internal dictionary
    #
    def addToDNS(self, clientName, clientId, dateAdded, description):
        # Inform DNS ping thread to kill
        #
        self.stopDNSPing = True

        # Acquire DNS table manipulate lock
        #
        self.dnsTableLock.acquire()

        # Print to log file we are adding a new entry
        #
        self.logger.info("Adding - '" + str(clientName) + "' to " + \
            "DNS table.")
        # Update dictionary with passed information
        #
        self.dns[clientName] = {}
        self.dns[clientName]['clientId'] = clientId
        self.dns[clientName]['dateAdded'] = dateAdded
        self.dns[clientName]['description'] = description

        # Release manipulating the DNS table to other threads
        #
        self.dnsTableLock.release()

        # Inform DNS ping thread to kill
        #
        self.stopDNSPing = False
        return 1

    # Removes one client to the internal dictionary
    #
    def removeDNSByHostname(self, clientName):
        # Inform DNS ping thread to kill
        #
        self.stopDNSPing = True

        # Acquire DNS table manipulate lock
        #
        self.dnsTableLock.acquire()

        # Print to log file we are removing a new entry
        #
        self.logger.info("Removing - '" + str(clientName) + "' from " + \
            "DNS table.")

        # Update dictionary with passed information
        #
        del self.dns[clientName]

        # Release manipulating the DNS table to other threads
        #
        self.dnsTableLock.release()

        # Inform DNS ping thread to kill
        #
        self.stopDNSPing = False
        return 1

    # Updates the current machines hostname entry in the internal dictionary
    #   
    def updateMyName(self, oldName, newName):
        userDesc = self.lookupDescByHostname(oldName)
        removeDNSByHostname(oldName)
        return self.addToDNS(newName, self.getMyIP(), \
            time.strftime("%Y%m%d - %H:%M:%S"), userDesc)

    # method to return IP of user the client is attempting to contact
    # returns 'None' if IP does not exist
    #   
    def lookupIPByHostname(self, userHostname):
        try:
            IP = self.dns[userHostname]['clientId']
        except KeyError:
            return None
        return IP

    # method to return IP of user the client is attempting to contact
    # returns 'None' if IP does not exist
    #   
    def lookupHostnameByIP(self, userIP):
        # Inform DNS ping thread to kill
        #
        self.stopDNSPing = True

        # Acquire DNS table manipulate lock
        #
        self.dnsTableLock.acquire()
        for hostname in self.dns:
            if self.dns[hostname]['clientId'] == userIP:
                return hostname
        # Release manipulating the DNS table to other threads
        #
        self.dnsTableLock.release()

        # Inform DNS ping thread to kill
        #
        self.stopDNSPing = False
        return None

    # method to return last update of passedIP
    #   
    def lookupAddedByHostname(self, userHostname):
        try:
            update = self.dns[userHostname]['dateAdded']
        except KeyError:
            return None
        return update

    #  method to return last update of passed hostname
    #   
    def lookupUpdateByIP(self, userIP):
        return self.lookupAddedByHostname(userHostname)

    # Return number of entries in our table
    #   
    def lookupDnsLegnth(self):
        return len(self.dns)

    # Return number of entries in our table
    #   
    def lookupDescByHostname(self, userHostname):
        try:
            update = self.dns[userHostname]['description']
        except KeyError:
            return None
        return update

    # -- START FUNCTION DESCR --
    #
    # Initiates a DNS table sync with designated client
    #
    # Inputs:
    #   - toiServerIP = The server we should sync with
    #
    # Outputs:
    #   None
    #
    # -- END FUNCTION DESCR --
    def syncDNS(self, toiServerIP):
        requestDNS = self.createRequestDnsMessage()
        self.myToiChatClient.sendMessage(toiServerIP, requestDNS)
        return 1

    # -- START FUNCTION DESCR --
    #
    # Message locates the local Broadband Hamnet router and will
    # send a command asking it to find all attached devices in the 
    # mesh network. It will then attempt to contact each device in the
    # network to see if any are running an instance of toiChatServer
    #
    # Inputs:
    #   - toiServerPort = The port which we will attempt to contact other
    #       toiChatServers.
    #
    # Outputs:
    #   - Upon successful connection to another toiChatServer we will update
    #       our current DNS table with its
    #   - Upon failure to find another toiChatServer we will return an error
    #
    # -- END FUNCTION DESCR --
    def attemptFindServer(self, toiServerPORT=5005):
        # Get a list of IPs running Toi-Chat software on the mesh network
        #
        listIPs = conn_router(gatewayIP(), self.user_pwd)
        self.logger.debug("List of returned IPs: " + str(listIPs))
        # Check to see if there are any IPs in the returned ARP list
        #
        if listIPs == None:
            return 0

        # Sort the list of IPs be increasing distance
        #
        sortIPs = pingIPSort(listIPs)[0]

        # Create a request DNS information request message
        #
        requestDNS = self.createRequestDnsMessage()
        self.logger.debug("List of potential TOIChat Hosts:" + \
            str(sortIPs))

        for toiServerIP in sortIPs:
            # Print to stdout what we are trying to connect to
            #
            self.logger.debug("Trying to connect to '" + \
                str.strip(toiServerIP) + "'.")
            try:
                self.myToiChatClient.sendMessage(toiServerIP, requestDNS, \
                    toiServerPORT)
            except Exception as e:
                if toiServerIP == sortIPs[len(sortIPs)-1]:
                    # We tried all IPs in the list and could not connect to 
                    # any. Return error to stdout informing the user
                    self.logger.warning("Could not connect to '" + \
                        str.strip(toiServerIP) + "'. Exited with status: " + \
                        str(e) + ". Exhausted known list of hosts.")
                    return 0
                else:
                    self.logger.info("Could not connect to '" + \
                        str.strip(toiServerIP) + "'... Exited with status: " + \
                        str(e) + "Trying next IP in list.")
                    continue 
            # Did not fail to connect. Connection to server successful
            # Break out of for loop
            #
            break
        return 1

    # --------------------------------------------------------------------
    # ------------------- START OF MSG HANDLING FUNCTIONS ----------------
    # --------------------------------------------------------------------
    # Handle DnsMessage type received from a toiChatServer instance.  
    # Message type is already known to be DNS message
    #
    def handleDnsMessage(self, myDnsMessage):
        if myDnsMessage.command == self.getCommand[0]:
            self.logger.info("Received a '" + \
                str(self.getCommand[0]) + "' DNS message from '" + \
                myDnsMessage.id.clientId + "'.")
            self.handleRegisterDNS(myDnsMessage)
        elif myDnsMessage.command == self.getCommand[1]:
            self.logger.info("Received a '" + \
                str(self.getCommand[1]) + "' DNS message from '" + \
                myDnsMessage.id.clientId + "'.")
            self.handleRequestDNS(myDnsMessage)
        else:
            self.logger.warning("Unknown DNSMessage Command: '" + \
                str(myDnsMessage.command) + "' received from '" + \
                myDnsMessage.id.clientId + "'.")
            return 0
        return 1

    # Extract the name, ipv4 address, last update, and misc information from 
    # DNS message and register into local DNS
    #
    def handleRegisterDNS(self, registerDNSMessage):
        # We started thinking we have a more updated table
        #
        moreUpdated = False

        # Keep track of number of clients we add to our table
        #
        counter = 0
        # Loop through all repeated clients in DnsMessage
        #
        for newClient in registerDNSMessage.clients:
            # Check if user is in the DNS already
            #

            if newClient.clientName in self.dns:
                # If user is already in DNS check if receiver has updated
                # client information
                #
                if self.lookupAddedByHostname(newClient.clientName) > \
                    newClient.dateAdded:
                    # We skip adding since our dns has a more updated
                    # entry. We also need to reply to the client noting
                    # we have a more updated entry
                    #
                    moreUpdated = True
                    continue
                # The two tables are in sync for this client so we continue
                #
                elif self.lookupAddedByHostname(newClient.clientName) == \
                    newClient.dateAdded:
                    continue

            # The sender has a more updated dns entry for this client
            # so we update our table
            #
            self.addToDNS(newClient.clientName, newClient.clientId, \
                newClient.dateAdded, newClient.description)
            counter += 1

        # Our dns table was more updated compared to the sender so
        # we reply with our table
        #
        if (moreUpdated == True) or \
            (len(registerDNSMessage.clients)-counter < self.lookupDnsLegnth()):
            # We send a register dns message back to the sender
            #
            self.handleRequestDNS(registerDNSMessage)
        return 1

    # Handles a DnsMessage from a client who is requesting our DNS table.
    # Returns a registerDNS message to the client
    #
    def handleRequestDNS(self, requestDNSMessage):
        # Get the information about the client requesting DNS information
        #
        returnAddress = requestDNSMessage.id.clientId

        # Create a new Register DNS Message
        #
        myRequestDNS = self.createRegisterDnsMessage()

        self.logger.info("Sending a '" + str(self.getCommand[1]) + \
            "' message to '" + str(returnAddress) +"'.")
        # Send message back to requester
        #
        self.myToiChatClient.sendMessage(returnAddress, myRequestDNS)
        
        return 1        
  
    # Send our DNS table to another machine
    # Populate a DnsMessage Register message type with information about
    # each client in our DNS table. 
    #
    def createRegisterDnsMessage(self):
        # Inform DNS ping thread to kill
        #
        self.stopDNSPing = True

        # Create a template DNS message
        #
        registerDNS = \
            self.myToiChatClient.createTemplateIdentifierMessage("dnsMessage")

        # Populate the command command with status of "register"
        #
        registerDNS.dnsMessage.command = self.getCommand[0]

        # Create a DNSclient message for each client in our DNS dictionary
        #
        registerDNSClient = ToiChatProtocol_pb2.Identifier()

        # Acquire DNS table manipulate lock
        #
        self.dnsTableLock.acquire()

        # Populate our registerDNS message with DNSClients from our
        # DNS dictionary
        #
        for hostname in self.dns:
            registerDNSClient = registerDNS.dnsMessage.clients.add()
            registerDNSClient.clientName = hostname
            registerDNSClient.clientId  = self.dns[hostname]['clientId']
            registerDNSClient.dateAdded = self.dns[hostname]['dateAdded']
            registerDNSClient.description = self.dns[hostname]['description']

        # Release manipulating the DNS table to other threads
        #
        self.dnsTableLock.release()

        # Inform DNS ping thread to kill
        #
        self.stopDNSPing = False

        # Return DnsMessage Type
        #
        return registerDNS
   
    # Create a message requesting the DNS table from another machine
    #
    def createRequestDnsMessage(self):
        # Create a template DNS message
        #
        requestDNS = \
            self.myToiChatClient.createTemplateIdentifierMessage("dnsMessage")

        # Populate the command we will use in the message with the
        # request dnsMessage value
        #
        requestDNS.dnsMessage.command = self.getCommand[1]

        #return requestDNS message
        #
        return requestDNS

    # -----------------------------------------------------------------
    # ------------------- START OF AUTO PING FUNCTIONS ----------------
    # -----------------------------------------------------------------
    
    # -- START FUNCTION DESCR --
    #
    # Will periodically create a thread to ping servers in our dns table
    #
    # Inputs:
    #   - None
    #
    # Outputs:
    #   - Will update the DNS table with ping times to other servers
    #   - May delete entries from internal DNS dictionary. 
    #
    # -- END FUNCTION DESCR --
    def __loopPingDNS__(self):
        # Loop every 3 mins
        #
        Timer(self.DNS_PING_INTERVAL,self.__loopPingDNS__).start()
        self.__pingDNSAvaliable__()

    # -- START FUNCTION DESCR --
    #
    # Update DNS table in background by pinging different machines in our
    # DNS table
    #
    # Inputs:
    #   - None
    #
    # Outputs:
    #   - Will update the DNS table with ping times to other servers
    #   - May delete entries from internal DNS dictionary. 
    #
    # -- END FUNCTION DESCR --
    def __pingDNSAvaliable__(self):
        # Determine how large the dns table is and send a dynamic number 
        # of ICMP packets depending if there are many clients or not.
        #
        dnsLegnth = self.lookupDnsLegnth()

        if dnsLegnth > 10:
            icmpPcks = 2
        elif dnsLegnth > 5:
            icmpPcks = 4
        else:
            icmpPcks = 6

        # Gain DNS table manipulation lock
        #
        self.dnsTableLock.acquire()

        # Create a list to contain IPs we could not reach
        #
        listToDelete = []

        # Loop through each entry in the internal DNS
        #
        for hostname in self.dns.keys():
            # Get if stopDNSPing status. Stop thread if true.
            #
            if self.stopDNSPing == True:
                # Log we quit pinging
                #
                self.logger.debug("Pinging stopped due to interrupt.")
                # Check to see if we should quit pinging
                #
                break

            # Ping user
            #
            avgPing = pingOne(self.lookupIPByHostname(hostname), icmpPcks)

            # If the Pi can not ping the client in its DNS table
            # assume the client went off-line. Delete it from our table
            #
            if avgPing == None:
                # Delete entry from DNS
                #
                listToDelete.append(hostname)
                self.logger.debug("'" + str(hostname) + "' did not " + \
                    "respond.")
                continue
            
            # Otherwise we update the lastPingVal of the client
            #
            self.logger.debug("'" + str(hostname) + "' responded. " + \
                "Average ping time = " + str(avgPing) + " ms. ")
            self.dns[hostname]['lastPingVal'] = avgPing

        # Check to see if we would be deleting our entire table
        #
        if len(listToDelete) == self.lookupDnsLegnth():
            # If the two tables match print that we are probably disconnected
            # from the Internet
            #
            self.logger.warning("We can not reach any clients. Please " + \
                "check your Internet connection.")

            # Erase the current stdout prompt but store it first
            # 
            sys.stdout.write('\r'+' '*(len(readline.get_line_buffer())+2)+'\r')

            # Print the message from the receiver
            #
            sys.stdout.write("Network connection error. Ensure you " + \
                "are connected to the network.")

            # Print the message that came before
            #
            sys.stdout.write(" >> " + readline.get_line_buffer())
            sys.stdout.flush()
        else: 
            # Delete all IPs we could not contact
            #
            for clientName in listToDelete:
                # Print to log file we are removing a new entry
                #
                self.logger.info("Removing - '" +\
                    clientName +  "' from DNS table.")
                del self.dns[clientName]

        # Release DNS table manipulation lock
        #
        self.dnsTableLock.release()
        return 1
