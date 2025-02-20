# Copyright (c) 2018 Kannan Subramani <Kannan.Subramani@bmw.de>
# SPDX-License-Identifier: GPL-3.0
# -*- coding: utf-8 -*-.
"""Implementation of BIP related headers"""

import struct

from headers import *

#from PyOBEX.headers import header_dict, UnicodeHeader, DataHeader, App_Parameters, Target

IMAGEPUSH_UUID = "E33D9545-8374-4AD7-9EC5-C16BE31EDE8E"
IMAGEPULL_UUID = "8EE9B3D0-4608-11D5-841A-0002A5325B4E"
COVERART_UUID = "7163DD54-4A7E-11E2-B47C-0050C2490048"

"""
Basic Imaging primary session UUID Basic 
Imaging Image Push E33D9545-8374-4AD7-9EC5-C16BE31EDE8E Basic 
Imaging Image Pull 8EE9B3D0-4608-11D5-841A-0002A5325B4E Basic 
Imaging Advanced ImagePrinting 92353350-4608-11D5-841A-0002A5325B4E Basic 
Imaging Automatic Archive 940126C0-4608-11D5-841A-0002A5325B4E Basic 
Imaging Remote Camera 947E7420-4608-11D5-841A-0002A5325B4E Basic 
Imaging Remote Display 94C7CD20-4608-11D5-841A-0002A5325B4E Table 5-5: 
Bluetooth Basic primary session UUIDs

5.5.3 Secondary Session 
EstablishmentSecondary sessions are OBEX sessions established using a Target header witheither of the following values:
Basic Imaging secondary sessionUUID Basic 
Imaging Referenced Objects 8E61F95D-1A79-11D4-8EA4-00805F9B9834 Basic 
Imaging Archived Objects 8E61F95E-1A79-11D4-8EA4-00805F9B9834
"""

#########################
#                       #
# User Defined Headers  #
#                       #
#########################
# code | length | data
# 30   | 00 13  | 00 31 00 30 00 30 00 30 00 30 00 30 00 34 00 00
class Img_Handle(UnicodeHeader):
    code = 0x30


class Img_Descriptor(DataHeader):
    code = 0x71


header_dict.update({
    0x71: Img_Descriptor,
    0x30: Img_Handle
})


#############################################
#                                           #
# Application Parameters Header Properties  #
#                                           #
#############################################
class AppParamProperty(object):
    tagid = None # virtual
    fmt = None # virtual

    def __init__(self, data, encoded=False):
        self.data = data if encoded else self.encode(data)

    def encode(self, data):
        return struct.pack(">BB", self.tagid, struct.calcsize(self.fmt)) + data

    def decode(self):
        return struct.unpack(">BB", self.data[:2]), self.data[2:]


class OneByteProperty(AppParamProperty):
    fmt = ">B"

    def encode(self, data):
        return super(OneByteProperty, self).encode(struct.pack(self.fmt, data))

    def decode(self):
        headers, data = super(OneByteProperty, self).decode()
        return struct.unpack(self.fmt, data)[0]


class TwoByteProperty(AppParamProperty):
    fmt = ">H"

    def encode(self, data):
        return super(TwoByteProperty, self).encode(struct.pack(self.fmt, data))

    def decode(self):
        headers, data = super(TwoByteProperty, self).decode()
        return struct.unpack(self.fmt, data)[0]


class FourByteProperty(AppParamProperty):
    fmt = ">I"

    def encode(self, data):
        return super(FourByteProperty, self).encode(struct.pack(self.fmt, data))

    def decode(self):
        headers, data = super(FourByteProperty, self).decode()
        return struct.unpack(self.fmt, data)[0]


class SixteenByteProperty(AppParamProperty):
    fmt = ">16B"

    def encode(self, data):
        return super(SixteenByteProperty, self).encode(struct.pack(self.fmt, data))

    def decode(self):
        headers, data = super(SixteenByteProperty, self).decode()
        return struct.unpack(self.fmt, data)[0]


class NbReturnedHandles(TwoByteProperty):
    tagid = 0x01


class ListStartOffset(TwoByteProperty):
    tagid = 0x02


class LatestCapturedImages(OneByteProperty):
    tagid = 0x03


class PartialFileLength(FourByteProperty):
    tagid = 0x04


class PartialFileStartOffset(FourByteProperty):
    tagid = 0x05


class TotalFileSize(FourByteProperty):
    tagid = 0x06


class EndFlag(OneByteProperty):
    tagid = 0x07


class RemoteDisplay(OneByteProperty):
    tagid = 0x08


class ServiceID(SixteenByteProperty):
    tagid = 0x09


class StoreFlag(OneByteProperty):
    tagid = 0x0A


app_parameters_dict = {
    0x01: NbReturnedHandles,
    0x02: ListStartOffset,
    0x03: LatestCapturedImages,
    0x04: PartialFileLength,
    0x05: PartialFileStartOffset,
    0x06: TotalFileSize,
    0x07: EndFlag,
    0x08: RemoteDisplay,
    0x09: ServiceID,
    0x0A: StoreFlag
}


# Sample App Parameters data
# code | length | data
# 4c   | 00 0e  | 0202000101020002030101

def extended_decode(self):
    """Decodes the App_Parameters header data into AppParamProperties dict"""
    # size of tagid = 1 byte
    # size of length = 1 byte
    data = self.data
    res_dict = {}
    while data:
        tagid = ord(data[0])
        length = ord(data[1])
        app_param_class = app_parameters_dict[tagid]
        res_dict[app_param_class.__name__] = app_param_class(data[:length + 2], encoded=True)
        data = data[length + 2:]
    return res_dict


def extended_encode(self, data_dict):
    """Encodes the AppParamProperties dict + super().encode"""
    data = ""
    for item in data_dict.values():
        data += item.data
    return struct.pack(">BH", self.code, len(data) + 3) + data


App_Parameters.decode = extended_decode
App_Parameters.encode = extended_encode
