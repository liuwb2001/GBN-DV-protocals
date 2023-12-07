import socket
import sys
import threading
import time
import os
import random
import pickle
import json

class packet:
    def __init__(self, type, seqNum, data, portNum):
        self.type = type
        self.seqNum = seqNum
        self.data = data
        self.portNum = portNum
        
class node():

    def __init__(self, selfPort, neighbors, sendList, receivers, isLast):
        self.msg = "abcdefghij"
        self.selfPort = selfPort
        # self.peerPort = peerPort
        self.neighbors = neighbors  # Neighbors with their respective distances
        self.neighbors[selfPort] = 0
        self.routing_table = {port: (1.1, None) for port in neighbors}  # Format: {node: (distance, next_hop)}
        self.routing_table[self.selfPort] = (0, self.selfPort)  # Distance to itself is 0
        self.sendList = sendList
        self.isLast = isLast
        self.receivers = receivers
        self.windowSize = 5
        self.emulationMethod = '-p'
        self.value = {port: self.neighbors[port] for port in neighbors}
        self.SEQ_NUM_MODULO = 1001
        self.packetLoss = {port: 0 for port in neighbors}
        self.packetReceived = {port: 0 for port in neighbors}

        self.next_seq = {port: 0 for port in neighbors}
        self.exp_seq = {port: 0 for port in neighbors}
        self.base = {port: 0 for port in neighbors}
        self.pktArray = {port: [None]*self.SEQ_NUM_MODULO for port in neighbors}
        self.received_all_acks = {port: False for port in neighbors}
        self.finishedReading = {port: False for port in neighbors}
        self.readPos = {port: 0 for port in neighbors}
        self.timer = {port: False for port in neighbors}

        self.listeningSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.listeningSock.bind(('', self.selfPort)) # listen acks
        self.dataSock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM) # send data
        self.lock = threading.Lock()
        self.statusTable = {} # port: (sent, loss)
        self.is_start = threading.Event()
        # self.is_end = threading.Event()

    def reset(self, port):
        self.packetLoss[port] = 0
        self.packetReceived[port] = 0

        self.next_seq[port] = 0
        self.exp_seq[port] = 0
        self.base[port] = 0
        self.pktArray[port] = [None]*self.SEQ_NUM_MODULO
        self.received_all_acks[port] = False
        self.finishedReading[port] = False
        self.readPos[port] = 0
        self.timer[port] = False

    def start(self):
        listen = threading.Thread(target=self.listening, args=())
        listen.start()
        if self.isLast:
            self.sendSignal()
        else:
            self.is_start.wait()
        i = 1
        m = 0
        while True:
            # if m == 3:
            #     self.is_end.set()
            i += 1
            if i%20 == 0:
                t = time.time()
                print(f"[{t}] Display Routing Table:")
                self.displayRoutingTable()
                i = 1
                m += 1
                self.sendProbe()
            # print("should display")
            self.displayStatus()
            time.sleep(1) # send probe every 10 seconds
    
    def startSending(self, Sock, receiverPort):
        # print(f"start send to {receiverPort}")
        while True:
            # self.lock.acquire()
            if self.received_all_acks[receiverPort]: 
                # print(f"[summary] {self.ackLoss}/{self.packetSent} packets discarded, loss rate = {(self.ackLoss*1.0)/(self.packetSent*1.0)}%")
                # self.received_all_acks = False
                # self.finishedReading = False
                # self.readPos = 0
                
                self.reset(receiverPort)
                return
            
            if self.finishedReading[receiverPort] == False and self.isInWindow(receiverPort):
                self.pktHandler(Sock, receiverPort)
                if self.timer[receiverPort] == False:
                    self.timer[receiverPort] = self.curTime()
                self.next_seq[receiverPort] = (self.next_seq[receiverPort] + 1) % self.SEQ_NUM_MODULO

            if self.timer[receiverPort] and self.timeOut(receiverPort):
                t = time.time()
                # if self.base[receiverPort] == len(self.msg):
                #     self.reset(receiverPort)
                #     return
                # print(f"[{t}] packet{self.base[receiverPort]} timeout")
                self.timer[receiverPort] = self.curTime()
                self.resendPkt(Sock, receiverPort)
            time.sleep(0.5)
            # self.lock.release()

    def isInWindow(self, receiverPort):
        maximum_num = (self.base[receiverPort] + self.windowSize - 1) % self.SEQ_NUM_MODULO
        if self.base[receiverPort] > self.SEQ_NUM_MODULO - self.windowSize:
            return (self.next_seq[receiverPort] >= self.base[receiverPort]) or (self.next_seq[receiverPort] <= maximum_num)
        else:
            return (self.next_seq[receiverPort] >= self.base[receiverPort]) and (self.next_seq[receiverPort] <= maximum_num)

    def pktHandler(self, Sock, receiverPort):
        if self.readPos[receiverPort] >= len(self.msg):
            data = ""
        else:
            data = self.msg[self.readPos[receiverPort]]
            self.readPos[receiverPort]+=1
        if data == "":
            self.pktArray[receiverPort][self.next_seq[receiverPort]] = "EOT"
            self.finishedReading[receiverPort] = True
        else:
            self.pktArray[receiverPort][self.next_seq[receiverPort]] = packet(1, self.next_seq[receiverPort], data, self.selfPort)
            self.sendPkt(self.next_seq[receiverPort], receiverPort, Sock)

    def sendPkt(self, seq, receiverPort, Sock):
        if self.pktArray[receiverPort][seq] != "EOT":
            # self.logSeq()
            Sock.sendto(pickle.dumps(self.pktArray[receiverPort][seq]), ('localhost', receiverPort))
            t = time.time()
            # print(f"[{t}] packet{seq} {self.pktArray[receiverPort][seq].data} sent")
        else:
            pkt = packet(1, -1, "EOT", self.selfPort)
            Sock.sendto(pickle.dumps(pkt), ('localhost', receiverPort))

    def resendPkt(self, Sock, receiverPort):
        if self.base[receiverPort] > self.next_seq[receiverPort]:
            for seq_num in range(self.base[receiverPort], self.SEQ_NUM_MODULO):
                self.sendPkt(seq_num, receiverPort, Sock)
            for seq_num in range(0, self.next_seq[receiverPort]):
                self.sendPkt(seq_num, receiverPort, Sock)
        else:
            for seq_num in range(self.base[receiverPort], self.next_seq[receiverPort]):
                self.sendPkt(seq_num, receiverPort, Sock)

    def curTime(self):
        return int(round(time.time()*1000))
    
    def timeOut(self, port):
        return self.curTime() - self.timer[port] >= 500

    def listening(self):
        while True:
            udpArray, senderAddr = self.listeningSock.recvfrom(4096)
            pkt = pickle.loads(udpArray)
            # print(type(pkt), senderAddr[1])
            pktType, seqNum, data = pkt.type, pkt.seqNum, pkt.data
            # self.lock
            senderPort = pkt.portNum
            # print(senderPort)
            if pktType == 2: # EOT
                # if senderAddr[1] == senderPort:
                eot = packet(2, self.exp_seq[senderPort], 'receiver', self.selfPort)
                # print("listen2", senderPort)
                self.dataSock.sendto(pickle.dumps(eot), ('localhost', senderPort))
                continue
            
            if pktType == 0: # ACK
                if seqNum >= self.base[senderPort]:
                    t = time.time()
                    self.base[senderPort] = (seqNum + 1) % self.SEQ_NUM_MODULO
                    # print(f"[{t}] {senderPort}: ACK{seqNum} received, window moves to {self.base[senderPort]}")

                    if self.pktArray[senderPort][self.base[senderPort]] == "EOT": # sym as the end of the msg. finished sending the msg
                        # print("ack stop eot", self.base[senderPort])
                        self.received_all_acks[senderPort] = True
                        # self.statusTable[senderPort] = (self.packetSent, self.pktResend)
                        # self.neighbors[senderPort] = (1.0*self.pktResend)/(1.0*self.packetSent)
                        # self.bellman_ford_update()
                        p = packet(1, self.base[senderPort], "EOT", self.selfPort)
                        # print("listen0", senderPort, type(p))
                        self.dataSock.sendto(pickle.dumps(p), ('localhost', senderPort))
                        continue

                    else:
                        if self.base[senderPort] == self.next_seq[senderPort]:
                            self.timer[senderPort] = False
                        else:
                            self.timer[senderPort] = self.curTime()
                else:
                    t = time.time()
                    # print(f"[{t}] {senderPort}: ACK{seqNum} received, window moves to {self.base[senderPort]}")

            if pktType == 1: # data (act as a receiver)
                # log
                if data == 'EOT':
                    # print(f"[summary] From {senderPort}: {self.packetLoss[senderPort]}/{self.packetReceived[senderPort]} packets droped, loss rate = {(self.packetLoss[senderPort]*1.0)/(self.packetReceived[senderPort]*1.0)}%")
                    self.statusTable[int(senderPort)] = (self.packetReceived[senderPort], self.packetLoss[senderPort])
                    # print(f"statustable send to {senderPort}")
                    self.sendStatusTable(senderPort, self.statusTable)
                    self.neighbors[senderPort] = (1.0*self.packetLoss[senderPort])/(1.0*self.packetReceived[senderPort])
                    if self.routing_table[senderPort] == 'inf':
                        self.routing_table[senderPort] = self.neighbors[senderPort]
                    # print('send change')
                    self.send_neighbor_change(senderPort, self.neighbors[senderPort])
                    self.exp_seq[senderPort] = 0
                    # self.routing_table[senderPort] = ((1.0*self.packetLoss)/(1.0*self.packetReceived), None)
                    # self.send_updates()
                    # self.bellman_ford_update()
                    # self.reset(senderPort)
                    continue
                self.packetReceived[senderPort] += 1
                t = time.time()
                # print(f"[{t}] {senderPort}: packet{seqNum} {data} received")
                if self.discard(self.packetReceived[senderPort]-1, senderPort):
                    t = time.time()
                    # print(f"[{t}] {senderPort}: packet{seqNum} {data} discarded")
                    continue
                if self.exp_seq[senderPort] == seqNum:
                    ack = packet(0, seqNum, "", self.selfPort)
                    # print("listen1", senderPort, type(ack))
                    self.dataSock.sendto(pickle.dumps(ack), ('localhost', senderPort))
                    self.exp_seq[senderPort] = (self.exp_seq[senderPort] + 1) % self.SEQ_NUM_MODULO
                    t = time.time()
                    # print(f"[{t}] {senderPort}: ACK{seqNum} sent, expecting packet{self.exp_seq[senderPort]}")

                else:
                    ack = packet(0, self.exp_seq[senderPort] - 1, '', self.selfPort)
                    # print("listen1_1", senderPort, type(ack))
                    self.dataSock.sendto(pickle.dumps(ack), ('localhost', senderPort))
                    t = time.time()
                    # print(f"[{t}] {senderPort} ACK{self.exp_seq[senderPort] - 1} sent, expecting packet{self.exp_seq[senderPort]}")
            if pktType == 3:
                message = json.loads(data)
                self.process_received_data(message, senderPort)
            if pktType == 4: # receive change of an edge from neighbor
                # print('receive change')
                message = json.loads(data)
                # print(message) # routing table of the neighbor
                cost = seqNum
                self.neighbors[senderPort] = cost
                self.process_received_data(message, senderPort)
            if pktType == 5: # start signal
                if self.is_start.is_set():
                    pass
                else:
                    self.is_start.set()
                    self.sendSignal()
            if pktType == 6:
                # print(f"receive statustable from {senderPort}")
                table = json.loads(data)
                # print(table, senderPort)
                self.statusTable[senderPort] = table[str(self.selfPort)]
                # print(self.statusTable)
    
    def process_received_data(self, message, neighbor_port):
        # print("in processing")
        # print(message, self.neighbors, self.routing_table)
        # with self.lock:
        # Deserialize the JSON data
        neighbor_routing_table = message
        updated = False
        for port, (cost, _) in neighbor_routing_table.items():
            port = int(port)
            if port not in self.routing_table:
                self.routing_table[port] = (cost + self.neighbors[neighbor_port], neighbor_port)
                updated = True
            else:
                if self.routing_table[port][0] > cost + self.neighbors[neighbor_port]:
                    self.routing_table[port] = (cost + self.neighbors[neighbor_port], neighbor_port)
                    updated = True
        # print(self.routing_table)
        if updated:
            self.send_updates()
        # self.send_updates()

    def discard(self, seq, senderPort):
        # print("in discard", self.neighbors[senderPort])
        if random.random() < self.value[senderPort]:
            self.packetLoss[senderPort] += 1
            return True
        else:
            return False
            
    def send_updates(self):
        # Serialize the routing table as JSON
        # print("send update")
        # with self.lock:
        data = json.dumps(self.routing_table)
        pkt = packet(3,-1, data, self.selfPort)
        for neighbor_port in self.neighbors.keys():
            if neighbor_port != self.selfPort:
                # print("send_updates", neighbor_port, type(pkt))
                self.dataSock.sendto(pickle.dumps(pkt), ('localhost', neighbor_port))
    
    # def sendProbe(self):
    #     for receiverPort in self.sendList:
    #         Sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    #         print(f"start send to {receiverPort}")
    #         self.startSending(Sock, receiverPort)
    def sendProbe(self):
        threads = []
        for receiverPort in self.sendList:
            Sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            thread = threading.Thread(target=self.startSending, args = (Sock, receiverPort))
            threads.append(thread)
            thread.start()

    def displayStatus(self):
        t = time.time()
        for port, (sent, loss) in self.statusTable.items():
            if port != self.selfPort:
                print(f"[{t}] Link to {port}: {sent} packets sent, {loss} packets lost, loss rate {(loss*1.0)/(sent*1.0)}")

    def send_neighbor_change(self, neighborPort, cost):
        data = json.dumps(self.routing_table)
        pkt = packet(4, cost, data, self.selfPort)
        # print("send_neighbor_change", neighborPort, type(pkt))
        self.dataSock.sendto(pickle.dumps(pkt), ('localhost', neighborPort))

    def sendSignal(self):
        pkt = packet(5,0,'', self.selfPort)
        for port in self.neighbors.keys():
            if port != self.selfPort:
                # print("sendSignal", port, type(pkt))
                self.dataSock.sendto(pickle.dumps(pkt), ('localhost', port))

    def sendStatusTable(self, senderPort, statustable):
        data = json.dumps(statustable)
        pkt = packet(6, 0, data, self.selfPort)
        # print("sendStatusTable", senderPort, type(pkt))
        self.dataSock.sendto(pickle.dumps(pkt), ('localhost', senderPort))

    def displayRoutingTable(self):
        for port in self.routing_table:
            hop = self.routing_table[port][1]
            if port != self.selfPort:
                if self.routing_table[port][0] < 1:
                    print(f"- ({round(self.routing_table[port][0], 2)}) -> Node {port}; Next hop -> Node {hop}")
                else:
                    print(f"- (inf) -> Node {port}; Next hop -> Node {hop}")


if __name__ == "__main__":
    selfPort = int(sys.argv[1])
    l  =len(sys.argv)
    isLast = 0
    isReceive = 0
    neighbors = {}
    receive = {}
    send = []
    i = 2
    while i < l:
        if sys.argv[i] == 'receive':
            isReceive = 1
            i += 1
            continue
        if sys.argv[i] == 'send':
            isReceive = 0
            i += 1
            continue
        if sys.argv[i] == 'last':
            isLast = 1
            break
        if isReceive:
            receive[int(sys.argv[i])] = float(sys.argv[i+1])
            neighbors[int(sys.argv[i])] = float(sys.argv[i+1])
            i += 2
        else:
            send.append(int(sys.argv[i]))
            neighbors[int(sys.argv[i])] = 1.0
            i += 1
    # print(neighbors, receive, send)
    newNode = node(selfPort, neighbors, send, receive, isLast)
    newNode.start()
        