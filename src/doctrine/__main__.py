"""`python -m doctrine` runs the command line."""

import sys

from doctrine.adapters.cli.main import main

sys.exit(main())
