#!/usr/bin/env python
# -*- coding: utf-8 -*-

import psycopg2
import select
import os
import sys
import time
import fcntl
import argparse
import getpass
from socket import socket, AF_INET, SOCK_DGRAM

def checkStop():
    return os.path.isfile(STOP_FILE)

if __name__ == '__main__':

    parser = argparse.ArgumentParser()
    parser.add_argument('-H', '--pg_host', type=str, action="store", default='localhost')
    parser.add_argument('-P', '--pg_port', type=int, action="store", default=5432)
    parser.add_argument('-D', '--dbname', type=str, action="store", default='postgres')
    parser.add_argument('-U', '--username', type=str, action="store", default=os.getenv('PGUSER', getpass.getuser()))
    parser.add_argument('-W', '--password', type=str, action="store", default=os.getenv('PGPASSWORD'))
    parser.add_argument('-A', '--socket_host', type=str, action="store", required=True)
    parser.add_argument('-X', '--socket_port', type=int, action="store", required=True)
    parser.add_argument('-C', '--channel', type=str, action="store", required=True)
    parser.add_argument('-B', '--start_listen', action = 'store_true')
    parser.add_argument('-E', '--stop_listen', action = 'store_true')
    args = parser.parse_args()

    STOP_FILE = '/var/tmp/pg_metricus.%s.stop' % args.channel
    LOCK_FILE  = '/var/tmp/pg_metricus.%s.lock' % args.channel

    if args.start_listen and args.stop_listen:
        sys.exit(0)

    if args.start_listen:
        if os.path.isfile(STOP_FILE):
            os.unlink(STOP_FILE)
        sys.exit(0)

    if args.stop_listen:
        open(STOP_FILE, 'w').close()
        sys.exit(0)

    if checkStop():
        sys.exit(0)

    lock_fd = os.open(LOCK_FILE, os.O_WRONLY | os.O_CREAT, 0644)
    st = fcntl.fcntl(lock_fd, fcntl.F_GETFD)
    fcntl.fcntl(lock_fd, fcntl.F_SETFD, st | fcntl.FD_CLOEXEC)

    try:
        fcntl.flock(lock_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except IOError as e:
        if e.errno != os.errno.EAGAIN:
            raise
        sys.exit(1)

    os.ftruncate(lock_fd, 0)
    os.write(lock_fd, "%s %s\n" % (os.getpid(), time.ctime()))
    os.fsync(lock_fd)

    connect_string = 'host={host} port={port} dbname={dbname} user={user} connect_timeout=5'.format(
        host=args.pg_host, port=args.pg_port, dbname=args.dbname, user=args.username
    )

    try:
        conn = psycopg2.connect(connect_string + (' password=' + args.password if args.password else ''))
        conn.set_isolation_level(psycopg2.extensions.ISOLATION_LEVEL_AUTOCOMMIT)

        curs = conn.cursor()
        curs.execute("LISTEN {0};".format(args.channel))

        addr = (args.socket_host, args.socket_port)
        sock = socket(AF_INET, SOCK_DGRAM)

        while not checkStop():
            if select.select([conn],[],[],5) != ([],[],[]):
                conn.poll()
                while conn.notifies:
                    notification = conn.notifies.pop(0)
                    sock.sendto(notification.payload.encode('utf-8'), addr)
    except Exception, e:
        sys.stdout.write("\nerror: %s\n" % e.message)
    finally:
        sock.close()
        conn.close()
