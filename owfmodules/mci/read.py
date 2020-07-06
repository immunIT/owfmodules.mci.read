# -*- coding: utf-8 -*-

# Octowire Framework
# Copyright (c) ImmunIT - Jordan Ovrè / Paul Duncan
# License: Apache 2.0
# Paul Duncan / Eresse <pduncan@immunit.ch>
# Jordan Ovrè / Ghecko <jovre@immunit.ch>

from tqdm import tqdm

from octowire_framework.module.AModule import AModule
from octowire.mci import MCI
from owfmodules.mci.detect import Detect


class Read(AModule):
    def __init__(self, owf_config):
        super(Read, self).__init__(owf_config)
        self.meta.update({
            'name': 'MCI read',
            'version': '1.0.0',
            'description': 'Read Memory Card contents through MCI interface.',
            'author': 'Jordan Ovrè / Ghecko <jovre@immunit.ch>, Paul Duncan / Eresse <pduncan@immunit.ch>'
        })
        self.options = {
            "start_address": {"Value": "", "Required": True, "Type": "int",
                              "Description": "Byte address to start reading from.", "Default": 0},
            "size": {"Value": "", "Required": False, "Type": "int",
                     "Description": "The number of bytes to read. If unset, the module will try to detect the MCI "
                                    "interface and perform a full dump from start_address", "Default": ""},
            "dumpfile": {"Value": "", "Required": True, "Type": "file_w", "Description": "Dump output filename",
                         "Default": ""}
        }
        self.dependencies.append(
            "owfmodules.mci.detect>=1.0.0"
        )
        self.chunk_size = 512

    def detect(self):
        detect_module = Detect(owf_config=self.config)
        detect_module.owf_serial = self.owf_serial
        resp = detect_module.run(return_value=True)
        print(resp)
        if resp['status'] == 0:
            return resp["capacity"]
        else:
            self.logger.handle("Unable to retrieve the size of the Memory Card. Exiting...", self.logger.ERROR)
            return None

    def read(self, mci_interface, start_off, start_blk, blk_count, size):
        self.logger.handle("Reading the contents of the Memory Card...", self.logger.INFO)
        with open(self.options["dumpfile"]["Value"], "wb") as f:
            for blk in tqdm(range(0, blk_count), desc="Reading", unit='B', unit_scale=True,  unit_divisor=1000,
                            ascii=" #", bar_format="{desc} : {percentage:3.0f}%[{bar}] {n_fmt}/{total_fmt} Blocks "
                                                   "(512 bytes) [elapsed: {elapsed} left: {remaining}]"):
                # Determine actual block size (last block may be smaller than others)
                cs = self.chunk_size
                if (blk + 1) >= blk_count:
                    cs = (start_off + size) % self.chunk_size

                # Read and strip data from first chunk up to start offset
                chunk = mci_interface.receive(cs, start_blk + blk)

                if blk == 0:
                    chunk = chunk[start_off:]

                # Write chunk to file
                f.write(chunk)

    def process(self):
        mci_interface = MCI(serial_instance=self.owf_serial)
        size = self.options["size"]["Value"]
        start_address = self.options["start_address"]["Value"]

        # If size not set, try to detect the MCI interface to retrieve the memory size.
        if size == "":
            size = self.detect() * 1024
            if size is None:
                return

        # Determine start block, start offset and total block count
        start_blk = start_address // self.chunk_size
        start_off = start_address % self.chunk_size
        blk_count = ((start_off + size) // self.chunk_size)
        if ((start_off + size) % self.chunk_size) > 0:
            blk_count = blk_count + 1

        # Read Data
        self.read(mci_interface, start_off, start_blk, blk_count, size)

    def run(self):
        """
        Main function.
        Read Memory Card contents through MCI interface.
        :return:
        """
        # If detect_octowire is True then detect and connect to the Octowire hardware. Else, connect to the Octowire
        # using the parameters that were configured. This sets the self.owf_serial variable if the hardware is found.
        self.connect()
        if not self.owf_serial:
            return
        try:
            self.process()
        except ValueError as err:
            self.logger.handle(err, self.logger.ERROR)
        except Exception as err:
            self.logger.handle("{}: {}".format(type(err).__name__, err), self.logger.ERROR)
