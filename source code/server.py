import socket
import threading
import os
import sys
from collections import defaultdict

# định nghĩa các biến
HOST = ''
PORT = 7734
V = 'P2P-CI/1.0'
# element: {(host,port), set[rfc #]}
peers = defaultdict(set)
# element: {RFC #, (title, set[(host, port)])}
rfcs = {}
lock = threading.Lock()


# hàm start

def start():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.bind((HOST, PORT))
        s.listen(5)
        print('Server %s is listening on port %s' %
                (V, PORT))

        while True:
            soc, addr = s.accept()
            print('%s:%s connected' % (addr[0], addr[1]))
            thread = threading.Thread(
                target=handler, args=(soc, addr))
            thread.start()
    except KeyboardInterrupt:
        print('\nShutting down the server..\nGood Bye!')
        try:
            sys.exit(0)
        except SystemExit:
            os.exit(0)


def handler(soc, addr):
    # keep recieve request from client
    host = None
    port = None
    while True:
        try:
            req = soc.recv(1024).decode()
            print('Recieve request:\n%s' % req)
            lines = req.splitlines()
            version = lines[0].split()[-1]
            if version != V:
                soc.sendall(str.encode(
                    V + ' 505 P2P-CI Version Not Supported\n'))
            else:
                method = lines[0].split()[0]
                if method == 'ADD':
                    host = lines[1].split(None, 1)[1]
                    port = int(lines[2].split(None, 1)[1])
                    num = int(lines[0].split()[-2])
                    title = lines[3].split(None, 1)[1]
                    #k = title
                    addRecord(soc, (host, port), num, title)
                elif method == 'LOOKUP':
                    num = int(lines[0].split()[-2])
                    #title = lines[3].split(None, 1)[1]
                    getPeersOfRfc(soc, num)
                elif method == 'LIST':
                    #title = lines[3].split(None, 1)[1]
                    getAllRecords(soc)
                else:
                    raise AttributeError('Method Not Match')
        except ConnectionError:
            print('%s:%s left' % (addr[0], addr[1]))
            # Clean data if necessary
            if host and port:
                clear(host,port)
            soc.close()
            break
        except BaseException:
            try:
                soc.sendall(str.encode(V + '  400 Bad Request\n'))
            except ConnectionError:
                print('%s:%s left' % (addr[0], addr[1]))
                # Clean data if necessary
                if host and port:
                    clear(host,port)
                soc.close()
                break



def clear( host, port):
    lock.acquire()
    nums = peers[(host, port)]
    for num in nums:
        rfcs[num][1].discard((host, port))
    if not rfcs[num][1]:
        rfcs.pop(num, None)
    peers.pop((host, port), None)
    lock.release()


def addRecord( soc, peer, num, title):
        lock.acquire()
        try:
            peers[peer].add(num)
            rfcs.setdefault(num, (title, set()))[1].add(peer)
        finally:
            lock.release()
        header = V + ' 200 OK\n'
        header += 'RFC %s %s %s %s\n' % (num,
                                         title, peer[0], peer[1])
        soc.sendall(str.encode(header))

def getPeersOfRfc( soc, num):
    lock.acquire()
    try:
        if num not in rfcs:
            header = V + ' 404 Not Found\n'
        else:
            header = V + ' 200 OK\n'
            title = rfcs[num][0]
            for peer in rfcs[num][1]:
                header += 'RFC %s %s %s %s\n' % (num,
                                                    title, peer[0], peer[1])
    finally:
        lock.release()
    soc.sendall(str.encode(header))

def getAllRecords( soc):
    lock.acquire()
    try:
        if not rfcs:
            header = V + ' 404 Not Found\n'
        else:
            header = V + ' 200 OK\n'
            for num in rfcs:
                title = rfcs[num][0]
                for peer in rfcs[num][1]:
                    header += 'RFC %s %s %s %s\n' % (num, title, peer[0], peer[1])
    finally:
        lock.release()
    soc.sendall(str.encode(header))


start()
