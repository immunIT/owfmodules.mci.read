from tqdm import tqdm

from octowire_framework.module.AModule import AModule
from octowire.mci import MCI
from owfmodules.mci.detect import Detect


class Read(AModule):
    def __init__(self, owf_config):
        super(Read, self).__init__(owf_config)
        self.meta.update({
            'name': 'MCI read.',
            'version': '1.0.0',
            'description': 'Memory-Card read content through MCI interface.',
            'author': 'Jordan Ovrè / Ghecko <jovre@immunit.ch>, Paul Duncan / Eresse <pduncan@immunit.ch>'
        })
        self.options = {
            "start_address": {"Value": "", "Required": True, "Type": "int",
                              "Description": "The address of the first byte to receive.", "Default": 0},
            "size": {"Value": "", "Required": False, "Type": "int",
                     "Description": "The number of byte(s) to read. If unset, the module will try to detect the MCI "
                                    "interface and perform a full-dump from the start_address", "Default": ""},
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
            self.logger.handle("Unable to retrieve the size of the Memory-Card. Exiting...", self.logger.ERROR)
            return None

    def read(self, mci_interface, size, start_block, block_offset):
        self.logger.handle("Start reading the content of the memory card...", self.logger.INFO)
        # Read by block of 512 bytes to avoid overloading the computer RAM
        with open(self.options["dumpfile"]["Value"], "wb") as f:
            for block_index in tqdm(range(0, size // self.chunk_size), desc="Read", unit='B', unit_scale=True,
                                    unit_divisor=1000, ascii=" #",
                                    bar_format="{desc} : {percentage:3.0f}%[{bar}] {n_fmt}/{total_fmt} Blocks "
                                               "(512 bytes) [elapsed: {elapsed} left: {remaining}]"):
                block_number = block_index + start_block
                content = mci_interface.receive(self.chunk_size, block_number)
                # First block case. If start_address is not the index of a block.
                if block_index == 0:
                    f.write(content[block_offset:])
                # Last block case. If the last bytes is not a full block
                elif block_index == size // self.chunk_size:
                    f.write(content[:])

    def process(self):
        mci_interface = MCI(serial_instance=self.owf_serial)
        size = self.options["size"]["Value"]
        start_address = self.options["start_address"]["Value"]

        # If size not set, then try to detect the MCI interface to retrieve the memory size.
        if size == "":
            size = self.detect()
            if size is None:
                return
        # Memory Cards are block devices - 1 block = 512 bytes
        # Calculate start block
        start_block = start_address // self.chunk_size
        # Calculate start block offset
        start_block_offset = start_address % self.chunk_size
        # Calculate last block offset

        # Start reading the memory card content
        self.read(mci_interface, size, start_block, block_offset)

    def run(self):
        """
        Main function.
        Read Memory-Card through MCI interface.
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
