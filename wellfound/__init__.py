import os
from .utils import *
from .companies import Companies
from .login import Login

import undetected_chromedriver as uc


class Wellfound(Companies, Login):
    def __init__(self, **kwargs):
        options = uc.ChromeOptions()
        options.add_argument("--start-maximized")
        options.add_argument(
            f"--user-data-dir={os.path.join(os.getcwd(), 'chrome-data')}"
        )

        self.driver = uc.Chrome(options=options, version_main=149)

        Companies.__init__(self, **kwargs)
        Login.__init__(self, self.driver)

    def __del__(self):
        if hasattr(self, "driver"):
            self.driver.quit()


__authors__ = ["jwc20"]
__source__ = "https://github.com/jwc20/wellfound_api"
