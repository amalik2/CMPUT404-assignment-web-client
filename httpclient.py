#!/usr/bin/env python3
# coding: utf-8
# Copyright 2016 Abram Hindle, https://github.com/tywtyw2002, and https://github.com/treedust
# 
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
# 
#     http://www.apache.org/licenses/LICENSE-2.0
# 
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# Do not use urllib's HTTP GET and POST mechanisms.
# Write your own HTTP GET and POST
# The point is to understand what you have to send and get experience with it

import sys
import socket
import re
import ssl

from urllib.parse import urlparse, urlencode

def help():
    print("httpclient.py [GET/POST] [URL]\n")

class HTTPResponse(object):
    def __init__(self, code=200, body="", headers="", statusMessage=""):
        self.code = code
        self.body = body
        self.headers = headers
        self.statusMessage = statusMessage

    # Credit to Mark Byers at https://stackoverflow.com/a/4912856 for how to use __str__
    def __str__(self):
        return self.body

    def is_redirect(self):
        return self.code == 301 or self.code == 302
    
    def get_header(self, header):
        splitHeaders = self.headers.split("\r\n")
        searchText = header + ":"
        for headerDetails in splitHeaders:
            if (searchText in headerDetails):
                index = headerDetails.index(":") + 2
                return headerDetails[index:]
        return ""

class HTTPClient(object):
    def connect(self, host, port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.connect((host, port))
        self.socket = sock
        return sock

    def get_code(self, data):
        return int(data[0].split(" ")[1])

    def get_headers(self,data):
        headers = ""
        for line in data.split("\r\n"):
            if (":" in line):
                headers += line + "\r\n"
            elif (line == ""):
                break
        return headers

    def get_body(self, lines):
        body = ""
        atBody = False
        for line in lines:
            if (line == "\r" and not atBody):
                atBody = True
            elif (atBody):
                body += line + "\n"
        return body

    def get_status_message(self, data):
        return " ".join(data[0].split(" ")[2:])
    
    def sendall(self, data):
        self.socket.sendall(data.encode('utf-8'))
        
    def close(self):
        self.socket.close()

    # read everything from the socket
    def recvall(self, sock):
        buffer = bytearray()
        done = False
        while not done:
            part = sock.recv(1024)
            if (part):
                buffer.extend(part)
                tempBuf = str(buffer)
                if ("301 Moved Permanently" in tempBuf and "Location: " in tempBuf and len(part) < 1024 and ("</body>" in tempBuf or "</html>" in tempBuf)):
                    return tempBuf
            else:
                done = not part
        return buffer.decode('utf-8')

    def _get_socket_address(self, url):
        details = urlparse(url)
        port = details.port
        host = details.netloc
        if (port == None):
            if (":" in host):
                port = host.split(":")[1]
            elif (details.scheme == "https"):
                port = 443
            else:
                port = 80
        if (":" in host):
            host = host.split(":")[0]
        return (host, port, details.path)

    def _parse_response(self, response):
        headers = ""
        statusMessage = ""

        lines = response.split("\n")
        if (len(lines) == 1 and lines[0] == ""):
            print("EMPTY RESPONSE")
            body = ""
            code = 400
        else:
            headers = self.get_headers(response)
            body = self.get_body(lines)
            code = self.get_code(lines)
            statusMessage = self.get_status_message(lines)
        return HTTPResponse(code, body, headers, statusMessage)

    def _send_request(self, url, method, requestConcat):
        address = self._get_socket_address(url)
        sock = self.connect(address[0], address[1])
        host = address[0] + ":" + str(address[1])
        path = address[2]
        if (path == ""):
            path = "/"

        if (method == "GET"):
            self.sendall("GET %s HTTP/1.1\r\nHost: %s\r\nConnection: Upgrade\r\nUpgrade: websocket\r\n\r\n" % (path, host))
        self.sendall("%s %s HTTP/1.1\r\nHost: %s\r\nAccept: */*\r\n%s" % (method, path, host, requestConcat))

        response = self.recvall(sock)
        sock.close()
        responseData = self._parse_response(response)
        return responseData

    def _parse_args(self, args):
        if (args == None):
            return ""
        return urlencode(args)

    def _get_byte_length(self, string):
        # Credit to Kris at https://stackoverflow.com/a/30686735 for string byte length
        return len(string.encode("utf-8"))

    def GET(self, url, args=None):
        # TODO: does GET need to handle args?
        return self._send_request(url, "GET", "\r\n")

    def POST(self, url, args=None):
        data = self._parse_args(args)
        concat = "Content-Type: application/x-www-form-urlencoded\r\nContent-Length: %d\r\n\r\n%s" % (self._get_byte_length(data), data)
        response = self._send_request(url, "POST", concat)
        return response

    def command(self, url, command="GET", args=None):
        if ((not url.startswith("http")) and url.startswith("www.")):
            url = "http://" + url
        if (command == "POST"):
            return self.POST( url, args )
        else:
            return self.GET( url, args )
    
if __name__ == "__main__":
    client = HTTPClient()
    command = "GET"
    if (len(sys.argv) <= 1):
        help()
        sys.exit(1)
    elif (len(sys.argv) == 3):
        print(client.command( sys.argv[2], sys.argv[1] ))
    else:
        print(client.command( sys.argv[1] ))
