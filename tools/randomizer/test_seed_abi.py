import copy
import struct
import unittest
from validate_seed import REQUIRED, validate


class SeedABI(unittest.TestCase):
    def setUp(self):
        self.symbols = {name:(0x690000 + i*0x100,4) for i,name in enumerate(sorted(REQUIRED))}
        self.symbols['rItemOverrides']=(0x680000,16)
        self.symbols['rCustomMessages']=(0x710000,0)
        fields = {name:'00000000' for name in REQUIRED}
        fields['rItemOverrides']=struct.pack('<II',1,2).hex()
        entry=bytearray(0x60)
        struct.pack_into('<I',entry,0,10)
        struct.pack_into('<II',entry,16,0,4)
        self.seed={'format':'retuned-seed-proof-v1','runtime_ready':False,
                   'runtime_fields_hex':fields,'message_data_hex':'01020304',
                   'message_entries_hex':entry.hex()}

    def test_valid_relative_message(self):
        before=copy.deepcopy(self.seed)
        self.assertEqual(validate(self.seed,self.symbols)['message_count'],1)
        self.assertEqual(self.seed,before)

    def test_wrong_guest_abi(self):
        self.symbols['gSettingsContext']=(0x690000,8)
        with self.assertRaises(ValueError):validate(self.seed,self.symbols)

    def test_missing_table(self):
        del self.seed['runtime_fields_hex']['rDungeonImportance']
        with self.assertRaises(ValueError):validate(self.seed,self.symbols)

    def test_full_override_table_without_sentinel(self):
        self.symbols['rItemOverrides']=(0x680000,8)
        with self.assertRaises(ValueError):validate(self.seed,self.symbols)

    def test_message_outside_buffer(self):
        entry=bytearray.fromhex(self.seed['message_entries_hex'])
        struct.pack_into('<II',entry,16,3,4)
        self.seed['message_entries_hex']=entry.hex()
        with self.assertRaises(ValueError):validate(self.seed,self.symbols)

    def test_duplicate_message_id(self):
        self.seed['message_entries_hex']*=2
        with self.assertRaises(ValueError):validate(self.seed,self.symbols)

    def test_table_outside_guest_memory(self):
        self.symbols['gSettingsContext']=(0x587958,4)
        with self.assertRaises(ValueError):validate(self.seed,self.symbols)

if __name__=='__main__':unittest.main()
