import sys
import getopt
import random
import time
import Checksum
import BasicSender

'''
This is a skeleton sender class. Create a fantastic transport protocol here.
'''
class Sender(BasicSender.BasicSender):
    def __init__(self, dest, port, filename, debug=False):
        super(Sender, self).__init__(dest, port, filename, debug)
        #100 bytes for seqno, checksum, msgtype
        self.PACKET_SIZE = 1372
        self.WINDOW_SIZE = 5
        self.TIMEOUT_LENGTH = 0.5
        self.dup_counter = 0
        self.window_buffer = []
        self.seqno = 0
        self.last = -1
        self.done = False
        self.done_ack = False


    def handle_response(self,response_packet,min_ack):
        if response_packet is None:
            return False

        split_packet = self.split_packet(response_packet)
        msg_type = split_packet[0]
        ack = split_packet[1]

        #check if corrupt (non-acks)
        if (type(ack) == type(str)):
            if not ack.isdigit():
                return False
        if msg_type != 'ack':
            return False

        #check if dupACK
        if int(ack) == min_ack:
            self.dup_counter += 1
        else:
            self.dup_counter = 0

        


        #check if checksum is valid
        if Checksum.validate_checksum(response_packet):
            pass
        else:
            #print "recv: %s <--- CHEKCSUM FAILED" % response_packet
            return False

        #check if within window range
        if not ack > min_ack and ack <= min_ack + self.WINDOW_SIZE:
            return False

        return True

    def fill_window(self, msg):
        seqno_to_send = self.seqno
        while len(self.window_buffer) < self.WINDOW_SIZE and not self.done:
            next_msg = self.infile.read(self.PACKET_SIZE)
            msg_type = 'data'
            #print "nextmsg: %s" % next_msg[0:10]
            if next_msg == "":
                msg_type = 'end'
                self.done = True
                self.last = seqno_to_send
            packet = self.make_packet(msg_type,seqno_to_send,msg)
            self.window_buffer.append(packet)
            #print "added packet to buffer, seqno: %s" % seqno_to_send
            #print "packet type is %s" % msg_type
            msg = next_msg
            seqno_to_send += 1
        



    # Main sending loop.
    def start(self):
        self.seqno = random.randint(5000,10000) #randomize starting seqno

        msg = self.infile.read(self.PACKET_SIZE)
        next = self.infile.read(self.PACKET_SIZE)
        if (self.start_connection(self.seqno, msg)):
            msg = next
        else: #failed to start connection
            return

        start_time = time.time()
        while not self.done_ack:
            self.fill_window(msg) #fills send window with data packets
            if len(self.window_buffer) == 0:
                break

            for packet in self.window_buffer:
                self.send(packet)
                #print "sent: %s" % packet
            while not self.done_ack: #loops until final ack is received
                response = self.receive(self.TIMEOUT_LENGTH)
                if not response: #packet timeout
                    current_time = time.time()
                    if time.time() > start_time + 10: #10 seconds without receiving a response
                        return
                    if self.WINDOW_SIZE > 1:
                        self.WINDOW_SIZE -=1
                    break
                start_time = time.time()

                if self.handle_response(response, self.seqno):
                    if self.WINDOW_SIZE < 5:
                        self.WINDOW_SIZE += 1
                    self.handle_new_ack(response)
                    buffer_start_size = len(self.window_buffer)
                    self.fill_window(msg)
                    buffer_filled_size = len(self.window_buffer)
                    for i in range(buffer_start_size, buffer_filled_size):
                        self.send(self.window_buffer[i])   
                
                if len(self.window_buffer) == 0: 
                    break #go back to out loop to fill send window again

                if self.dup_counter >= 3:
                    if self.WINDOW_SIZE > 1
                        self.WINDOW_SIZE -= 1
                    self.send(self.window_buffer[0])
        
        self.infile.close()



    def start_connection(self,startno,msg):
        start = self.make_packet('start',startno,msg)
        start_time = time.time()
        while True:
            self.send(start)
            response = self.receive(self.TIMEOUT_LENGTH)
            #print "start ack recieved: %s" % response
            if self.handle_response(response,startno):
                #print "started Connection"
                self.seqno += 1
                return True
            elif time.time() - start_time > 10: #10 seconds without receiving response
                return False


    def handle_timeout(self):
        pass

    def handle_new_ack(self, ack):
        ack_count = int(self.split_packet(ack)[1])
        if ack_count == self.last:
            self.done_ack = True
        #print "ack received: %s" % ack_count
        #print "seqno: %s" % self.seqno
        for i in range(self.seqno, ack_count):
            if len(self.window_buffer) == 0:
                break

            popped = self.window_buffer.pop(0)
            #print "popped: %s" % popped[0:10]
        self.seqno = ack_count


    def handle_dup_ack(self, ack):
        pass

    def log(self, msg):
        if self.debug:
            print msg

'''
This will be run if you run this script from the command line. You should not
change any of this; the grader may rely on the behavior here to test your
submission.
'''
if __name__ == "__main__":
    def usage():
        print "BEARS-TP Sender"
        print "-f FILE | --file=FILE The file to transfer; if empty reads from STDIN"
        print "-p PORT | --port=PORT The destination port, defaults to 33122"
        print "-a ADDRESS | --address=ADDRESS The receiver address or hostname, defaults to localhost"
        print "-d | --debug Print debug messages"
        print "-h | --help Print this usage message"

    try:
        opts, args = getopt.getopt(sys.argv[1:],
                               "f:p:a:d", ["file=", "port=", "address=", "debug="])
    except:
        usage()
        exit()

    port = 33122
    dest = "localhost"
    filename = None
    debug = False

    for o,a in opts:
        if o in ("-f", "--file="):
            filename = a
        elif o in ("-p", "--port="):
            port = int(a)
        elif o in ("-a", "--address="):
            dest = a
        elif o in ("-d", "--debug="):
            debug = True

    s = Sender(dest,port,filename,debug)
    try:
        s.start()
    except (KeyboardInterrupt, SystemExit):
        exit()
