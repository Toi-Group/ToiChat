#!/usr/bin/env python3

#import necessary library files
#
import sys
import threading
from modules.toiChatServer import toiChatServer
from modules.toiChatClient import toiChatClient
from modules.toiChatter import toiChatter
from modules.toiChatNameServer import toiChatNameServer
from modules.testSSH import *
from gi.repository import Gtk, GObject
import time
#create main class
#this class will load .glade file and display first login window
#
class toiChatGui():
    
    def __init__(self):
        #Load glade file for login window
        #initilize all buttons and entry boxes
        #
        #Login window
        #
        self.builder = Gtk.Builder()
        self.builder.add_from_file('toiTest.glade')
        self.window = self.builder.get_object('mainWindow')
        self.userName = self.builder.get_object('user_name')
        self.passWord = self.builder.get_object('pass_word')
        self.miscellaneous = self.builder.get_object('misc')
        self.errorMessage = self.builder.get_object('errorLogin')
        self.login = self.builder.get_object('Login')
        self.quit = self.builder.get_object('quit')
        self.spinner = self.builder.get_object('spinner1')
	
        #dns window
        #
        self.window_dns = self.builder.get_object('dnsWindow')
        self.menubar_dns = self.builder.get_object('menubar1')
        #self.combobox_dns = self.builder.get_object('combobox1') 
        self.listview_dns = self.builder.get_object('treeview1')
        self.liststore_dns = self.builder.get_object('liststore1')
          
        if(self.window):
            self.window.connect('destroy',Gtk.main_quit)
        if(self.window_dns):
            self.window_dns.connect('destroy',Gtk.main_quit)
          
        #connect objects that have reactions to functions defined later in class
        #
        self.dic = {
            "on_Login_clicked" : self.loginClick,
            "on_quit_clicked" : self.quitClick
        }  
    
        self.builder.connect_signals(self.dic)

        #show login window
        #
        self.window.show()
        
         
    
    #login button clicked
    #grab username, password, and misc information
    #start server
    #display error message if needed
    # 
    def loginClick(self,widget):
        
        callSign = self.userName.get_text()
        self.routerPassword = self.passWord.get_text()
        miscInformation = self.miscellaneous.get_text()

        if not self.routerPassword:
            self.errorMessage.set_text('No Password entered')
        
        elif not callSign:
            self.errorMessage.set_text('No Username Entered')
       
        else:
            #Start toichatclient
            #
            print('Starting toichatclient\n')
            if not miscInformation:
                self.myToiChatClient = toiChatClient(callSign)
            else:
                self.myToiChatClient = toiChatClient(callSign,miscInformation)
            print('Starting Nameserver\n Updating Nameserver\n Starting toichatserver\n')
            
            try: 
                self.verified_routerPassword = testSSH(self.routerPassword)
            except Exception as e:
                self.errorMessage.set_text(str(e))
                return
            
            #start the spinner 
            #
            self.spinner.start()

            #create thread to start server when the spinner is spinning
            #
            start_ToiChat_thread = threading.Thread(target=self.start_ToiChat)
            start_ToiChat_thread.daemon = True
            start_ToiChat_thread.start()

    #Start the server and do a forcednsupdate
    #This must be threaded as it executes blocking operations 
    #
    def start_ToiChat(self):
 
        self.myNameServer = toiChatNameServer(self.myToiChatClient,self.verified_routerPassword)
        print('1')
        self.myToiChatClient.updateNameServer(self.myNameServer)
        print('2')
        self.myToiChatServer = toiChatServer(self.myNameServer)
        print('3')
        self.myToiChatServer.startServer()
        print('4')
        self.myNameServer.attemptFindServer()
        print('5')
        
        self.spinner.stop()
        self.dnsWindow()
    
    def quitClick(self, widget):
        print('quit')
        #stop server -- not needed here I don't think
        #   
        #if (myToiChatServer):
            #self.myToiChatServer.stopServer()
        sys.exit(0)

    #open DNS window and hide login window
    #
    def dnsWindow(self):
        self.window.hide()
        self.window_dns.show()
        self.listview_dns.AddAttribute(('hello world',))
        

#create the window and wait in a loop to recieve interrupts or signals
#
if __name__ == "__main__":
    GObject.threads_init()
    toichatGui = toiChatGui()
    Gtk.main()  