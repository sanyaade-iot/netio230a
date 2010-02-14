#
# -*- encoding: UTF8 -*-

# author: Philipp Klaus, philipp.l.klaus AT web.de


#   This file is part of netio230a.
#
#   netio230a is free software: you can redistribute it and/or modify
#   it under the terms of the GNU General Public License as published by
#   the Free Software Foundation, either version 3 of the License, or
#   (at your option) any later version.
#
#   netio230a is distributed in the hope that it will be useful,
#   but WITHOUT ANY WARRANTY; without even the implied warranty of
#   MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#   GNU General Public License for more details.
#
#   You should have received a copy of the GNU General Public License
#   along with netio230a.  If not, see <http://www.gnu.org/licenses/>.



# This class represents the multiple plug hardware Koukaam NET-IO 230A
# It can be configured using raw TCP communication.
# The class aimes at providing complete coverage of the functionality of the box
#  but not every action is supported yet.



###--------- ToDo next ------------
# http://koukaam.se/koukaam/forum/viewthread.php?forum_id=18&thread_id=399
# Command for enable wd with 360s delay on output 2:
# port wd 2 enable 192.168.10.101 10 360 1 3 enable enable



# for the raw TCP socket connection:
import socket
# for md5 checksum:
import hashlib
# for RegularExpressions:
import re
## for debugging (set debug mark with pdb.set_trace() )
#import pdb
# for math.ceil()
import math
# for shlex.shlex() (to parse answers from the NETIO 230A)
import shlex
# for errno codes (cf. <http://docs.python.org/library/errno.html>)
import errno

import time
### for date.today()
#from datetime import date
from datetime import datetime

TELNET_LINE_ENDING = "\r\n"
TELNET_SOCKET_TIMEOUT = 5

class netio230a(object):
    """netio230a is the basic class that you want to instantiate when communicating
    with the Koukaam NETIO 230A. It can handle the raw TCP socket connection and
    helps you send the commands to switch on / off powerSockets etc."""
    
    def __init__(self, host, username, password, secureLogin=False, customTCPPort=23):
        """netio230a constructor: set up an instance of netio230a by giving:
        
            host        the hostname of the NETIO-230A (may be in the form of something.dyndns.org or 192.168.1.2)
            username    the username you want to use to authenticate against the NETIO-230A
            password    the password (that belongs to username)
            secureLogin bool value specifying whether to use a hashed or a cleartext login. True is hightly recommended for insecure networks!
            customTCPPort  integer specifying which port to connect to, defaul: 23 (NETIO-230A must be reachable via KSHELL/telnet via hostname:customTCPPort)
        """
        self.__host = host
        self.__username = username
        self.__password = password
        self.__secureLogin = secureLogin
        self.__tcp_port = customTCPPort
        self.__bufsize = 1024
        self.__power_sockets = [ PowerSocket() for i in range(4) ]
        self.__create_socket_and_login()
    
    def __create_socket_and_login(self):
        # create a TCP/IP socket
        self.__s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.__s.settimeout(TELNET_SOCKET_TIMEOUT)
        self.__login()
 
    def __login(self):
        """Login to the server using the credentials given to the constructor.
           Note that this is a private method called by the constructor
           (so all connection details are set already)."""
        # connect to the server
        try:
            self.__s.connect((self.__host, self.__tcp_port))
            # wait for the answer
            data = self.__s.recv(self.__bufsize)
        except StandardError, error:
            if type(error) == socket.timeout:
                raise NameError("Timeout while connecting to " + self.__host)
                #print("There was a timeout")
            elif type(error) == socket.gaierror or type(error) == socket.error and error.errno == errno.ENETUNREACH:
                raise NameError("Unable to understand the host you gave: %s. Please give a correct IP address or domain name." % self.__host)
            elif type(error) == socket.error:
                if error.errno == errno.ECONNREFUSED:
                    raise NameError("The connection was refused by the remote host.\nPossible errors: wrong IP or wrong TCP port given or the telnet server on the NETIO-230A crashed.")
                elif error.errno == errno.EHOSTUNREACH:
                    raise NameError("There is no route to the host given: " + self.__host)
                
            # in any other case just hand on the risen error:
            raise error
        # The answer should be in the form     "100 HELLO E675DDA5"
        # where the last eight letters are random hexcode used to hash the password
        if self.__reSearch("^100 HELLO [0-9A-F]{8}"+TELNET_LINE_ENDING+"$", data) == None and \
           self.__reSearch("^100 HELLO [0-9A-F]{8} - KSHELL V1.1"+TELNET_LINE_ENDING+"$", data) == None and \
           self.__reSearch("^100 HELLO [0-9A-F]{8} - KSHELL V1.2"+TELNET_LINE_ENDING+"$", data) == None  :
            raise NameError("Error while connecting: Not received a \"100 HELLO ... signal from the NET-IO 230A")
        if self.__secureLogin:
            m = hashlib.md5()
            hash=str(data).split(" ")[2]
            msg=self.__username + self.__password + hash
            m.update(msg.encode("ascii"))
            loginString = "clogin " + self.__username + " " + m.hexdigest() + "\n"
            # log in using the hashed password
            self.__s.send(loginString.encode("ascii"))
        else:
            # log in however sending the password in cleartext
            self.__s.send("login " + self.__username + " " + self.__password + "\n")
        # wait for the answer
        data = self.__s.recv(self.__bufsize)
        # check the answer for errors
        if self.__reSearch("^250 OK"+TELNET_LINE_ENDING+"$", data) == None :
            raise NameError("Error while connecting: Login failed; response from NET-IO 230A is:  " + data)

    def __reSearch(self, regexp, data):
        return re.search(regexp.encode("ascii"), data)

    def getPowerSocketList(self):
        """Sends request to the NETIO 230A to ask for the power socket status.
        
        Returns string (4 chars long) specifying which power sockets are switched on/off.
        Each char is representing the power status of one power socket: 0/1
        For example: "1001" (power socket 1 and power socket 4 are on, all others off)"""
        return self.__sendRequest("port list")
    
    def getPowerSocketSetup(self,power_socket):
        """Sends request to the NETIO 230A to ask for the setup of the power socket given as parameter.
        returns the "port setup" string as specifyed by Koukaam"""
        return self.__sendRequest("port setup " + str(power_socket+1))
    
    def setPowerSocketPower(self,power_socket,switchOn=False):
        """setPowerSocketPower(power_socket,switchOn=False): method to set the power status of the power socket specified by the argument power socket to the bool argument switchOn
        returns nothing"""
        # the type conversion of switchOn ensures that the values are either "0" or "1":
        self.__sendRequest("port " + str(power_socket) + " " + str(int(bool(int(switchOn)))) )
    
    def setPowerSocketTempInterrupt(self,power_socket):
        self.__sendRequest("port " + str(int(power_socket)) + " int" )
    
    def setPowerSocketManualMode(self,power_socket,manualMode=True):
        self.__sendRequest("port " + str(int(power_socket)) + " manual")
    
    def getFirmwareVersion(self):
        return self.__sendRequest("version")
    
    def getDeviceAlias(self):
        return self.__sendRequest("alias")
    def setDeviceAlias(self,alias = "netio230a"):
        self.__sendRequest("alias " + alias)
    
    # this command is operation-safe: it does not switch the power sockets on/off during reboot of the NETIO 230A
    def reboot(self):
        response = self.__sendRequest("reboot",False)
        if re.search("^120 Rebooting", response) != None:
            time.sleep(.05) # no reboot if disconnecting too soon
    
    def getWatchdogSettings(self,power_socket):
        return self.__sendRequest("port wd " + str(power_socket))
    
    def getNetworkSettings(self):
        return self.__sendRequest("system eth")
    def setNetworkSettings(self,dhcpMode=False,deviceIP="192.168.1.2",subnetMask="255.255.255.0",gatewayIP="192.168.1.1"):
        if dhcpMode:
            self.__sendRequest("system eth dhcp")
        else:
            self.__sendRequest("system eth manual " + deviceIP + " " + subnetMask + " " + gatewayIP)
    
    def getDnsServer(self):
        return self.__sendRequest("system dns")
    def setDnsServer(self,dnsServer="192.168.1.1"):
        self.__sendRequest("system dns " + dnsServer)
    
    def getSystemDiscoverableUsingTool(self):
        if self.__sendRequest("system discover") == "enable":
            return True
        else:
            return False
    def setSystemDiscoverableUsingTool(self,setDiscoverable=True):
        if setDiscoverable:
            command = "enable"
        else:
            command = "disable"
        self.__sendRequest("system discover " + command)
    
    def setSwitchDelay(self,seconds):
        return self.__sendRequest("system swdelay " + str(int(math.ceil(seconds*10.0))))
    def getSwitchDelay(self):
        return int(self.__sendRequest("system swdelay"))/10.0
    
    def getSntpSettings(self):
        return self.__sendRequest("system sntp")
    def setSntpSettings(self,enable=True,sntpServer="time.nist.gov"):
        if enable:
            command = "enable"
        else:
            command = "disable"
        self.__sendRequest("system sntp " + " " + sntpServer)
    
    def setSystemTime(self,dt):
        self.__sendRequest("system time " + dt.strftime("%Y/%m/%d,%H:%M:%S") )
    def getSystemTime(self):
        """getSystemTime() returns a datetime object"""
        formatedTimestring = self.__sendRequest("system time")
        date = formatedTimestring.partition(",")[0].split("/")
        time = formatedTimestring.partition(",")[2].split(":")
        return datetime(int(date[0]), int(date[1]), int(date[2]), int(time[0]), int(time[1]), int(time[2]))
    
    def getSystemTimezone(self):
        """getSystemTimezone() returns the timezone offset from UTC in hours of the NETIO-230A."""
        return float(int(self.__sendRequest("system timezone")))/3600.0
    def setSystemTimezone(self,hoursOffset):
        """setSystemTimezone(hoursOffset) sets the timezone offset from UTC in hours of the NETIO-230A."""
        self.__sendRequest("system timezone " + str(math.ceil(hoursOffset*3600.0)))
    
    def setPowerSocket(self,number,power_socket):
        self.__power_sockets[number] = power_socket
    
    def getPowerSocket(self,number):
        self.updatePowerSocketsStatus()
        return self.__power_sockets[number]
    
    def getAllPowerSockets(self):
        self.updatePowerSocketsStatus()
        return self.__power_sockets
    
    def updatePowerSocketsStatus(self):
        power_sockets = []
        powerOnStatus = self.getPowerSocketList()
        for i in range(4):
            status_splitter = shlex.shlex(self.getPowerSocketSetup(i).encode('ascii'), posix=True)
            status_splitter.whitespace_split = True
            power_sockets.append( list(status_splitter) )
            self.__power_sockets[i].setName(power_sockets[i][0])
            self.__power_sockets[i].setPowerOnAfterPowerLoss(bool(int(power_sockets[i][3])))
            self.__power_sockets[i].setPowerOn(bool(int(powerOnStatus[i])))
            self.__power_sockets[i].setManualMode(power_sockets[i][1]=="manual")
            self.__power_sockets[i].setInterruptDelay(int(power_sockets[i][2]))
            #still missing: setWatchdogOn
    
    # generic method to send requests to the NET-IO 230A and checking the response
    def __sendRequest(self,request,complainIfAnswerNot250=True):
        try:
            self.__s.send(request.encode("ascii")+b"\n")
        except:
            try:
                self.__create_socket_and_login()
                self.__s.send(request.encode("ascii")+b"\n")
            except StandardError,error:
                raise NameError("no connection possible or other exception: "+str(error))
        
        data = self.__s.recv(self.__bufsize)
        if self.__reSearch("^250 ", data) == None and complainIfAnswerNot250:
            raise NameError("Error while sending request: " + request + "\nresponse from NET-IO 230A is:  " + data)
        else:
            data=data.decode("ascii")
            return data.replace("250 ","").replace(TELNET_LINE_ENDING,"")
    
    def disconnect(self):
        # close the socket:
        self.__sendRequest("quit",False)
        self.__s.close()
    
    def __del__(self):
        self.disconnect()
    ###   end of class netio230a   ----------------



class PowerSocket(object):
    """ This is a class to represent the power sockets of the NETIO-230A. """

    def __init__(self):
        self.__name = ""
        self.__manualMode = True #  False  means  timer mode
        self.__powerOn = False
        self.__watchdogOn = False
        self.__interruptDelay = 2
    
    def setManualMode(self,manualMode=True):
        self.__manualMode = manualMode
    def getManualMode(self):
        return self.__manualMode
    
    def setPowerOnAfterPowerLoss(self,powerOn=False):
        self.__powerOnAfterPowerLoss = powerOn
    def getPowerOnAfterPowerLoss(self):
        return self.__powerOnAfterPowerLoss
    
    def setTimerMode(self,timerMode):
        self.__manualMode = not timerMode
    def getTimerMode(self):
        return not self.__manualMode
    
    def setPowerOn(self,powerOn = False):
        self.__powerOn = powerOn
    def getPowerOn(self):
        return self.__powerOn
    
    def setName(self,newName):
        self.__name = newName
    def getName(self):
        return self.__name
    
    def setInterruptDelay(self,interruptDelay):
        self.__interruptDelay = interruptDelay
    def getInterruptDelay(self):
        return self.__interruptDelay
    
    def setWatchdogOn(self,watchdogOn):
        self.__watchdogOn = watchdogOn
    def getWatchdogOn(self):
        return self.__watchdogOn



# ----------------------------------------------------------------
# logic and code to detect available NETIO-230A devices on the LAN

import socket
import threading
import array
import time
import sys

NETIO230A_UDP_DISCOVER_PORT = 4000
TIMEOUT=0.2 # should be enough. Usualy we get the answer in 4.6 ms
DEVICE_NAME_TERMINATION = "\x00\x30\x30\x38\x30"
# the request to ask for available NETIO-230A on the network (bytes sniffed using wireshark)
DISCOVER_REQUEST = "PCEdit\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x02\x00\x00\x00"
DISCOVER_REQUEST += "\x00\x00\x00\x00\x00\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"
DISCOVER_REQUEST += "\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00"


# thread to run the UDP server that listens to answering NETIOs on your network
class UDPintsockThread(threading.Thread):
    def __init__ (self,port,callback_for_found_devices):
        """ listens to answers from available NETIO-230A devices on the LAN and calls
            callback_for_found_devices([deviceName, ip, sm, gw, mac, answerTime])     """
        threading.Thread.__init__(self)
        self.__port = port
        self.__callback = callback_for_found_devices
        self.__startTime = time.time()
    def run(self):
        addr = ('', self.__port)
        # Create socket and bind to address
        UDPinsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        UDPinsock.bind(addr)
        # will listen for three seconds to your network
        UDPinsock.settimeout(TIMEOUT)
        while True:
            try:
                # Receive messages
                data, addr = UDPinsock.recvfrom(1024)
                # keep timestamp of arriving package
                answerTime=time.time()
            except:
                #print "server timeout"
                break
            # check if we found a NETIO-230A
            if data.find("IPCam") == 0 and len(data)== 61:
                # documentation of data is found on http://wiki.github.com/pklaus/netio230a/netdiscover-protocol
                deviceName = data[38:data.find(DEVICE_NAME_TERMINATION)]
                data = array.array('B', data)
                ip = []
                for n in range(0, 4):
                    ip.append(data[10+n])
                mac = [0,0,0,0,0,0]
                for n in range(0, 6):
                    mac[n] = data[14+n]
                sm = []
                for n in range(0, 4):
                    sm.append(data[20+n])
                gw = []
                for n in range(0, 4):
                    gw.append(data[27+n])
                device = [deviceName, ip, sm, gw, mac, (answerTime-self.__startTime)*1000]
                self.__callback(device)
        UDPinsock.close()


def discover_netio230a_devices(callback_for_found_devices):
    dest = ('<broadcast>',NETIO230A_UDP_DISCOVER_PORT)
    #dest = ('255.255.255.255',NETIO230A_UDP_DISCOVER_PORT)
    myUDPintsockThread = UDPintsockThread(NETIO230A_UDP_DISCOVER_PORT,callback_for_found_devices)
    myUDPintsockThread.start()
    
    # send on all interfaces of the computer:
    # cf. last lines of the comment <http://serverfault.com/questions/72112/how-to-fix-the-global-broadcast-address-255-255-255-255-behavior-on-windows/72152#72152>
    for interface in all_interfaces():
        UDPoutsock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        # to allow broadcast communication:
        UDPoutsock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        host = socket.inet_ntoa(interface[1])
        UDPoutsock.bind((host, 0))
        # send UDP broadcast:
        UDPoutsock.sendto(DISCOVER_REQUEST, dest)
    myUDPintsockThread.join()

## http://code.activestate.com/recipes/439093/#c1
# import socket
import fcntl
import struct
import array
def all_interfaces():
    max_possible = 128  # arbitrary. raise if needed.
    bytes = max_possible * 32
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    names = array.array('B', '\0' * bytes)
    outbytes = struct.unpack('iL', fcntl.ioctl(
        s.fileno(),
        0x8912,  # SIOCGIFCONF
        struct.pack('iL', bytes, names.buffer_info()[0])
    ))[0]
    namestr = names.tostring()
    lst = []
    for i in range(0, outbytes, 40):
        name = namestr[i:i+16].split('\0', 1)[0]
        ip   = namestr[i+20:i+24]
        lst.append((name, ip))
    return lst

all_devices=[]
def device_detected_callback(device):
    global all_devices
    all_devices.append(device)
# if any software module wants to get all found devices with one call (blocking) then this function can be used:
def get_all_detected_devices():
    global all_devices
    all_devices = []
    discover_netio230a_devices(device_detected_callback)
    return all_devices
