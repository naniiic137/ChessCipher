"""Tests for the ChessCipher mapping, filename format and decoder (python -m unittest)."""
import random
import unittest

import main


class MappingTests(unittest.TestCase):
    def test_every_square_used_once(self):
        c2s, s2c = main.create_mapping()
        squares = [sq for cands in c2s.values() for sq in cands]
        self.assertEqual(len(squares), 64)
        self.assertEqual(set(squares), set(main.ALL_SQUARES))
        self.assertEqual(len(s2c), 64)

    def test_slot_counts(self):
        c2s, _ = main.create_mapping()
        for ch in 'ETA ':
            self.assertEqual(len(c2s[ch]), 3)
        for ch in 'QZXJ0123456789':
            self.assertEqual(len(c2s[ch]), 1)
        self.assertEqual(len(c2s['B']), 2)

    def test_repeated_letters_rotate(self):
        self.assertEqual(len(set(main.message_to_squares('AAA'))), 3)
        sq = main.message_to_squares('LL')
        self.assertNotEqual(sq[0], sq[1])


class RoundTripTests(unittest.TestCase):
    def filename_for(self, msg):
        squares = main.encode_squares(msg)
        moves = [main.make_notation(sq, 'knight', random.Random(0)) for sq in squares]
        return main.format_filename(moves, main.result_token(len(squares)))

    def test_round_trip(self):
        rng = random.Random(42)
        for _ in range(300):
            msg = ''.join(rng.choice(main.CHARACTERS) for _ in range(rng.randint(1, 40)))
            self.assertEqual(main.decode_filename(self.filename_for(msg)), msg)

    def test_v2_marker(self):
        name = self.filename_for('HELLO WORLD')
        self.assertTrue(name.endswith(('_1-0.png', '_0-1.png')))
        self.assertEqual(main.parse_cipher(name)[1], True)

    def test_readme_v2_example(self):
        self.assertEqual(main.decode_filename('1.Ba5_d3_2.Bxh2_b3_3.Rh3_Rh5_0-1'), 'HELLO')
        self.assertEqual(main.decode_filename('1.a5_Qd3_2.Nxh2+_Nb3_3.h3_Nxh5_0-1'), 'HELLO')

    def test_legacy_v1_filename_still_decodes(self):
        # README example from the original one-square-per-character format
        self.assertEqual(main.decode_filename('1.Be2+_e5_2.Rxh8_Rh8_3.a5'), 'HELLO')
        self.assertEqual(main.decode_filename('1.Be2+_e5_2.Rxh8_Rh8_3.a5.png'), 'HELLO')

    def test_normal_game_is_rejected(self):
        self.assertIsNone(main.decode_filename('1.e4_e5_2.Nf3_Nc6_3.Bb5_a6'))
        # a real game that ends with a result is rejected by the checksum
        self.assertIsNone(main.decode_filename('1.e4_e5_2.Nf3_Nc6_3.Bb5_a6_1-0'))
        self.assertIsNone(main.decode_filename('hello world'))


if __name__ == '__main__':
    unittest.main()
