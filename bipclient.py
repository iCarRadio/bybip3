# Copyright (c) 2018 Kannan Subramani <Kannan.Subramani@bmw.de>
# SPDX-License-Identifier: GPL-3.0
# -*- coding: utf-8 -*-
"""Implementation of bipclient to test bipserver ( for cover art of AVRCP )"""

import atexit
import io
import logging
import os
import readline
import sys

from optparse import make_option
from PIL import Image
import bluetooth
import cmd2

import tools
import bipheaders as headers


#from PyOBEX import client, responses
import client
import responses


from xml_data_binding import image_descriptor, image_handles_descriptor, images_listing

logger = logging.getLogger(__name__)

sock = None

class BIPClient(client.Client):
    """Basic Imaging Profile Client"""

    def __init__(self, address, port):
        print (address, port)
        client.Client.__init__(self, address, port)

    def get_capabilities(self):
        """Requests level of support for various imaging capabilities"""
        logger.info("get_capabilities requested")
        # connection_id will be automatically prepended by pyobex/client.py:_send_headers
        header_list = [headers.Type(b'x-bt/img-capabilities')]
        return self.get(header_list=header_list)

    def get_images_list(self, nb_returned_handles=0, list_startoffset=0, latest_captured_images=0x00):
        """Requests list of handles for available images along with file info like cdate, mdate etc"""
        logger.info("get_images_list requested. params = %s", locals())

        print(headers.NbReturnedHandles(nb_returned_handles))

        app_parameters_dict = {
            "NbReturnedHandles": headers.NbReturnedHandles(nb_returned_handles),
            "ListStartOffset": headers.ListStartOffset(list_startoffset),
            "LatestCapturedImages": headers.LatestCapturedImages(latest_captured_images)
        }

        # construct the image_handles_descriptor xml using xml_data_binding
        root = image_handles_descriptor.image_handles_descriptor()

        root.filtering_parameters = image_handles_descriptor.filtering_parameters(created="19990101T000000Z-20010101T235959Z")

        img_handles_desc_data = tools.export_xml(root)

        print (app_parameters_dict, img_handles_desc_data)

        header_list = [headers.Type(b'x-bt/img-listing')] #,
                       #headers.App_Parameters(app_parameters_dict),
                       #headers.Img_Descriptor(img_handles_desc_data)]

        print(header_list)

        return self.get(header_list=header_list)

    def get_image_properties(self, img_handle):
        """Requests info regarding image formats, encodings etc."""
        logger.info("get_image_properties requested")
        header_list = [headers.Type(b'x-bt/img-properties'), headers.Img_Handle(img_handle)]
        return self.get(header_list=header_list)

    def get_image(self, image_handle):
        """Requests an Image with specified format and encoding"""
        logger.info("get_image requested")
        img_descriptor_object = image_descriptor.image_descriptor()

        img_descriptor_object.image = image_descriptor.image(encoding="JPEG", pixel="1300*1300")
        xml= tools.export_xml(img_descriptor_object)
        print() 
        header_list = [headers.Type(b'x-bt/img-img'), 
                       headers.Img_Handle(image_handle),
                       headers.Img_Descriptor( xml.encode('utf8') )]

        return self.get(header_list=header_list)

    def get_linked_thumbnail(self, image_handle):
        """Requests thumbnail version of the images"""
        logger.info("get_linked_thumbnail requested")
        header_list = [headers.Type(b'x-bt/img-thm'), headers.Img_Handle(image_handle)]
        return self.get(header_list=header_list)

class REPL(cmd2.Cmd):
    """REPL to use BIP client"""
    
    @staticmethod
    def colorize (string, color):
        return string
        #return string

    def __init__(self):
        super().__init__()
        #cmd2.Cmd.__init__(self)
        self.prompt = "bip> "
        self.intro = self.colorize("Welcome to the Basic Imaging Profile!", "green")
        
        self.client = None
        self._valid_image_handle = None
        self._store_history()
        #cmd2.set_use_arg_list(False) # If you want to be able to pass arguments with spaces to scripts, https://cmd2.readthedocs.io/_/downloads/en/0.7.8/pdf/

    @staticmethod
    def _store_history():
        history_file = os.path.expanduser('~/.bipclient_history')
        if not os.path.exists(history_file):
            with open(history_file, "w") as fobj:
                fobj.write("")
        readline.read_history_file(history_file)
        atexit.register(readline.write_history_file, history_file)

    # The default behavior of cmd2 is to pass the user input directly to your do_* methods as a string.
    # The object passed to your method is actually a Statement object, which has additional attributes that may be helpful, including arg_list and argv:
    # for arg in statement.arg_list:
    #     self.poutput(arg)
    # @with_argument_list 
    # https://cmd2.readthedocs.io/en/latest/features/argument_processing.html#argument-list

    #@options([], arg_desc="server_address")
    def do_connect(self, line, opts = {}):
        """Connects to BIP Server"""
        if len(line)<2:
            line="B8:27:EB:C6:CA:CE"
        server_address = line
        if not server_address:
            raise TypeError("server_address cannot be empty")
        logger.info("Finding BIP service ...")
        services = bluetooth.find_service(address=server_address, uuid="7163dd54-4a7e-11e2-b47c-0050c2490048")
        if not services:
            sys.stderr.write("No BIP (IMAGEPUSH_UUID) service found\n")
            #sys.exit(1)
            host = server_address
            port=0x1021
        else:
            for service in services:
                print(service)
            host = services[0]["host"]
            port = services[0]["port"]
            logger.info("Connecting to bip server = (%s, %s, %s)", host, port, services[0]["service-id"])
            logger.info("BIP service found!")

        host = server_address
        port=0x1021
        self.client = BIPClient(host, port) 
        uuid = b"\x71\x63\xDD\x54\x4A\x7E\x11\xE2\xB4\x7C\x00\x50\xC2\x49\x00\x48"
        logger.info("Connecting to bip server = (%s, %s)", host, port)
        sock=bluetooth.BluetoothSocket(bluetooth.L2CAP)
        #bd_addr = "B8:27:EB:C6:CA:CE"
        #port = 0x1021
        opt = bluetooth.get_l2cap_options(sock)

        opt[0] = 4096
        opt[1] = 4096
        #opt[2] = 0x2000 #flush_to
        opt[3] = 3  #mode
        opt[5] = 10 #max_tx
        opt[6] = 5  #tx_win_size
        print(opt)

        bluetooth.set_l2cap_options(sock, opt)

        sock.connect( (host, port) )

        opt = bluetooth.get_l2cap_options(sock)
        print (opt)
        #bluetooth.set_l2cap_mtu (sock, 8087)
        self.client.set_socket ( sock )

        print(uuid)
        result = self.client.connect ( header_list = [headers.Target(uuid)] )
        print (bluetooth.get_l2cap_options(sock) )
        if not isinstance(result, responses.ConnectSuccess):
            logger.error("Connect Failed, Terminating the bip client..")
            return
        logger.info("Connect success")
        self.prompt = self.colorize("bip> ", "green")

    #@options([], arg_desc="")
    def do_disconnect(self, line, opts = {}):
        """Disconnects the BIP connection"""
        if self.client is None:
            logger.error("BIPClient is not even connected.. Connect and then try disconnect")
            sys.exit(2)
        logger.debug("Disconnecting bip client with bip server")
        self.client.disconnect()
        self.client = None
        self.prompt = self.colorize("bip> ", "yellow")

    #@options([], arg_desc="")
    def do_capabilities(self, line, opts = {}):
        """Returns the capabilities supported by BIP Server"""
        logger.debug("Requesting BIP Service capabilities")
        result = self.client.get_capabilities()
        if isinstance(result, responses.FailureResponse):
            logger.error("GetCapabilities failed ... reason = %s", result)
            return
        header, capabilities = result
        logger.debug("\n" + capabilities)

    
    #@options([make_option('-c', '--max-count', type=int, default=0, help="Maximum number of image handles to be returned"),
    #               make_option('-o', '--start-offset', type=int, default=0, help="List start offset"),
    #               make_option('-x', '--latest-images-only', type=int, default=0, help="Include latest captured images only")], arg_desc="")
    def do_imageslist(self, args, opts = { }):
        """Returns list of available images"""
        logger.debug("Requesting for available imageslist")
        result = self.client.get_images_list(opts.get("max_count", 1), opts.get("start_offset", 0), opts.get("latest_images_only", 0))
        if isinstance(result, responses.FailureResponse):
            logger.error("GetImagesList failed ... reason = %s", result)
            return
        header, images_list = result
        logger.debug("\n" + images_list)
        parsed_img_listing = images_listing.parseString(images_list, silence=True)
        if parsed_img_listing.image:
            self._valid_image_handle = parsed_img_listing.image[0].handle

    #@options([], arg_desc="image_handle")
    def do_imageproperties(self, line, opts = {}):
        """Gets the properties of image for given image_handle"""
        logger.debug("Requesting for image properties of handle = %s", line)
        result = self.client.get_image_properties(line)
        if isinstance(result, responses.FailureResponse):
            logger.error("GetImageProperties failed ... reason = %s", result)
            return
        header, image_prop = result
     
        logger.debug("\n" + image_prop.decode())

    #@options([], arg_desc="image_handle")
    def do_getimage(self, line, opts = {}):
        """Gets image for given image_handle"""
        logger.debug("Requesting for image of handle = %s", line)
        result = self.client.get_image(line)
        if isinstance(result, responses.FailureResponse):
            logger.error("GetImage failed ... reason = %s", result)
            return
        header, image_data = result
        im = Image.open(io.BytesIO(image_data))
        im.save("%s_.jpg" % line)
        logger.debug("getimage response. image saved in %s_.jpg" % line)
        im.show()

    #@options([], arg_desc="image_handle")
    def do_getthumbnail(self, line, opts = {}):
        """Gets Thumbnail version of image for given image_handle"""
        logger.debug("Requesting for thumbnail image of handle = %s", line)
        result = self.client.get_linked_thumbnail(line)
        if isinstance(result, responses.FailureResponse):
            logger.error("GetThumbnail failed ... reason = %s", result)
            return
        header, image_data = result
        im = Image.open(io.BytesIO(image_data))
        im.save("%s_thumbnail_image.jpg" % line)
        logger.debug("getthumbnail response. image saved in %s_thumbnail_image.jpg" %  line)
        im.show()

    #@options([], arg_desc="server_address")
    def do_test(self, line, opts = {}):
        """Triggers Basic tests for all functionality of BIPClient"""
        self.do_connect(line)
        #self.do_capabilities("")
        #self.do_imageslist("")
        #self.do_imageslist("--max-count 2 --start-offset 1 --latest-images-only 1")
        self._valid_image_handle = "1000099"
        if self._valid_image_handle:
            self.do_imageproperties(self._valid_image_handle)
            self.do_getimage(self._valid_image_handle)
            self.do_getthumbnail(self._valid_image_handle)
        self._valid_image_handle = None
        self.do_disconnect("")


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG, format='%(asctime)s %(name)s %(levelname)-8s %(message)s')

    #sock=bluetooth.BluetoothSocket(bluetooth.L2CAP)

    #bd_addr = "B8:27:EB:C6:CA:CE"
    #port = 0x1021

    #sock.connect((bd_addr, port))

    #sock.send("hello!!")

    #sock.close()


    repl = REPL()
    #repl.do_connect("B8:27:EB:C6:CA:CE")
    repl.cmdloop() 
    sys.exit(0)