import inspect
import os
import test.src

import src

PROJECT_DIR = os.path.dirname(inspect.getabsfile(src))
TEST_DIR = os.path.dirname(inspect.getabsfile(test.src))
KATCH_PATH = os.path.join(PROJECT_DIR, "..", "bin", "katch", "katch")
