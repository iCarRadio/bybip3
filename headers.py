"""
headers.py - Classes encapsulating OBEX headers.

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

import struct


class Header:
    code = None

    def __init__(self, data, encoded=False):

        if encoded:
            self.data = data
        else:
            self.data = self.encode(data)

    def encode(self, data):
        raise NotImplementedError()


class UnicodeHeader(Header):

    def decode(self):
        return str(self.data, encoding="utf_16_be").rstrip("\x00")

    def encode(self, data):
        encoded_data = data.encode("utf_16_be") + b"\x00\x00"
        return struct.pack(">BH", self.code,
                           len(encoded_data) + 3) + encoded_data


class DataHeader(Header):

    def decode(self):
        return self.data

    def encode(self, data):
        return struct.pack(">BH", self.code, len(data) + 3) + data


class ByteHeader(Header):

    def decode(self):
        return struct.unpack(">B", self.data)[0]

    def encode(self, data):
        return struct.pack(">BB", self.code, data)


class FourByteHeader(Header):

    def decode(self):
        return struct.unpack(">I", self.data)[0]

    def encode(self, data):
        return struct.pack(">BI", self.code, data)


class Count(FourByteHeader):
    code = 0xC0


class Name(UnicodeHeader):
    code = 0x01


class Type(DataHeader):
    code = 0x42

    def encode(self, data):
        if data[-1:] != b"\x00":
            data += b"\x00"
        return struct.pack(">BH", self.code, len(data) + 3) + data


class Length(FourByteHeader):
    code = 0xC3


class Time(DataHeader):
    code = 0x44


class Description(UnicodeHeader):
    code = 0x05


class Target(DataHeader):
    code = 0x46


class HTTP(DataHeader):
    code = 0x47


class Body(DataHeader):
    code = 0x48


class EndOfBody(DataHeader):
    code = 0x49


class Who(DataHeader):
    code = 0x4A


class ConnectionId(FourByteHeader):
    code = 0xCB


class AppParameters(DataHeader):
    code = 0x4C


class AuthChallenge(DataHeader):
    code = 0x4D


class AuthResponse(DataHeader):
    code = 0x4E


class ObjectClass(DataHeader):
    code = 0x51


class UserDefined:
    pass


header_dict = {
    0xC0: Count,
    0x01: Name,
    0x42: Type,
    0xC3: Length,
    0x44: Time,
    0x05: Description,
    0x46: Target,
    0x47: HTTP,
    0x48: Body,
    0x49: EndOfBody,
    0x4A: Who,
    0xCB: ConnectionId,
    0x4C: AppParameters,
    0x4D: AuthChallenge,
    0x4E: AuthResponse,
    0x51: ObjectClass
}


def header_class(header_id):

    try:
        return header_dict[header_id]

    except KeyError:

        if 0x30 <= (header_id & 0x3f) <= 0x3f:
            return UserDefined

    return Header


# aliases for renamed classes
# the old names are deprecated and should not be used anymore
# they are scheduled for removal in the future
# pylint: disable=invalid-name
App_Parameters = AppParameters
Auth_Challenge = AuthChallenge
Auth_Response = AuthResponse
Connection_ID = ConnectionId
End_Of_Body = EndOfBody
Object_Class = ObjectClass
# pylint: enable=invalid-name
