import socket
import sys
import threading
import time
import os
import random
import pickle

class packet:
    MAX_DATA_LENGTH = 3
    
    def __init__(self, type, seqNum, data):
        # type = 0: ack, 1: packet 2: EOT
        if len(data) > self.MAX_DATA_LENGTH:
            raise Exception(f"Data too large (max {self.MAX_DATA_LENGTH} char): ", len(data))
        self.type = type
        self.seqNum = seqNum
        self.data = data
        # print(seqNum)

    # def getUdpData(self):
    #     array = bytearray()
    #     array.extend(self.type.to_bytes(length=4, byteorder="big"))
    #     array.extend(self.seqNum.to_bytes(length=4, byteorder="big"))
    #     array.extend(len(self.data).to_bytes(length=4, byteorder="big"))
    #     array.extend(self.data.encode())
    #     return array
    
    # @staticmethod
    # def parseUdpData(UdpData):
    #     type = int.from_bytes(UdpData[0:4], byteorder="big")
    #     seqNum = int.from_bytes(UdpData[4:8], byteorder="big")
    #     length = int.from_bytes(UdpData[8:12], byteorder="big")
    #     if type == 1:
    #         data = UdpData[12:12+length].decode()
    #         return packet(type, seqNum, data)
    #     else:
    #         return packet(type, seqNum, "")
        
class node():

    def __init__(self, selfPort, peerPort, windowSize, emulationMethod, value):
        self.msg = ""
        self.selfPort = selfPort
        self.peerPort = peerPort
        self.windowSize = windowSize
        self.emulationMethod = emulationMethod
        self.value = value
        self.SEQ_NUM_MODULO = 1001
        self.packetSent = 0
        self.packetLoss = 0
        self.ackLoss = 0
        self.packetReceived = 0
        self.ackReceived = 0
        self.pktResend = 0
        self.next_seq = 0
        self.exp_seq = 0
        self.base = 0
        self.pktArray = [None]*self.SEQ_NUM_MODULO
        self.received_all_acks = False
        self.finishedReading = False
        self.readPos = 0
        self.timer = False
        self.listeningSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listeningSock.bind(('', self.selfPort)) # listen acks
        self.dataSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # send data
        # self.dataSock.bind(('', self.selfPort))

    def reset(self):
        self.msg = ""
        self.packetSent = 0
        self.packetLoss = 0
        self.ackLoss = 0
        self.packetReceived = 0
        self.ackReceived = 0
        self.pktResend = 0
        self.next_seq = 0
        self.exp_seq = 0
        self.base = 0
        self.pktArray = [None]*self.SEQ_NUM_MODULO
        self.received_all_acks = False
        self.finishedReading = False
        self.readPos = 0
        self.timer = False

    def start(self):
        listen = threading.Thread(target=self.listening, args=())
        listen.start()
        time.sleep(0.01)
        self.parseCommand()

    def parseCommand(self):
        while True:
            try:
                inputList = []
                try:
                    tmp = input("node> ")
                    inputList = tmp.split()
                except KeyboardInterrupt:
                    os._exit(1)
                if len(inputList) == 0:
                    continue
                header = inputList[0]
                if header == 'send':
                    if len(inputList) >= 2:
                        self.msg = inputList[1]
                        self.startSending()
                    else:
                        print("node> Please provide a message to send.")
                else:
                    print("node> Invalid input!")
                    continue
            except Exception as e:  # Catch the exception and print its message
                print("node> [Error!] Exception:", str(e))

    
    def startSending(self):
        while True:
            # self.lock.acquire()
            if self.received_all_acks: 
                # print("sum 1")
                print(f"[summary] {self.ackLoss}/{self.packetSent} packets discarded, loss rate = {(self.ackLoss*1.0)/(self.packetSent*1.0)}")
                self.received_all_acks = False
                self.finishedReading = False
                self.readPos = 0
                self.reset()
                return
            
            if self.finishedReading == False and self.isInWindow():
                self.pktHandler()
                if self.timer == False:
                    self.timer = self.curTime()
                self.next_seq = (self.next_seq + 1) % self.SEQ_NUM_MODULO

            if self.timer and self.timeOut():
                t = time.time()
                print(f"[{t}] packet{self.base} timeout")
                self.timer = self.curTime()
                tmp = self.resendPkt()
                # if tmp == 1:
                #     return
            # self.lock.release()

    def isInWindow(self):
        maximum_num = (self.base + self.windowSize - 1) % self.SEQ_NUM_MODULO
        if self.base > self.SEQ_NUM_MODULO - self.windowSize:
            return (self.next_seq >= self.base) or (self.next_seq <= maximum_num)
        else:
            return (self.next_seq >= self.base) and (self.next_seq <= maximum_num)

    def pktHandler(self):
        if self.readPos >= len(self.msg):
            data = ""
        else:
            data = self.msg[self.readPos]
            self.readPos+=1
        if data == "":
            self.pktArray[self.next_seq] = "EOT"
            self.finishedReading = True
        else:
            self.pktArray[self.next_seq] = packet(1, self.next_seq, data)
            self.sendPkt(self.next_seq)

    def sendPkt(self, seq):
        if self.pktArray[seq] != "EOT":
            # self.logSeq()
            self.packetSent += 1
            self.dataSock.sendto(pickle.dumps(self.pktArray[seq]), ('localhost', self.peerPort))
            t = time.time()
            print(f"[{t}] packet{seq} {self.pktArray[seq].data} sent")
        # else:
        #     pkt = packet(1, -1, "EOT")
        #     self.dataSock.sendto(pickle.dumps(pkt), ('localhost', self.peerPort))

    def resendPkt(self):
        tmp = 0
        self.pktResend += 1
        if self.pktResend == len(self.msg):
            # print("sum 2")
            print(f"[summary] {len(self.msg)}/{len(self.msg)} packets lost, loss rate = 1")
            self.received_all_acks = False
            self.finishedReading = False
            self.readPos = 0
            self.reset()
            tmp = 1
        if self.base > self.next_seq:
            for seq_num in range(self.base, self.SEQ_NUM_MODULO):
                self.sendPkt(seq_num)
            for seq_num in range(0, self.next_seq):
                self.sendPkt(seq_num)
        else:
            for seq_num in range(self.base, self.next_seq):
                self.sendPkt(seq_num)
        return tmp

    def curTime(self):
        return int(round(time.time()*1000))
    
    def timeOut(self):
        return self.curTime() - self.timer >= 500

    def listening(self):
        while True:
            udpArray, senderAddr = self.listeningSock.recvfrom(4096)
            pkt = pickle.loads(udpArray)
            pktType, seqNum, data = pkt.type, pkt.seqNum, pkt.data
            # self.lock
            # print(senderAddr[1])
            if pktType == 2: # EOT
                print("in eot")
                # if senderAddr[1] == self.peerPort:
                eot = packet(2, self.exp_seq, 'receiver')
                self.dataSock.sendto(pickle.dumps(eot), ('localhost', self.peerPort))
                continue
            
            if pktType == 0: # ACK
                self.ackReceived += 1
                if self.discard(self.ackReceived-1):
                    t = time.time()
                    print(f"[{t}] ACK{seqNum} discarded")
                    continue
                if seqNum >= self.base:
                    t = time.time()
                    self.base = (seqNum + 1) % self.SEQ_NUM_MODULO
                    print(f"[{t}] ACK{seqNum} received, window moves to {self.base}")

                    if self.pktArray[self.base] == "EOT": # sym as the end of the msg. finished sending the msg
                        self.received_all_acks = True
                        p = packet(1, self.base, "EOT")
                        self.dataSock.sendto(pickle.dumps(p), ('localhost', self.peerPort))
                        continue

                    else:
                        if self.base == self.next_seq:
                            self.timer = False
                        else:
                            self.timer = self.curTime()
                else:
                    t = time.time()
                    print(f"[{t}] ACK{seqNum} received, window moves to {self.base}")

            if pktType == 1: # data (act as a receiver)
                # log
                if data == 'EOT':
                    # print("sum 3")
                    rate = (self.packetLoss*1.0)/(self.packetReceived*1.0)
                    print(f"[summary] {self.packetLoss}/{self.packetReceived} packets droped, loss rate = {rate}")
                    self.reset()
                    continue
                self.packetReceived += 1
                t = time.time()
                print(f"[{t}] packet{seqNum} {data} received")
                if self.discard(self.packetReceived-1):
                    t = time.time()
                    print(f"[{t}] packet{seqNum} {data} discarded")
                    continue
                if self.exp_seq == seqNum:
                    ack = packet(0, seqNum, '')
                    self.dataSock.sendto(pickle.dumps(ack), ('localhost', self.peerPort))
                    self.exp_seq = (self.exp_seq + 1) % self.SEQ_NUM_MODULO
                    t = time.time()
                    print(f"[{t}] ACK{seqNum} sent, expecting packet{self.exp_seq}")

                else:
                    ack = packet(0, self.exp_seq - 1, '')
                    self.dataSock.sendto(pickle.dumps(ack), ('localhost', self.peerPort))
                    t = time.time()
                    print(f"[{t}] ACK{self.exp_seq - 1} sent, expecting packet{self.exp_seq}")
    def discard(self, seq):
        if self.emulationMethod == '-d':
            # print(seq)
            if (seq+1)%self.value == 0:
                self.packetLoss += 1
                self.ackLoss += 1
                return True
            else:
                return False
        else:
            if random.random() < self.value:
                self.packetLoss += 1
                self.ackLoss += 1
                return True
            else:
                return False

if __name__ == "__main__":
    selfPort = int(sys.argv[1])
    peerPort = int(sys.argv[2])
    windowSize = int(sys.argv[3])
    method = sys.argv[4]
    value = float(sys.argv[5])
    if selfPort < 1024 or selfPort > 65535:
        print(">>> [Invalid server-port. Ensure the server-port is between 1024 and 65535.]]")
        os._exit(1)
    if peerPort < 1024 or peerPort > 65535:
        print(">>> [Invalid client-port. Ensure the client-port is between 1024 and 65535.]]")
        os._exit(1)
    newNode = node(selfPort, peerPort, windowSize, method, value)
    newNode.start()
