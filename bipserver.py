# Copyright (c) 2018 Kannan Subramani <Kannan.Subramani@bmw.de>
# SPDX-License-Identifier: GPL-3.0
# -*- coding: utf-8 -*-
"""Implementation of bipserver ( for cover art of AVRCP, only contains Image pull feature )"""
import dbus
import dbus.service
import dbus.mainloop.glib


import argparse
import copy
import logging
import operator
import os
import sys

import dateutil.parser

import bluetooth
import time
import tools
import bipheaders as headers

import server
import responses
import requests
import common
import glob

from PIL import Image

from xml_data_binding import image_descriptor, image_handles_descriptor, images_listing

from bluetooth import BluetoothSocket, RFCOMM, OBEX_FILETRANS_CLASS, \
    OBEX_FILETRANS_PROFILE, OBEX_OBJPUSH_CLASS, OBEX_OBJPUSH_PROFILE, \
    OBEX_UUID, PUBLIC_BROWSE_GROUP, RFCOMM_UUID, advertise_service, \
    stop_advertising

logger = logging.getLogger(__name__)

socket = None

class BIPServer(server.Server):
    def __init__(self, device_address, rootdir=""):
        server.Server.__init__(self, device_address)
        if len(rootdir) == 0: 
            self.rootdir = os.getcwd()
        else:
            self.rootdir = "%s/%s" % ( os.getcwd(), rootdir )
        logger.info (self.rootdir)

    def process_request(self, connection, request):
        """Processes the request from the connection."""
        logger.info("\n-----------------------------------")
        if isinstance(request, requests.Connect):
            logger.debug("Request type = connect")
            self.connect(connection, request)
            logger.debug(self.remote_info.max_packet_length)
            logger.debug(self.remote_info.minimum_length)
        elif isinstance(request, requests.Disconnect):
            logger.debug("Request type = disconnect")
            self.disconnect(connection, request)
        elif isinstance(request, requests.Put):
            logger.debug("Request type = put")
            self.put(connection, request)
        elif isinstance(request, requests.Get):
            logger.debug("Request type = get")
            self.get(connection, request)
        else:
            logger.debug("Request type = Unknown. so rejected")
            self._reject(connection)

    def get(self, socket, request):
        decoded_header = self._decode_header_data(request)
        if request.is_final():
            logger.debug("request is final")
            print (decoded_header["Type"])
            if decoded_header["Type"] == "x-bt/img-capabilities":
                self._get_capabilities(socket, decoded_header)
            elif decoded_header["Type"] == "x-bt/img-listing":
                self._get_images_list(socket, decoded_header)
            elif decoded_header["Type"] == "x-bt/img-properties":
                self._get_image_properties(socket, decoded_header)
            elif decoded_header["Type"] == "x-bt/img-img":
                self._get_image(socket, decoded_header)
            elif decoded_header["Type"] == "x-bt/img-thm":
                self._get_linked_thumbnail(socket, decoded_header)
            else:
                logger.error("Requested type = %s is not supported yet.", decoded_header["Type"])
                self.send_response(socket, responses.Bad_Request())

    def _decode_header_data(self, request):
        """Decodes all headers in given request and return the decoded values in dict"""
        logger.debug("_decode_header_data")
        header_dict = {}
        for header in request.header_data:
            h= header.decode()
            logger.info("Decode %s len %u" % (h , len(h)) )
            if len(h) > 0:
                if isinstance(header, headers.Name):
                    h= h.decode("utf-8")
                    print ("Name", h)
                    header_dict["Name"] = h.rstrip("\r\n\t\0")
                    logger.info("Name = %s" % header_dict["Name"])
                elif isinstance(header, headers.Length):
                    h= h.decode("utf-8")
                    print ("Length", h)
                    header_dict["Length"] = h.rstrip("\r\n\t\0")
                    logger.info("Length = %i" % header_dict["Length"])
                elif isinstance(header, headers.Type):
                    print ("Type", h)
                    h = h.decode("utf-8")
                    header_dict["Type"] = h.rstrip("\r\n\t\0")
                    logger.info("Type = %s" % header_dict["Type"])
                elif isinstance(header, headers.Connection_ID):
                    print ("Connection ID", h)
                    h= h.decode("utf-8")
                    header_dict["Connection_ID"] = h.rstrip("\r\n\t\0")
                    logger.info("Connection ID = %s" % header_dict["Connection_ID"])
                elif isinstance(header, headers.Img_Descriptor):
                    print ("Img_Descriptor", h )
                    h= h.decode("utf-8")
                    print (h)
                    header_dict["Img_Descriptor"] = h.rstrip("\r\n\t\0")
                    logger.info("Img Descriptor = %s" % header_dict["Img_Descriptor"])
                elif isinstance(header, headers.Img_Handle):
                    print ("ImgHandle", h)
                    #h= h.decode("utf-8")
                    header_dict["Img_Handle"] = h.rstrip("\r\n\t\0")
                    logger.info("Img Handle = %s" % header_dict["Img_Handle"])
                elif isinstance(header, headers.App_Parameters):
                    print ("App_Parameters", h)
                    #h= h.decode("utf-8")
                    header_dict["App_Parameters"] = h
                    logger.info("App Parameters are :")
                    for param, value in header_dict["App_Parameters"].items():
                        logger.info("{param}: {value}".format(param=param, value=value.decode()))
                else:
                    logger.error("Some Header data is not yet added in _decode_header_data")
                    raise NotImplementedError("Some Header data is not yet added in _decode_header_data")
        return header_dict

    def _decode_app_params(self, app_params):
        """This will decode or populate app_params with default value."""
        decoded_app_params = {}
        if "NbReturnedHandles" in app_params:
            decoded_app_params["NbReturnedHandles"] = app_params["NbReturnedHandles"].decode()
        if "ListStartOffset" in app_params:
            decoded_app_params["ListStartOffset"] = app_params["ListStartOffset"].decode()
        if "LatestCapturedImages" in app_params:
            decoded_app_params["LatestCapturedImages"] = app_params["LatestCapturedImages"].decode()
        return decoded_app_params

    def _get_capabilities(self, socket, decoded_header):
        """Returns level of support for various imaging capabilities"""
        logger.info("_get_capabilities invoked")
        # TODO: replace with real data
        capabilities_object = tools.generate_dummy_imaging_capabilities()
        header_list = [headers.End_Of_Body(tools.export_xml(capabilities_object))]
        self.send_response(socket, responses.Success(), header_list)

    def _get_images_list(self, socket, decoded_header):
        """Returns list of handles for available images along with file info like cdate, mdate etc"""
        logger.info("_get_images_list invoked")
        app_params = self._decode_app_params(decoded_header["App_Parameters"])

        # TODO: replace with real data
        images_listing_object = tools.generate_dummy_images_listing()

        nb_returned_handles = app_params["NbReturnedHandles"]
        list_startoffset = app_params["ListStartOffset"]
        latest_captured_images = app_params["LatestCapturedImages"]

        # filtering images of images_listing using filtering_parameters
        img_handles_desc = image_handles_descriptor.parseString(decoded_header["Img_Descriptor"], silence=True)
        filtered_images_listing = self._filter_images_listing(img_handles_desc, images_listing_object)
        if nb_returned_handles == 0:
            nb_returned_handles_hdr = {"NbReturnedHandles":
                                       headers.NbReturnedHandles(len(filtered_images_listing.image))
                                       }
            empty_image_listing = images_listing.images_listing()
            header_list = [headers.App_Parameters(nb_returned_handles_hdr),
                           headers.Img_Descriptor(tools.export_xml(img_handles_desc)),
                           headers.End_Of_Body(tools.export_xml(empty_image_listing))]

        else:
            # restrict the images of images_listing using ListStartOffset and NbReturnedHandles
            restricted_images_listing = self._restricted_images_listing(filtered_images_listing,
                                                                        list_startoffset,
                                                                        nb_returned_handles)

            # order descending based on created time to get latest captured images
            if latest_captured_images:
                restricted_images_listing.image.sort(key=operator.attrgetter("created"), reverse=True)

            nb_returned_handles_hdr = {"NbReturnedHandles":
                                       headers.NbReturnedHandles(len(restricted_images_listing.image))
                                       }
            header_list = [headers.App_Parameters(nb_returned_handles_hdr),
                           headers.Img_Descriptor(tools.export_xml(img_handles_desc)),
                           headers.End_Of_Body(tools.export_xml(restricted_images_listing))]
        self.send_response(socket, responses.Success(), header_list)

    @staticmethod
    def _restricted_images_listing(images_listing, list_startoffset, nb_returned_handles):
        images_listing_copy = copy.deepcopy(images_listing)
        images_listing_copy.image = images_listing_copy.image[list_startoffset:
                                                              list_startoffset + nb_returned_handles]
        return images_listing_copy

    @staticmethod
    def _filter_images_listing(img_handles_desc, images_listing):
        """filters the images_listing based on filtering_parameters in img_handles_desc"""
        filtering_parameters = img_handles_desc.filtering_parameters
        images_listing_copy = copy.deepcopy(images_listing)
        for image in images_listing.image:
            match = True
            if filtering_parameters.created:
                match &= (dateutil.parser.parse(image.created) in tools.DatetimeRange(filtering_parameters.created))
            if filtering_parameters.modified:
                match &= (dateutil.parser.parse(image.modified) in tools.DatetimeRange(filtering_parameters.modified))
            if filtering_parameters.encoding:
                match &= (image.encoding == filtering_parameters.encoding)
            if filtering_parameters.pixel:
                match &= (tools.Pixel(image.pixel) in tools.PixelRange(filtering_parameters.pixel))
            if not match:
                images_listing_copy.image.remove(image)
        return images_listing_copy

    def _get_image_properties(self, socket, decoded_header):
        # TODO: replace with real data and get the properties for specified handle
        """Returns info regarding image formats, encodings etc."""
        handle = decoded_header["Img_Handle"]
        logger.info("_get_image_properties: %s" % handle)
        if len(handle) != 7: # not in tools.DUMMY_IMAGE_HANDLES:
            self.send_response(socket, responses.Not_Found(), [])
            return
        filelist = glob.glob("%s/%s_*.jpg" % (self.rootdir, handle) )
        if len(filelist)==0:
            im_file_name = "%s/%s_.jpg" % (self.rootdir, handle)
            imagefile = tools.generate_dummy_image(handle, thumbnail=True)
            file1 = open(im_file_name, 'wb'); file1.write(imagefile); file1.close()
        else:
            im_file_name = filelist[0]
        fs=os.path.getsize(im_file_name)
        logger.info( "image %s %u" % (im_file_name, fs) )

        img_prop_obj = tools.generate_image_properties(handle, fs)

        exp = tools.export_xml(img_prop_obj)
        logger.info("<xmp>%s</xmp>" % exp )
        header_list = [headers.End_Of_Body(exp.encode('utf-8'))]
        self.send_response(socket, responses.Success(), header_list)

    def _get_image(self, socket, decoded_header, thumbnail=False):
        """Returns an Image with specified format and encoding"""
        handle = decoded_header["Img_Handle"]
        logger.info("%s get_image " % handle)
         
        if len(handle) != 7 : #not in tools.DUMMY_IMAGE_HANDLES
            self.send_response(socket, responses.Not_Found(), [])
            return

        if not thumbnail:
            if decoded_header.get("Img_Descriptor") == None:
                thumbnail=True
                logger.info( "Thumbnail" )
            else:
                logger.info( decoded_header.get("Img_Descriptor") )

        if not thumbnail:
            description = image_descriptor.parseString(decoded_header["Img_Descriptor"], silence=True)
            logger.info( "<xmp>%s %s</xmp>" % (description.image.encoding, description.image.pixel) )

        # construct a dummy image

        filelist = glob.glob("%s/%s_*.jpg" % (self.rootdir, handle) )
        logger.info(filelist)

        if len(filelist) > 0:
            im_file=filelist[0]
            if os.path.isfile( im_file ):
                with open(im_file, 'rb') as fp:
                    imagefile = fp.read()
        
        else:
            im_file = "%s/%s_.jpg" % (self.rootdir, handle)
            if not thumbnail:
                imagefile = tools.generate_dummy_image(handle, description.image.encoding, thumbnail=False)
            else:
                imagefile = tools.generate_dummy_image(handle, thumbnail=True)

            file1 = open(im_file, 'wb'); file1.write(imagefile); file1.close()

        imagefile_size = os.path.getsize(im_file)
        logger.info("ImageSize %u" % imagefile_size)
        with Image.open( im_file ) as img:
            logger.info ("JPEG Size %s*%s" % (img.width, img.height) )

        # TODO: adjust the max packet length in obex connect, since bt rfcomm can send only ~1000 bytes at once
        max_length = min(self.mtu, self.remote_info.max_packet_length) - 64
        bytes_transferred = 0

        header_list = [headers.Length(imagefile_size)]

        while bytes_transferred < imagefile_size:
            if  imagefile_size - bytes_transferred > max_length:
                image_chunk = imagefile[bytes_transferred: (bytes_transferred + max_length)]
                header_list.append(headers.Body(image_chunk))
                self.send_response(socket, responses.Continue(), header_list)
            else:
                image_chunk = imagefile[bytes_transferred:]
                header_list.append(headers.End_Of_Body(image_chunk))
                self.send_response(socket, responses.Success(), header_list)

            header_list = []
            bytes_transferred += len(image_chunk)
            if bytes_transferred < imagefile_size:
                request = self.request_handler.decode(self.connection)
                # 'continue' response and process the subsequent requests
                if not isinstance(request, requests.Get_Final):
                    raise IOError("didn't receive get final request for continuation")
                    #self.connected = False #restart connection
                    break
            else:
                logger.info("bytes_transferred %u/%u" % (len(image_chunk), bytes_transferred) )

    def _get_linked_thumbnail(self, socket, decoded_header):
        """Returns thumbnail version of the images"""
        logger.info("_get_linked_thumbnail invoked")
        self._get_image(socket, decoded_header, thumbnail=True)


    def serve1(self, socket):
        """Override: changes 'connection' as instance variable.
        So we can access it in other methods, enables handling
        of 'Continue' response and subsequent requests
        """
        self.socket = socket
        logger.info ("SERVE")
        while True:
            connection, address = socket.accept()
            if not self.accept_connection():
                print ("close")
                connection.close()
                continue
            self.connected = True

            logger.info("OBEX, Connection from %s %s", address, dir(connection))
            self.connection = connection
            opt = bluetooth.get_l2cap_options(socket)
            self.mtu = min(opt[0], opt[1])
            
            while self.connected:
                logger.info ("+++++++++++++++++++++++++++++++++READY omtu:%u imtu:%u", opt[0], opt[1])
                try:
                    #data = connection.recv(1024)
                    #logger.info("OBEX, Connection from %s", data)
                    request = self.request_handler.decode(connection)
                    print("==", request)
                    self.process_request(connection, request)
                    if not self.connected: 
                        connection.close()
                except Exception  as err: #Exception
                    logger.info("error:close connection %s" % (err))  
                    connection.close()  
                    self.connected = False

def run_server(device_address, rootdir=""):
    # Run the server in a function so that, if the server causes an exception
    # to be raised, the server instance will be deleted properly, giving us a
    # chance to create a new one and start the service again without getting
    # errors about the address still being in use.
    socket = None

    bip_server = BIPServer(device_address, rootdir)

    while True:
        try:
            port=0x1021 #11
            socket = BluetoothSocket(bluetooth.L2CAP) #RFCOMM)   #server_sock=bluetooth.BluetoothSocket( bluetooth.L2CAP 
            socket.bind((device_address, port))
            #bluetooth.set_l2cap_mtu( socket, 65535 )

            opt = bluetooth.get_l2cap_options(socket)
            print(opt)
            opt[0] = 1024 #omtu
            opt[1] = 1024 #imtu
            #opt[2] = 1 #flush_to
            opt[3] = 3  #mode
            opt[5] = 10 #max_tx
            opt[6] = 5  #tx_win_size
            print(opt)
            bluetooth.set_l2cap_options(socket, opt)

            socket.listen(1)
            print("Starting server for %s on port %i" % (socket.getsockname(), port) )
            #socket = bip_server.start_service()
            bip_server.serve1(socket)
        except Exception  as err:
            logger.debug (err) 
            if (socket):
                socket.close()
            else:
                raise err


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG,  filename='/tmp/bip_log', format='%(asctime)s %(name)s %(levelname)-8s %(message)s')
#    <attribute id="0x0003">                                        \
#        <!-- ServiceID -->                                         \
#        <uuid value="7163DD54-4A7E-11E2-B47C-0050C2490048" />      \
#    </attribute>          
    console = logging.StreamHandler()
    console.setLevel(logging.DEBUG)
# set a format which is simpler for console use
    formatter = logging.Formatter('%(name)-12s: %(levelname)-8s %(message)s')
# tell the handler to use this format
    console.setFormatter(formatter)
# add the handler to the root logger
    logging.getLogger().addHandler(console)                                         \

    parser = argparse.ArgumentParser(description="Basic Imaging Profile server...")
    parser.add_argument("--address", required=True, help="bluetooth address to start the server")
    parser.add_argument("--imagedir", default="", help="images directory from where images needs to be served")
    args = parser.parse_args()

    logger.info("Starting server on address %s and imagedir %s" % (args.address, args.imagedir) )

    bus = dbus.SystemBus()

    file1 = open('coverart_record.xml', 'r')
    sdp_record_xml = file1.read(); file1.close();
    UUID = "7163dd54-4a7e-11e2-b47c-0050c2490048"
    opts = dbus.Dictionary({
         "ServiceRecord": sdp_record_xml,
#             "Role": "server",
         "RequireAuthentication": dbus.Boolean(False),
         "RequireAuthorization": dbus.Boolean(False),
#             "AutoConnect" : dbus.Boolean(True),
#             "Name": "CoverArt",
#             "Channel": dbus.UInt16(11), #BIP_DEFAULT_CHANNEL
#             "Service":"0x111b"
    }, signature="sv")

    manager = dbus.Interface(bus.get_object("org.bluez", "/org/bluez"), "org.bluez.ProfileManager1")
#        profile = BluetoothBluezProfile(bus, "/org/bluez/profile/coverart")
    manager.RegisterProfile("/org/bluez/profile/coverart", UUID, opts)
    """
    UUID ="1105"
    file1 = open('/home/admin/obex_push.xml', 'r')
    obex_push_xml = file1.read(); file1.close();
    opts = dbus.Dictionary({
         "ServiceRecord": obex_push_xml,
#             "Role": "server",
         "RequireAuthentication": dbus.Boolean(False),
         "RequireAuthorization": dbus.Boolean(False),
#             "AutoConnect" : dbus.Boolean(True),
#             "Name": "OBEX Push",
#             "Channel": dbus.UInt16(12), #BIP_DEFAULT_CHANNEL
#             "Service":"0x1105"
    }, signature="sv")
    manager.RegisterProfile("/org/bluez/profile/obex_push", UUID, opts)
    """
    services = bluetooth.find_service(address=args.address, uuid="110c")
    if not services:
        sys.stderr.write("No BIP (IMAGEPUSH_UUID) service found\n")
        #sys.exit(1)
    else:
        for service in services:
            print(service)

    run_server(args.address, args.imagedir)

