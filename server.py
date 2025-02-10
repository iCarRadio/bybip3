"""
server.py - Server classes for handling OBEX requests and sending responses.

Copyright (C) 2007 David Boddie <david@boddie.org.uk>

This file is part of the PyOBEX Python package.

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
"""

from bluetooth import (BluetoothSocket, RFCOMM, OBEX_FILETRANS_CLASS,
                       OBEX_FILETRANS_PROFILE, OBEX_OBJPUSH_CLASS,
                       OBEX_OBJPUSH_PROFILE, OBEX_UUID, PUBLIC_BROWSE_GROUP,
                       RFCOMM_UUID, advertise_service, stop_advertising,
                       PORT_ANY)

from common import ObexVersion
import requests
import responses


class Server:

    def __init__(self, address=""):

        self.address = address
        self.max_packet_length = 0xffff
        self.obex_version = ObexVersion()
        self.request_handler = requests.RequestHandler()
        self.connected = False
        self.remote_info = None

    def start_service(self, port, name, uuid, service_classes,
                      service_profiles, provider, description, protocols):

        socket = BluetoothSocket(RFCOMM)
        socket.bind((self.address, port))
        socket.listen(1)

        advertise_service(
            socket, name, uuid, service_classes, service_profiles,
            provider, description, protocols
            )

        print("Starting server for %s on port %i" % socket.getsockname())
        return socket

    @staticmethod
    def stop_service(socket):

        stop_advertising(socket)

    def serve(self, socket):

        while True:

            connection, _ = socket.accept()
            if not self.accept_connection():
                connection.close()
                continue

            self.connected = True

            while self.connected:

                request = self.request_handler.decode(connection)

                self.process_request(connection, request)

    def _max_length(self):

        if hasattr(self, "remote_info"):
            return self.remote_info.max_packet_length
        return self.max_packet_length

    def send_response(self, socket, response, header_list=None):

        # TODO: This needs to be able to split messages that are longer than
        # the maximum message length agreed with the other party.
        while header_list:

            if response.add_header(header_list[0], self._max_length()):
                header_list.pop(0)
            else:
                socket.sendall(response.encode())
                response.reset_headers()

        # Always send at least one request.
        socket.sendall(response.encode())

    def _reject(self, socket):

        self.send_response(socket, responses.Forbidden())

    # pylint: disable=no-self-use
    def accept_connection(self, address=None, port=None):
        _, _ = address, port
        return True

    def process_request(self, socket, request):

        """Processes the request from the socket.

        This method should be reimplemented in subclasses to add support for
        more request types.
        """

        if isinstance(request, requests.Connect):
            self.connect(socket, request)

        elif isinstance(request, requests.Disconnect):
            self.disconnect(socket, request)

        elif isinstance(request, requests.Put):
            self.put(socket, request)

        else:
            self._reject(socket)

    def connect(self, socket, request):

        if request.obex_version > self.obex_version:
            self._reject(socket)

        self.remote_info = request
        max_length = self.remote_info.max_packet_length

        flags = 0
        data = (self.obex_version.to_byte(), flags, max_length)

        response = responses.ConnectSuccess(data)
        self.send_response(socket, response)

    def disconnect(self, socket, _):

        response = responses.Success()
        self.send_response(socket, response)
        self.connected = False

    def put(self, socket, _):

        self._reject(socket)


class BrowserServer(Server):

    def start_service(self, port=PORT_ANY):

        name = "OBEX File Transfer"
        # "E006" also appears to work if used as a service ID. However, 1106
        # is the official profile number:
        # (https://www.bluetooth.org/en-us/specification/assigned-numbers/service-discovery)
        uuid = "F9EC7BC4-953C-11d2-984E-525400DC9E09"
        service_classes = [OBEX_FILETRANS_CLASS]
        service_profiles = [OBEX_FILETRANS_PROFILE]
        provider = ""
        description = "File transfer"
        protocols = [OBEX_UUID]

        return Server.start_service(
            self, port, name, uuid, service_classes, service_profiles,
            provider, description, protocols)


class PushServer(Server):

    def start_service(self, port=PORT_ANY):

        name = "OBEX Object Push"
        uuid = PUBLIC_BROWSE_GROUP
        service_classes = [OBEX_OBJPUSH_CLASS]
        service_profiles = [OBEX_OBJPUSH_PROFILE]
        provider = ""
        description = "File transfer"
        protocols = [RFCOMM_UUID, OBEX_UUID]

        return Server.start_service(
            self, port, name, uuid, service_classes, service_profiles,
            provider, description, protocols)
