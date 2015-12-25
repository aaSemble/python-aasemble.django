from django.contrib.staticfiles.testing import StaticLiveServerTestCase

from selenium.webdriver.firefox.webdriver import WebDriver

from aasemble.django.tests import create_session_for_given_user


class WebObject(StaticLiveServerTestCase):
    """Base class for page objects."""

    @classmethod
    def setUpClass(self):
        super(WebObject, self).setUpClass()
        self.driver = WebDriver()
        self.driver.set_window_size(1024, 768)
        self.driver.maximize_window()
        self.driver.implicitly_wait(15)

    @classmethod
    def tearDownClass(self):
        self.driver.quit()
        super(WebObject, self).tearDownClass()

    def create_login_session(self, username):
        session_cookie = create_session_for_given_user(username)
        self.driver.get(self.live_server_url)
        self.driver.add_cookie(session_cookie)
