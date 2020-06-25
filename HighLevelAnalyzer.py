# Feedback:
# could not figure out where to import GraphTime from, had to check our unit tests.
# unit tests or attached debugger would save many hours
# auto-rerun would be nice
# auto or manual console clear would be nice
# some way of displaying numbers as hex in the bubbles.
# sometimes my format strings don't apply at all.
# can't display quote character in resulting strings, they get html encoded.


from saleae.analyzers import HighLevelAnalyzer, AnalyzerFrame, StringSetting, NumberSetting, ChoicesSetting
from saleae.data import GraphTime, GraphTimeDelta
from enum import Enum

# https://www.embedded.com/usb-type-c-and-power-delivery-101-power-delivery-protocol/
# preamble: 8 bytes of 0x55
# address. 2 bytes.
# header. 2 bytes.
# [3:0] command code
# [4]: 0
# [5] role?
# [6:7] spec revision
# [8] role?
# [11:9] message id
# [14:12] number of data objects
# data objects. each is 4 bytes. between 0 and 7, count in header.
# crc: 4 bytes
# eop: end of packet, 4 bits. likely not accessable from the manchester analyzer, so ignored.

# 4b5b encoding


encoding_lookup = {
    0B0000: 0B11110,
    0B0001: 0B01001,
    0B0010: 0B10100,
    0B0011: 0B10101,
    0B0100: 0B01010,
    0B0101: 0B01011,
    0B0110: 0B01110,
    0B0111: 0B01111,
    0B1000: 0B10010,
    0B1001: 0B10011,
    0B1010: 0B10110,
    0B1011: 0B10111,
    0B1100: 0B11010,
    0B1101: 0B11011,
    0B1110: 0B11100,
    0B1111: 0B11101,
}

addresses = {
    'SOP': [1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 1, 0, 0, 0, 1],
    'SOP\'': [1, 1, 0, 0, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 0, 0, 1, 1, 0],
    'SOP\'\'': [1, 1, 0, 0, 0, 0, 0, 1, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 0],
    'Hard Reset': [0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 1, 1, 1, 1, 0, 0, 1],
    'Cable Reset': [0, 0, 1, 1, 1, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 0, 0, 1, 1, 0],
    'SOP\'_debug': [1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0],
    'SOP\'\'_debug': [1, 1, 0, 0, 0, 1, 1, 0, 0, 1, 0, 0, 1, 1, 0, 1, 0, 0, 0, 1],
}

data_commands = {
    1: 'Source_Capabilities',
    2: 'Request',
    3: 'BIST',
    4: 'Sink_Capabilities',
    5: 'Battery_Status',
    6: 'Alert',
    7: 'Get_Contry_Info',
    8: 'Get_Contry_Info',
}

control_commands = {
    1: 'GoodCRC',
    2: 'GotoMin',
    3: 'Accept',
    4: 'Reject',
    5: 'Ping',
    6: 'PS_RDY',
    7: 'Get_Source_Cap',
    8: 'Get_Sink_Cap',
}


class Word():
    start_time = None
    end_time = None
    data = None

    def __init__(self, start_time, end_time, data):
        self.start_time = start_time
        self.end_time = end_time
        self.data = data

# High level analyzers must subclass the HighLevelAnalyzer class.


class Hla(HighLevelAnalyzer):

    # An optional list of types this analyzer produces, providing a way to customize the way frames are displayed in Logic 2.
    result_types = {
        'preamble': {'format': 'Preamble'},
        'address': {'format': 'Start Of Packet: {{data.address}}'},
        'header': {'format': '# of Objects: {{data.number_of_objects}} Message ID: {{data.message_id}} Command Code: {{data.command_code}} Spec Revision: {{data.spec_revision}}'},
        'object': {'format': 'Object {{data.index}}: {{data.data}}'},
        'crc': {'format': 'CRC: {{data.crc}}'},
        'eop': {'format': 'end of packet'}
    }

    def __init__(self):
        self.result = None
        self.engine = None
        self.word_result = None
        self.leftover_bits = []

    def decode(self, frame: AnalyzerFrame):
        '''
        Process a frame from the input analyzer, and optionally return a single `AnalyzerFrame` or a list of `AnalyzerFrame`s.

        The type and data values in `frame` will depend on the input analyzer.
        '''

        if self.engine is None:
            self.engine = self.state_machine()
            self.engine.send(None)

        try:
            output_frame = self.engine.send(frame)
            if output_frame is not None:
                return output_frame
        except StopIteration:
            self.engine = None

    def state_machine(self):
        next = None
        while True:
            preamble_start = None
            preamble_end = None
            self.leftover_bits.clear()
            for x in range(8):
                frame = next
                if frame is None:
                    frame = yield
                next = None
                if frame.data['data'] != 0xAA:
                    next = None
                    return
                if x == 0:
                    preamble_start = frame.start_time
                if x == 7:
                    preamble_end = frame.end_time
            print('Preamble')
            next = yield AnalyzerFrame('preamble', preamble_start, preamble_end, {})

            address_word = yield from self.get_bits(next, 20)
            self.leftover_bits.extend(address_word.data)
            address_cmd = self.decode_address(self.leftover_bits)
            self.leftover_bits = self.leftover_bits[20:]
            print(address_cmd)
            next = yield AnalyzerFrame('address', address_word.start_time, address_word.end_time, {'address': address_cmd})

            header_word = yield from self.get_bits(next, 20)
            header_decoded = self.bits_to_bytes(header_word.data, 2)
            header_int = int.from_bytes(header_decoded, "little")
            object_count = (header_int >> 12) & 0x07

            # object_count = 7
            print(self.decode_header(header_int))
            next = yield AnalyzerFrame('header', header_word.start_time, header_word.end_time, self.decode_header(header_int))

            for object_index in range(object_count):
                object_word = yield from self.get_bits(next, 40)
                object_decoded = self.bits_to_bytes(object_word.data, 4)
                object_int = int.from_bytes(object_decoded, "little")
                print('data object {data}'.format(data = hex(object_int)))
                next = yield AnalyzerFrame('object', object_word.start_time, object_word.end_time, {'index': object_index, 'data': hex(object_int)})

            crc_word = yield from self.get_bits(next, 40)
            crc_decoded = self.bits_to_bytes(crc_word.data, 4)
            crc_int = int.from_bytes(crc_decoded, "little")
            print('crc {crc}'.format(crc=hex(crc_int)))
            next = yield AnalyzerFrame('crc', crc_word.start_time, crc_word.end_time, {'crc': hex(crc_int)})

    def get_bits(self, first_frame, num_bits):
        bits_needed = max(num_bits - len(self.leftover_bits), 0)
        bytes_to_read = int(bits_needed / 8)
        extra_bits = bits_needed % 8
        if bits_needed % 8 != 0:
            bytes_to_read += 1
        self.word_result = None
        word_start = None
        word_end = None
        # data = bytearray(num_bytes)
        raw_bits = []
        for x in range(bytes_to_read):
            frame = first_frame
            if x > 0:
                frame = yield
            if x == 0:
                word_start = frame.start_time
                if len(self.leftover_bits) > 0:
                    # adjust the start time!
                    fraction = len(self.leftover_bits) / 8 * 0.9
                    span = float(frame.end_time - frame.start_time)
                    adjustment = fraction * span
                    word_start = frame.start_time - \
                        GraphTimeDelta(second=adjustment)
            if x == bytes_to_read-1:
                word_end = frame.end_time
                if extra_bits > 0:
                    fraction = extra_bits / 8 * 0.9
                    span = float(frame.end_time - frame.start_time)
                    adjustment = fraction * span
                    word_end = frame.end_time - \
                        GraphTimeDelta(second=adjustment)
            raw_bits.extend(self.byte_to_bits(frame.data['data']))
        return Word(word_start, word_end, raw_bits)

    def bits_to_bytes(self, new_bits, num_bytes):
        decoded = bytearray(num_bytes)
        # leftovers is an array in time order. everything is LSB first (bytes and bits) in USB pd anyway.
        self.leftover_bits.extend(new_bits)
        # get everything into a huge array of bits
        for i in range(num_bytes):
            # convert 10 bits to 8 bits, save in decoded.
            fiver = self.leftover_bits[:5]
            nibble = self.decode5bits(fiver)
            self.leftover_bits = self.leftover_bits[5:]
            decoded[i] = nibble
            nibble = self.decode5bits(self.leftover_bits[:5])
            self.leftover_bits = self.leftover_bits[5:]
            decoded[i] |= nibble << 4
        return decoded

    def byte_to_bits(self, byte):
        bits = []
        for x in range(8):
            bits.append((byte >> x) & 0x01)
        return bits

    def decode5bits(self, bit_array):
        raw_word = 0
        for i in range(5):
            raw_word = raw_word | (bit_array[i] << i)
        new_word = -1
        for entry in encoding_lookup:
            if encoding_lookup[entry] == raw_word:
                new_word = entry
                break
        if new_word == -1:
            new_word = 0

        return new_word

    def decode_address(self, bits):
        for address in addresses:
            raw_address = addresses[address]
            fiddle_sop = []
            for word in range(4):
                for bit in range(5):
                    fiddle_sop.append(raw_address[word * 5 + 4 - bit])
            match = True
            for i in range(20):
                if bits[i] != fiddle_sop[i]:
                    match = False
            if match == True:
                return address
        return 'Unknown SOP*'

    def decode_header(self, header):
        number_of_objects = (header >> 12) & 0x07
        command_code = header & 0xF
        if number_of_objects == 0:
            if command_code in control_commands:
                command_code = control_commands[command_code]
        else:
            if command_code in data_commands:
                command_code = data_commands[command_code]            
        return {
            'number_of_objects': number_of_objects,
            'message_id': (header >> 9) & 0x07,
            'spec_revision': (header >> 6) & 0x03,
            'command_code': str(command_code)
        }
