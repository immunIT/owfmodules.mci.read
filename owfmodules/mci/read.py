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
            'version': '1.1.0',
            'description': 'Read Memory Card contents through MCI interface',
            'author': 'Jordan Ovrè / Ghecko <jovre@immunit.ch>, Paul Duncan / Eresse <pduncan@immunit.ch>'
        })
        self.options = {
            "start_address": {"Value": "", "Required": True, "Type": "hex",
                              "Description": "Address to start reading from.", "Default": 0},
            "size": {"Value": "", "Required": False, "Type": "int",
                     "Description": "The number of bytes to read. If unset, the module will try to detect the MCI "
                                    "interface and perform a full dump from the defined start address", "Default": ""},
            "dumpfile": {"Value": "", "Required": True, "Type": "file_w", "Description": "Dump output filename",
                         "Default": ""}
        }
        self.dependencies.extend([
            "octowire-lib>=1.0.6",
            "owfmodules.mci.detect>=1.0.0"
         ])

    def detect(self):
        detect_module = Detect(owf_config=self.config)
        detect_module.owf_serial = self.owf_serial
        resp = detect_module.run(return_value=True)
        if resp['status'] == 0:
            return resp["capacity"]
        else:
            self.logger.handle("Unable to retrieve the size of the Memory Card. Exiting...", self.logger.ERROR)
            return None

    def read(self):
        mci_interface = MCI(serial_instance=self.owf_serial)
        size = self.options["size"]["Value"]
        start_address = self.options["start_address"]["Value"]

        # If size not set, try to detect the MCI interface to retrieve the memory size.
        if size == "":
            size = self.detect() * 1024
            if size is None:
                return

        self.logger.handle("Reading the contents of the Memory Card...", self.logger.INFO)
        with open(self.options["dumpfile"]["Value"], "wb") as f:
            progress_bar = tqdm(initial=0, total=size, desc="Reading", unit='B', unit_scale=True, ascii=" #",
                                bar_format="{desc} : {percentage:3.0f}%[{bar}] {n_fmt}/{total_fmt}B "
                                           "[elapsed: {elapsed} left: {remaining}, {rate_fmt}{postfix}]")
            while size > 0:
                # Read 8 block of 512 Bytes per iteration
                chunk_size = 4096 if size > 4096 else size
                # Read
                chunk = mci_interface.receive(size=chunk_size, start_addr=start_address)

                # Calculate the new address
                start_address = start_address + chunk_size

                # Write chunk to file
                f.write(chunk)

                # Decrement the size
                size = size - chunk_size

                # refresh the progress bar
                progress_bar.update(chunk_size)
                progress_bar.refresh()

            # Close the progress bar
            progress_bar.close()

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
            self.read()
        except ValueError as err:
            self.logger.handle(err, self.logger.ERROR)
        except Exception as err:
            self.logger.handle("{}: {}".format(type(err).__name__, err), self.logger.ERROR)
