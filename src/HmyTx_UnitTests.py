import unittest
import HmyTx_Utils as HmyUtils


class TestUtilsMethods(unittest.TestCase):

    def test_toOne(self):
        self.assertEqual(HmyUtils.convert_one_to_hex('one1unfc5h5plzf2je2zgr838mlvyuqnq0ucmcr4u3').lower(
        ), '0xe4d38a5e81f892a9654240cf13efec2701303f98')
        self.assertEqual(HmyUtils.convert_one_to_hex(
            'one1unfc5h5plzf2je2zgr838mlvyuqnq0ucmcr4u3'), '0xE4D38a5e81F892A9654240cF13efeC2701303F98')
        self.assertEqual(HmyUtils.convert_one_to_hex(
            '0xE4D38a5e81F892A9654240cF13efeC2701303F98'), '0xE4D38a5e81F892A9654240cF13efeC2701303F98')
        self.assertEqual(HmyUtils.convert_one_to_hex(
            '0xE4D38a5e81F892A9654240cF13efeC2701303F98'.lower()), '0xE4D38a5e81F892A9654240cF13efeC2701303F98')

    def test_toHex(self):
        self.assertEqual(HmyUtils.convert_hex_to_one(
            '0xe4d38a5e81f892a9654240cf13efec2701303f98'), 'one1unfc5h5plzf2je2zgr838mlvyuqnq0ucmcr4u3')
        self.assertEqual(HmyUtils.convert_hex_to_one(
            '0xE4D38a5e81F892A9654240cF13efeC2701303F98'), 'one1unfc5h5plzf2je2zgr838mlvyuqnq0ucmcr4u3')
        self.assertEqual(HmyUtils.convert_hex_to_one(
            'one1unfc5h5plzf2je2zgr838mlvyuqnq0ucmcr4u3'), 'one1unfc5h5plzf2je2zgr838mlvyuqnq0ucmcr4u3')

    def test_checkSum(self):
        self.assertTrue(HmyUtils.is_valid_address(
            'one1unfc5h5plzf2je2zgr838mlvyuqnq0ucmcr4u3'))
        self.assertTrue(HmyUtils.is_valid_address(
            HmyUtils.convert_hex_to_one('0xe4d38a5e81f892a9654240cf13efec2701303f98')))
        self.assertTrue(HmyUtils.is_valid_address(
            HmyUtils.convert_hex_to_one('0xE4D38a5e81F892A9654240cF13efeC2701303F98')))


if __name__ == '__main__':
    unittest.main(verbosity=2)
