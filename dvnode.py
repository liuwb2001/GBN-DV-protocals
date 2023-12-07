import socket
import threading
import json
import time
import sys
import os

class node:
    def __init__(self, local_port, neighbors, isLast):
        self.local_port = local_port
        self.neighbors = neighbors  # Neighbors with their respective distances
        self.neighbors[local_port] = 0
        self.routing_table = {port: (self.neighbors[port], None) for port in neighbors}  # Format: {node: (distance, next_hop)}
        self.routing_table[self.local_port] = (0, self.local_port)  # Distance to itself is 0
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind(('', self.local_port))
        self.isLast = isLast
        self.lock = threading.Lock()
        self.is_end = threading.Event()
        self.receivenum = 0
        self.is_start = False

    def start(self):
        # print(self.neighbors)
        threading.Thread(target=self.receive_updates, daemon=True).start()
        # self.bellman_ford_update()
        if self.isLast == 1:
            # print("sent")
            # self.bellman_ford_update()
            self.send_updates()
        i = 0
        while True:
            if self.is_start:
                i += 1
                self.send_updates()
            time.sleep(5)
            if i == 2:
                self.is_end.set()
                break

    def receive_updates(self):
        print("Start listening...")
        while True:
            message, senderAddr = self.socket.recvfrom(1024)
            self.is_start = True
            self.receivenum += 1
            neighbor_port = senderAddr[1]
            # print("neighborPort", neighbor_port)
            self.process_received_data(message, neighbor_port)

    def process_received_data(self, message, neighbor_port):
        # print(f"receive from {neighbor_port}")
        # Deserialize the JSON data
        neighbor_routing_table = json.loads(message.decode('utf-8'))
        updated = False
        # print(neighbor_routing_table)
        # print(self.routing_table)
        for port, (cost, _) in neighbor_routing_table.items():
            port = int(port)
            if port not in self.routing_table:
                # print(port, cost, self.neighbors[neighbor_port])
                self.routing_table[port] = (cost + self.neighbors[neighbor_port], neighbor_port)
                updated = True
            else:
                if self.routing_table[port][0] > cost + self.routing_table[neighbor_port][0]:
                    # print("&**************")
                    self.routing_table[port] = (cost + self.routing_table[neighbor_port][0], neighbor_port)
                    updated = True

        # If there was an update, perform a Bellman-Ford update
        if updated:
        #     print("isupdate")
            self.send_updates()
        #     # self.bellman_ford_update()
            # self.is_end.set()
        # else:
        # # self.send_updates()
        self.displayRoutingTable()
            

    def send_updates(self):
        # Serialize the routing table as JSON
        # with self.lock:
        data = json.dumps(self.routing_table)
        for neighbor_port in self.neighbors.keys():
            if neighbor_port != self.local_port:
                t = time.time()
                print(f"[{t}] Message sent from Node {self.local_port} to Node {neighbor_port}")
                self.socket.sendto(data.encode('utf-8'), ('localhost', neighbor_port))

    def displayRoutingTable(self):
        t = time.time()
        print(f"[{t}] Node {local_port} Routing Table")
        for port in self.routing_table:
            hop = self.routing_table[port][1]
            if port != local_port:
                if hop != None:
                    print(f"- ({round(self.routing_table[port][0], 2)}) -> Node {port}; Next hop -> Node {hop}")
                else:
                    print(f"- ({round(self.routing_table[port][0], 2)}) -> Node {port}")

if __name__ == "__main__":
    local_port = int(sys.argv[1])
    l = len(sys.argv)
    neighbors = {}
    isLast = 0
    for i in range(2, l):
        if i%2 == 0:
            if sys.argv[i] == 'last':
                isLast = 1
                break
            port  = int(sys.argv[i])
            if port < 1024 or port > 65535:
                print(">>> [Invalid server-port. Ensure the server-port is between 1024 and 65535.]")
                os._exit(1)
            rate = float(sys.argv[i+1])
            if rate < 0 or rate > 1:
                print(">>> [Invalid loss rate. Ensure the loss rate is between 0 and 1.]")
                os._exit(1)
            neighbors[port] = rate
            i += 1
    # print(neighbors)
    # num_neighbors = len(neighbors)
    newNode = node(local_port, neighbors, isLast)
    newNode.start()
    newNode.is_end.wait()
    newNode.displayRoutingTable()

        
