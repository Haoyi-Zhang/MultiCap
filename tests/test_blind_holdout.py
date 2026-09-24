import importlib.util
import random
import unittest
from pathlib import Path

P=Path(__file__).resolve().parents[1]/"reviewer"/"blind_holdout.py"
spec=importlib.util.spec_from_file_location("blind_holdout",P)
m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
class BlindHoldoutTests(unittest.TestCase):
    def test_residual_fresh_trials(self): self.assertEqual(m.check_residual_trials(random.Random(m.SEED),20)['trials'],20)
    def test_integer_rank_exhaustive(self): self.assertEqual(m.check_integer_rank_exhaustive()['matrices'],256)
    def test_cache(self): self.assertEqual(m.check_cache()['instances'],16)
if __name__=='__main__': unittest.main()
