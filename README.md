# PA 2

Name: Wenbo Liu

UNI: wl2927

## Task 1. GBN protocal

### Packet structure

My `packet` structure shown like this:

``````python
class packet:
  	MAX_DATA_LENGTH = 1
    def __init__(self, type, seqNum, data):
        # type = 0: ack, 1: packet 2: EOT
        if len(data) > self.MAX_DATA_LENGTH:
            raise Exception(f"Data too large (max {self.MAX_DATA_LENGTH} char): ", len(data))
        self.type = type
        self.seqNum = seqNum
        self.data = data
``````

The `type` stands for the type of a packet (0: ACK, 1: data packet, 2: EOT. EOT means the end of the text to be sent). 

Because the node will only send one character in each packet, I set the `MAX_DATA_LENGTH` to 1.

When the node receives a packet from its peer, it will analyze the type of the packet firstly and then make a further analization.

When the node finishes sending all the messages, it will send an EOT packet (type = 2) to the receiver and for both sender node and receiver node will calculate the loss rate.

### Discard methods

```python
def discard(self, seq):
        if self.emulationMethod == '-d':
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
```

There are two discarding method - deterministic and probabilistic. If the packet need to be discarded, the function `discard` will return True. The number of losing packets or ACKs will also add one when discarding a packet or an ACK.

### Other details

For the input commands, I will check whether the port numbers are valid. 

In order to make the node become able to send messages for many times, I will init the node when a message has been send and the loss rate has been calculated. 

The parameter `self.pktArray` works as a packet buffer. 

More details can be found in section "How to run the code" and "Test".

## Task 2. DV protocal

### Structure of the routing table

The defination of my routing table is shown below:

```python
self.neighbors = neighbors  # Neighbors with their respective distances
self.neighbors[local_port] = 0
self.routing_table = {port: (self.neighbors[port], None) for port in neighbors}  # Format: {node: (distance, next_hop)}
self.routing_table[self.local_port] = (0, self.local_port)  # Distance to itself is 0
```

`self.neighbors` stores the information of its neighbors. `self.routing_table` works as a routing table. The initial routing table only contains the neighbor nodes. The format of my routing table is shown in the comment of my code.

### Send updates

```python
def send_updates(self):
        with self.lock:
            data = json.dumps(self.routing_table)
        for neighbor_port in self.neighbors.keys():
            if neighbor_port != self.local_port:
                t = time.time()
                print(f"[{t}] Message sent from Node {self.local_port} to Node {neighbor_port}")
                self.socket.sendto(data.encode('utf-8'), ('localhost', neighbor_port))
```

Function `send_updates` will send the routing table to all of the neighbor nodes and print the sending message.

### Process received data

```python
def process_received_data(self, message, neighbor_port):
        with self.lock:
            neighbor_routing_table = json.loads(message.decode('utf-8'))
            updated = False
            for port, (cost, _) in neighbor_routing_table.items():
                port = int(port)
                if port not in self.routing_table:
                    self.routing_table[port] = (cost + self.neighbors[neighbor_port], neighbor_port)
                    updated = True
                else:
                    if self.routing_table[port][0] > cost + self.routing_table[neighbor_port][0]:
                        self.routing_table[port] = (cost + self.routing_table[neighbor_port][0], neighbor_port)
                        updated = True
        if updated:
            self.send_updates()
        self.displayRoutingTable()
```

Function `process_received_data` will use Bellman-Ford algorithm to update routing tables. If there is a change in the routing table, the node will send its latest routing table to all its neighbor nodes. When receive a message, the node will also display its latest routing table. 

The function `displayRoutingTable` is shown below:

```python
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
```

### When to start

If the node is not the last node, it will only start its listening thread and does not do more things. If the node is the last node, it will send its neighbors its routing table. When other nodes receive a message from any of its neighbors, it will start to send packets to other nodes. In another words, the first received update message works as a signal to inform the node to start working. The code is shown below:

```python
def start(self):
        threading.Thread(target=self.receive_updates, daemon=True).start()
        if self.isLast == 1:
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
```

### When to end (converge)

Because the costs of each edges are static, each node send its routing table to its neighbors twice will make sure the routing table will converge. I define an event for each node. When the node start, the program will wait for the event. When the routing table converges, the event will set to happened and end the program. Mode details can be found in my code.

## Task 3. Merge both protocal

### Data structure

```python
class packet:
    def __init__(self, type, seqNum, data, portNum):
        self.type = type
        self.seqNum = seqNum
        self.data = data
        self.portNum = portNum
```

Compared with the `packet` in task 1, the `packet` in task 3 has several differences. For task 3, the packed will not only contain the message data, but also contain more information, like the routing table. Therefore, I do not define the `MAX_DATA_LENGTH`. Also, if a node need to send probes to multy nodes and a node may receive probes from several nodes, I will start a now sending thread for each probe. Therefore, the `packet` need contain the port of the sender node. For the same reason, I change the type of following parameters to `dict`:

```python
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
```

### sendProbe

```python
def sendProbe(self):
    threads = []
    for receiverPort in self.sendList:
        Sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        thread = threading.Thread(target=self.startSending, args = (Sock, receiverPort))
        threads.append(thread)
        thread.start()
```

The node will start a new sending thread for each of its receivers.

### When to start

It is similar to task 2. The last node will send a signal to all its neighbors. When the neighbors receive the signal, they will also send signals to their neighbors. If the node is active when receives a signal, it will ignore the signal. The whole process is very similar to broadcast. Once the node become actively, it will start sending probes to the nodes in its receiver list. To implement this method, I also define an even `self.is_start` like task 2. When a node reveives a signal, it will run the following code:

```python
if pktType == 5: # start signal
		if self.is_start.is_set():
				pass
		else:
				self.is_start.set()
				self.sendSignal()
```

### How to update the routing tables

Once the probe has been received by the receiver, the receiver will calculate the loss rate as the cost of the edge between the sender and the receiver. The receiver will store the sender port, the number of received packets and lost packets to its `statusTable`. Then the receiver will also send the status information and its routing table to the sender in order to let the sender update the cost of the edge, its routing table and display the information of this probe sending process. When the sender's routing table changes, it will also inform the receiver to update its routing table. Therefore, both of the sender's and receiver's  routing tables can be updated.

### Other details

The node will send probes every 20 seconds and the consol will display the routing table every 20 seconds.

The whole network is dynamic and the nodes will update their routing table dynamically. Therefore, the program will not stop automately. Users can use `ctrl+C` to stop running.

## How to run the code

### Task 1 (gbnnode.py)

Firstly, open 2 terminals for running sending and receiving node. The format of the commands are shown below:

```shell
python gbnnode.py <self_port> <peer_port> <window_size> [-d <value_of_n> | -p <value_of_p>]
```

For example:

```shell
python gbnnode.py 1111 2222 3 -p 0.3
python gbnnode.py 2222 1111 3 -p 0.3
```

The ports of the two nodes are 1111 and 2222. The discarding method is probabilistic. The probability is 0.3.

### Task 2 (dynode.py)

Firstly, open `n` terminals for running `n` nodes. In each terminals, run the following command:

```shell
python dvnode.py <self_port> <neighbor1_port> <loss_rate_1> <neighbor2_port> <loss_rate_2> ... [last]
```

For example, the following commands start four nodes in four terminals:

```shell
python dvnode.py 1111 2222 0.1 3333 0.5
python dvnode.py 2222 1111 0.1 3333 0.2 4444 0.8
python dvnode.py 3333 1111 0.5 2222 0.2 4444 0.5
python dvnode.py 4444 2222 0.8 3333 0.5 last
```

Please ensure that the cost of the same edge is of the same. Otherwise, the program will act as running in a directed graph.

### Task 3 (cnnode.py)

Firstly, open `n` terminals for running `n` nodes. In each terminals, run the following command:

```shell
python cnnode.py <local_port> receive <neighbor1_port> <loss_rate_1> <neighbor2_port> <loss_rate_2> ... <neighborM_port> <loss_rate_M> send <neighbor(M+1)_port> <neighbor(M+2)_port> ... <neighborN_port> [last]
```

For example, run 4 nodes in 4 terminals:

```shell
python cnnode.py 1111 receive send 2222 3333
python cnnode.py 2222 receive 1111 0.1 send 3333 4444
python cnnode.py 3333 receive 1111 0.5 2222 0.2 send 4444
python cnnode.py 4444 receive 2222 0.8 3333 0.5 send last
```



## Test

### gbnnode

#### Case 1:

```shell
python gbnnode.py 1111 2222 3 -p 0.3
python gbnnode.py 2222 1111 3 -p 0.3
```

```
Sender:
[1701900704.856885] packet0 a sent
[1701900704.8579452] packet1 b sent
[1701900704.8583848] packet2 c sent
[1701900704.867042] ACK0 discarded
[1701900705.356501] packet0 timeout
[1701900705.357165] packet0 a sent
[1701900705.357413] packet1 b sent
[1701900705.3576581] packet2 c sent
[1701900705.364015] ACK0 received, window moves to 1
[1701900705.364046] ACK1 received, window moves to 2
[1701900705.364058] ACK2 received, window moves to 3
[1701900705.3643022] packet3 d sent
[1701900705.364544] packet4 e sent
[1701900705.364585] ACK3 discarded
[1701900705.3646889] packet5 f sent
[1701900705.371116] ACK4 discarded
[1701900705.8635] packet3 timeout
[1701900705.8640058] packet3 d sent
[1701900705.8642151] packet4 e sent
[1701900705.8644228] packet5 f sent
[1701900705.870765] ACK4 received, window moves to 5
[1701900705.870801] ACK4 received, window moves to 5
[1701900705.870956] packet6 g sent
[1701900706.370502] packet5 timeout
[1701900706.370991] packet5 f sent
[1701900706.37119] packet6 g sent
[1701900706.376884] ACK5 discarded
[1701900706.389473] ACK6 received, window moves to 7
[summary] 4/15 packets discarded, loss rate = 0.26666666666666666
Receiver:
[1701900704.857871] packet0 a received
[1701900704.860594] ACK0 sent, expecting packet1
[1701900704.860683] packet1 b received
[1701900704.860697] packet1 b discarded
[1701900704.860717] packet2 c received
[1701900704.860723] packet2 c discarded
[1701900705.357297] packet0 a received
[1701900705.357682] ACK0 sent, expecting packet1
[1701900705.357708] packet1 b received
[1701900705.35792] ACK1 sent, expecting packet2
[1701900705.3579361] packet2 c received
[1701900705.358121] ACK2 sent, expecting packet3
[1701900705.364367] packet3 d received
[1701900705.364547] ACK3 sent, expecting packet4
[1701900705.36465] packet4 e received
[1701900705.364803] ACK4 sent, expecting packet5
[1701900705.364823] packet5 f received
[1701900705.364827] packet5 f discarded
[1701900705.864109] packet3 d received
[1701900705.864435] ACK4 sent, expecting packet5
[1701900705.864459] packet4 e received
[1701900705.864641] ACK4 sent, expecting packet5
[1701900705.864661] packet5 f received
[1701900705.864664] packet5 f discarded
[1701900705.871008] packet6 g received
[1701900705.8710132] packet6 g discarded
[1701900706.371103] packet5 f received
[1701900706.37136] ACK5 sent, expecting packet6
[1701900706.371378] packet6 g received
[1701900706.371531] ACK6 sent, expecting packet7
[summary] 5/15 packets droped, loss rate = 0.3333333333333333
```

For more testing cases, refer to `test.txt`

### dvnode

#### Case 1:

```shell
python dvnode.py 1111 2222 0.1 3333 0.5
python dvnode.py 2222 1111 0.1 3333 0.2 4444 0.8
python dvnode.py 3333 1111 0.5 2222 0.2 4444 0.5
python dvnode.py 4444 2222 0.8 3333 0.5 last
```

```
Node 1111:
[1701906039.850515] Message sent from Node 1111 to Node 2222
[1701906039.852739] Message sent from Node 1111 to Node 3333
[1701906039.853045] Node 1111 Routing Table
- (0.1) -> Node 2222
- (0.3) -> Node 3333; Next hop -> Node 2222
- (0.9) -> Node 4444; Next hop -> Node 2222
[1701906039.85315] Message sent from Node 1111 to Node 2222
[1701906039.8535] Message sent from Node 1111 to Node 3333
[1701906039.853764] Node 1111 Routing Table
- (0.1) -> Node 2222
- (0.3) -> Node 3333; Next hop -> Node 2222
- (0.8) -> Node 4444; Next hop -> Node 3333
[1701906039.853872] Message sent from Node 1111 to Node 2222
[1701906039.854094] Message sent from Node 1111 to Node 3333
[1701906039.854301] Node 1111 Routing Table
- (0.1) -> Node 2222
- (0.3) -> Node 3333; Next hop -> Node 2222
- (0.8) -> Node 4444; Next hop -> Node 2222
[1701906040.702322] Node 1111 Routing Table
- (0.1) -> Node 2222
- (0.3) -> Node 3333; Next hop -> Node 2222
- (0.8) -> Node 4444; Next hop -> Node 2222
[1701906043.8865018] Message sent from Node 1111 to Node 2222
[1701906043.887423] Message sent from Node 1111 to Node 3333
[1701906044.856168] Node 1111 Routing Table
- (0.1) -> Node 2222
- (0.3) -> Node 3333; Next hop -> Node 2222
- (0.8) -> Node 4444; Next hop -> Node 2222
[1701906045.707218] Node 1111 Routing Table
- (0.1) -> Node 2222
- (0.3) -> Node 3333; Next hop -> Node 2222
- (0.8) -> Node 4444; Next hop -> Node 2222
[1701906048.891198] Message sent from Node 1111 to Node 2222
[1701906048.8918989] Message sent from Node 1111 to Node 3333
[1701906053.896624] Node 1111 Routing Table
- (0.1) -> Node 2222
- (0.3) -> Node 3333; Next hop -> Node 2222
- (0.8) -> Node 4444; Next hop -> Node 2222

Node 2222:
[1701906036.538374] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.8) -> Node 4444
[1701906039.8465972] Message sent from Node 2222 to Node 1111
[1701906039.849762] Message sent from Node 2222 to Node 3333
[1701906039.850322] Message sent from Node 2222 to Node 4444
[1701906039.8515468] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.8) -> Node 4444
[1701906039.8528051] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.8) -> Node 4444
[1701906039.8531232] Message sent from Node 2222 to Node 1111
[1701906039.853503] Message sent from Node 2222 to Node 3333
[1701906039.85375] Message sent from Node 2222 to Node 4444
[1701906039.853911] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.7) -> Node 4444; Next hop -> Node 3333
[1701906039.853964] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.7) -> Node 4444; Next hop -> Node 3333
[1701906039.853997] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.7) -> Node 4444; Next hop -> Node 3333
[1701906039.854134] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.7) -> Node 4444; Next hop -> Node 3333
[1701906039.8542452] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.7) -> Node 4444; Next hop -> Node 3333
[1701906040.702501] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.7) -> Node 4444; Next hop -> Node 3333
[1701906041.540747] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.7) -> Node 4444; Next hop -> Node 3333
[1701906043.887757] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.7) -> Node 4444; Next hop -> Node 3333
[1701906044.855073] Message sent from Node 2222 to Node 1111
[1701906044.855874] Message sent from Node 2222 to Node 3333
[1701906044.856268] Message sent from Node 2222 to Node 4444
[1701906045.707453] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.7) -> Node 4444; Next hop -> Node 3333
[1701906046.5467362] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.7) -> Node 4444; Next hop -> Node 3333
[1701906048.892061] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.7) -> Node 4444; Next hop -> Node 3333
[1701906049.8617449] Node 2222 Routing Table
- (0.1) -> Node 1111
- (0.2) -> Node 3333
- (0.7) -> Node 4444; Next hop -> Node 3333

Node 3333:
[1701906036.538495] Node 3333 Routing Table
- (0.5) -> Node 1111
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906039.850532] Message sent from Node 3333 to Node 1111
[1701906039.852672] Message sent from Node 3333 to Node 2222
[1701906039.8529751] Message sent from Node 3333 to Node 4444
[1701906039.853166] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906039.853227] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906039.8532622] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906039.853834] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906039.8539] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906039.853945] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906039.854366] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906039.854413] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906040.70183] Message sent from Node 3333 to Node 1111
[1701906040.702214] Message sent from Node 3333 to Node 2222
[1701906040.702415] Message sent from Node 3333 to Node 4444
[1701906041.541056] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906043.888183] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906044.856555] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906045.706461] Message sent from Node 3333 to Node 1111
[1701906045.707068] Message sent from Node 3333 to Node 2222
[1701906045.7073421] Message sent from Node 3333 to Node 4444
[1701906046.546929] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906048.892329] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444
[1701906050.71185] Node 3333 Routing Table
- (0.3) -> Node 1111; Next hop -> Node 2222
- (0.2) -> Node 2222
- (0.5) -> Node 4444

Node 4444:
[1701906036.537143] Message sent from Node 4444 to Node 2222
[1701906036.5382469] Message sent from Node 4444 to Node 3333
[1701906039.850932] Message sent from Node 4444 to Node 2222
[1701906039.851454] Message sent from Node 4444 to Node 3333
[1701906039.851743] Node 4444 Routing Table
- (0.8) -> Node 2222
- (0.5) -> Node 3333
- (0.9) -> Node 1111; Next hop -> Node 2222
[1701906039.853285] Message sent from Node 4444 to Node 2222
[1701906039.853473] Message sent from Node 4444 to Node 3333
[1701906039.853745] Node 4444 Routing Table
- (0.7) -> Node 2222; Next hop -> Node 3333
- (0.5) -> Node 3333
- (0.8) -> Node 1111; Next hop -> Node 3333
[1701906039.854006] Message sent from Node 4444 to Node 2222
[1701906039.854207] Message sent from Node 4444 to Node 3333
[1701906039.854382] Node 4444 Routing Table
- (0.7) -> Node 2222; Next hop -> Node 3333
- (0.5) -> Node 3333
- (0.8) -> Node 1111; Next hop -> Node 2222
[1701906040.702677] Node 4444 Routing Table
- (0.7) -> Node 2222; Next hop -> Node 3333
- (0.5) -> Node 3333
- (0.8) -> Node 1111; Next hop -> Node 2222
[1701906041.5400488] Message sent from Node 4444 to Node 2222
[1701906041.540632] Message sent from Node 4444 to Node 3333
[1701906044.85684] Node 4444 Routing Table
- (0.7) -> Node 2222; Next hop -> Node 3333
- (0.5) -> Node 3333
- (0.8) -> Node 1111; Next hop -> Node 2222
[1701906045.70767] Node 4444 Routing Table
- (0.7) -> Node 2222; Next hop -> Node 3333
- (0.5) -> Node 3333
- (0.8) -> Node 1111; Next hop -> Node 2222
[1701906046.546062] Message sent from Node 4444 to Node 2222
[1701906046.546588] Message sent from Node 4444 to Node 3333
[1701906051.54936] Node 4444 Routing Table
- (0.7) -> Node 2222; Next hop -> Node 3333
- (0.5) -> Node 3333
- (0.8) -> Node 1111; Next hop -> Node 2222
```

For more testing cases, refer to `test.txt`

### cnnode

#### Case 1:

```shell
python dvnode.py 1111 receive send 2222 3333
python dvnode.py 2222 receive 1111 0.2 send 3333 4444
python dvnode.py 3333 receive 1111 0.1 2222 0.2 send 4444 5555
python dvnode.py 4444 receive 2222 0.3 3333 0.3 send 5555 6666
python dvnode.py 5555 receive 3333 0.1 4444 0.1 send 6666
python dvnode.py 6666 receive 4444 0.5 5555 0.2 send last
```

```
Node 1111:
[1701908519.9134989] Display Routing Table:
- (inf) -> Node 2222; Next hop -> Node None
- (inf) -> Node 3333; Next hop -> Node None
[1701908525.93796] Link to 2222: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908525.93796] Link to 3333: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908526.943342] Link to 2222: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908526.943342] Link to 3333: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908527.944522] Link to 2222: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908527.944522] Link to 3333: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908528.945291] Link to 2222: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908528.945291] Link to 3333: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908529.949232] Link to 2222: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908529.949232] Link to 3333: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908530.9535391] Link to 2222: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908530.9535391] Link to 3333: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908531.955212] Link to 2222: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908531.955212] Link to 3333: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908532.958853] Link to 2222: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908532.958853] Link to 3333: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908533.963465] Link to 2222: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908533.963465] Link to 3333: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908534.964213] Link to 2222: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908534.964213] Link to 3333: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908535.969244] Link to 2222: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908535.969244] Link to 3333: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908536.971361] Link to 2222: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908536.971361] Link to 3333: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908537.975338] Link to 2222: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908537.975338] Link to 3333: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908538.980546] Display Routing Table:
- (0.09) -> Node 2222; Next hop -> Node 2222
- (0.17) -> Node 3333; Next hop -> Node 2222
- (0.61) -> Node 4444; Next hop -> Node 2222

Node 2222:
[1701908519.9117398] Display Routing Table:
- (inf) -> Node 1111; Next hop -> Node None
- (inf) -> Node 3333; Next hop -> Node None
- (inf) -> Node 4444; Next hop -> Node None
[1701908525.9373372] Link to 1111: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908525.9373372] Link to 3333: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908526.94176] Link to 1111: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908526.94176] Link to 3333: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908527.944515] Link to 1111: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908527.944515] Link to 3333: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908528.947542] Link to 1111: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908528.947542] Link to 3333: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908529.951643] Link to 1111: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908529.951643] Link to 3333: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908529.951643] Link to 4444: 96 packets sent, 77 packets lost, loss rate 0.8020833333333334
[1701908530.953557] Link to 1111: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908530.953557] Link to 3333: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908530.953557] Link to 4444: 104 packets sent, 81 packets lost, loss rate 0.7788461538461539
[1701908531.956406] Link to 1111: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908531.956406] Link to 3333: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908531.956406] Link to 4444: 112 packets sent, 87 packets lost, loss rate 0.7767857142857143
[1701908532.961459] Link to 1111: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908532.961459] Link to 3333: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908532.961459] Link to 4444: 120 packets sent, 94 packets lost, loss rate 0.7833333333333333
[1701908533.966591] Link to 1111: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908533.966591] Link to 3333: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908533.966591] Link to 4444: 128 packets sent, 100 packets lost, loss rate 0.78125
[1701908534.9714959] Link to 1111: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908534.9714959] Link to 3333: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908534.9714959] Link to 4444: 136 packets sent, 107 packets lost, loss rate 0.7867647058823529
[1701908535.974926] Link to 1111: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908535.974926] Link to 3333: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908535.974926] Link to 4444: 144 packets sent, 114 packets lost, loss rate 0.7916666666666666
[1701908536.976937] Link to 1111: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908536.976937] Link to 3333: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908536.976937] Link to 4444: 152 packets sent, 120 packets lost, loss rate 0.7894736842105263
[1701908537.98092] Link to 1111: 11 packets sent, 1 packets lost, loss rate 0.09090909090909091
[1701908537.98092] Link to 3333: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908537.98092] Link to 4444: 160 packets sent, 125 packets lost, loss rate 0.78125
[1701908538.984855] Display Routing Table:
- (0.09) -> Node 1111; Next hop -> Node 1111
- (0.08) -> Node 3333; Next hop -> Node 3333
- (0.52) -> Node 4444; Next hop -> Node 3333

Node 3333:
[1701908519.9117389] Display Routing Table:
- (inf) -> Node 1111; Next hop -> Node None
- (inf) -> Node 2222; Next hop -> Node None
- (inf) -> Node 4444; Next hop -> Node None
[1701908525.938168] Link to 4444: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908525.938168] Link to 2222: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908525.938168] Link to 1111: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908526.943417] Link to 4444: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908526.943417] Link to 2222: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908526.943417] Link to 1111: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908527.945523] Link to 4444: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908527.945523] Link to 2222: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908527.945523] Link to 1111: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908528.949228] Link to 4444: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908528.949228] Link to 2222: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908528.949228] Link to 1111: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908529.954355] Link to 4444: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908529.954355] Link to 2222: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908529.954355] Link to 1111: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908530.958251] Link to 4444: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908530.958251] Link to 2222: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908530.958251] Link to 1111: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908531.96341] Link to 4444: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908531.96341] Link to 2222: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908531.96341] Link to 1111: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908532.9684658] Link to 4444: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908532.9684658] Link to 2222: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908532.9684658] Link to 1111: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908533.9736161] Link to 4444: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908533.9736161] Link to 2222: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908533.9736161] Link to 1111: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908534.977684] Link to 4444: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908534.977684] Link to 2222: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908534.977684] Link to 1111: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908535.980514] Link to 4444: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908535.980514] Link to 2222: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908535.980514] Link to 1111: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908536.9810822] Link to 4444: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908536.9810822] Link to 2222: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908536.9810822] Link to 1111: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908537.9828758] Link to 4444: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908537.9828758] Link to 2222: 12 packets sent, 1 packets lost, loss rate 0.08333333333333333
[1701908537.9828758] Link to 1111: 23 packets sent, 8 packets lost, loss rate 0.34782608695652173
[1701908538.98519] Display Routing Table:
- (0.17) -> Node 1111; Next hop -> Node 2222
- (0.08) -> Node 2222; Next hop -> Node 2222
- (0.43) -> Node 4444; Next hop -> Node 4444

Node 4444:
[1701908519.9134989] Display Routing Table:
- (inf) -> Node 2222; Next hop -> Node None
- (inf) -> Node 3333; Next hop -> Node None
[1701908525.937338] Link to 3333: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908526.940511] Link to 3333: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908527.944512] Link to 3333: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908528.946186] Link to 3333: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908529.9498198] Link to 3333: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908529.9498198] Link to 2222: 96 packets sent, 77 packets lost, loss rate 0.8020833333333334
[1701908530.951736] Link to 3333: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908530.951736] Link to 2222: 104 packets sent, 81 packets lost, loss rate 0.7788461538461539
[1701908531.955791] Link to 3333: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908531.955791] Link to 2222: 112 packets sent, 87 packets lost, loss rate 0.7767857142857143
[1701908532.958611] Link to 3333: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908532.958611] Link to 2222: 120 packets sent, 94 packets lost, loss rate 0.7833333333333333
[1701908533.961499] Link to 3333: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908533.961499] Link to 2222: 128 packets sent, 100 packets lost, loss rate 0.78125
[1701908534.9667048] Link to 3333: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908534.9667048] Link to 2222: 136 packets sent, 107 packets lost, loss rate 0.7867647058823529
[1701908535.969242] Link to 3333: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908535.969242] Link to 2222: 144 packets sent, 114 packets lost, loss rate 0.7916666666666666
[1701908536.971176] Link to 3333: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908536.971176] Link to 2222: 152 packets sent, 120 packets lost, loss rate 0.7894736842105263
[1701908537.975338] Link to 3333: 30 packets sent, 13 packets lost, loss rate 0.43333333333333335
[1701908537.975338] Link to 2222: 160 packets sent, 125 packets lost, loss rate 0.78125
[1701908538.980546] Display Routing Table:
- (0.52) -> Node 2222; Next hop -> Node 3333
- (0.43) -> Node 3333; Next hop -> Node 3333
- (0.61) -> Node 1111; Next hop -> Node 3333
```

Due to the costs of each edges are not stable, the routing table may have some differences compared with Task 2 in some cases.

For more testing cases, refer to `test.txt`.