import os
import re

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test.utils import override_settings, skipIf

import selenium.common.exceptions as Exceptions

from selenium.webdriver.common import by
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.ui import Select

from aasemble.django.apps.buildsvc.tasks import poll_one

from aasemble.django.tests import create_session_cookie, create_session_for_given_user


@skipIf(os.environ.get('SKIP_SELENIUM_TESTS', '') == '1',
        'Skipping Selenium based test, because SKIP_SELENIUM_TESTS=1')
class RepositoryFunctionalTests(StaticLiveServerTestCase):
    fixtures = ['complete.json']

    @classmethod
    def setUpClass(cls):
        super(RepositoryFunctionalTests, cls).setUpClass()
        cls.selenium = WebDriver()
        cls.selenium.maximize_window()

    @classmethod
    def tearDownClass(cls):
        cls.selenium.quit()
        super(RepositoryFunctionalTests, cls).tearDownClass()

    def test_user_signs_up_for_signup(self):
        self.selenium.get('%s%s' % (self.live_server_url, '/accounts/signup/'))
        username_input = self.selenium.find_element_by_id('id_email')
        username_input.send_keys('newuser@linux2go.dk')
        password1_input = self.selenium.find_element_by_id('id_password1')
        password1_input.send_keys('secret')
        password2_input = self.selenium.find_element_by_id('id_password2')
        password2_input.send_keys('secret')
        signup_form = self.selenium.find_element_by_id('signup_form')
        signup_form.submit()
        page_header = self.selenium.find_element_by_class_name('page-header')
        text_found = re.search(r'Dashboard', page_header.text)
        self.assertNotEqual(text_found, None)

    def test_secured_pages_open_after_login(self):
        session_cookie = create_session_cookie(username='test@email.com', password='top_secret')
        self.selenium.get(self.live_server_url)
        self.selenium.add_cookie(session_cookie)

        # test whether sources page opens after user logs in
        self.selenium.get('%s%s' % (self.live_server_url, '/buildsvc/sources/'))
        page_header = self.selenium.find_element_by_class_name('page-header')
        text_found = re.search(r'Sources', page_header.text)
        self.assertNotEqual(text_found, None)

    def test_source_package(self):
        '''This test performs a basic package addition and deletion.
           This test consists of following steps:
           1. Create a session cookie for given user. We are using a existing
               user 'Dennis' which is already added as fixture.
           2. Try to create a package.
           3. Verify if the package has been created.
           4. Try to delete the package
           5. Verify if the package has been deleted'''
        self.create_login_session('brandon')
        # test whether sources page opens after user logs in
        self.selenium.get('%s%s' % (self.live_server_url, '/buildsvc/sources/'))
        self.selenium.set_window_size(1024, 768)
        self.sources_button.click()
        git_url = "https://github.com/aaSemble/python-aasemble.django.git"
        self.create_new_package_source(git_url=git_url, branch='master', series='brandon/aasemble')
        self.assertEqual(self.verify_package_source(git_url=git_url), True, 'Package not created')
        self.delete_package_source()
        self.assertEqual(self.verify_package_source(git_url=git_url), False, 'Package not deleted')

    def test_profile_button(self):
        '''This test verifies the "Profile" button.
        1. Create a session cookie for given user. We are using a existing
               user 'brandon' which is already added as fixture.
        2. Press 'Profile' button.
        3. Verify page by username'''
        self.create_login_session('brandon')
        # test whether sources page opens after user logs in
        self.selenium.get('%s%s' % (self.live_server_url, '/buildsvc/sources/'))
        self.selenium.set_window_size(1024, 768)
        self.profile_button.click()
        self.assertEqual(self.verify_profile_page('brandon'), True, "Profile Name not verified")

    def test_new_mirrors(self):
        ''' This tests validates if non public mirror is created'''
        new_mirror_button = (by.By.LINK_TEXT, 'New')
        self.create_login_session('brandon')
        self.selenium.get('%s%s' % (self.live_server_url, '/mirrorsvc/mirrors/'))
        self.selenium.set_window_size(1024, 768)
        self.assertTrue(self._is_element_visible(new_mirror_button), "Mirror New Button is not Visible")
        self.selenium.find_element(*new_mirror_button).click()
        self.selenium.find_element(by.By.ID, 'id_url').send_keys('%s%s' % (self.live_server_url, '/apt/brandon/brandon'))
        self.selenium.find_element(by.By.ID, 'id_series').send_keys('brandon/aasemble')
        self.selenium.find_element(by.By.ID, 'id_components').send_keys('aasemble')
        self.selenium.find_element(by.By.XPATH, './/button[@type="submit" and contains(.,"Submit")]').click()
        self.assertTrue(self._is_element_visible((by.By.LINK_TEXT, '%s%s' % (self.live_server_url, '/apt/brandon/brandon'))))
        # Test if public flag is false
        self.assertTrue(self._is_element_visible((by.By.XPATH, ".//table/tbody/tr[1]/td[5][contains(text(), False)]")))

    def _is_element_visible(self, locator):
        try:
            return self.selenium.find_element(*locator).is_displayed()
        except (Exceptions.NoSuchElementException,
                Exceptions.ElementNotVisibleException):
            return False

    def create_login_session(self, username):
        session_cookie = create_session_for_given_user(username)
        self.selenium.get(self.live_server_url)
        self.selenium.add_cookie(session_cookie)

    def verify_profile_page(self, username):
        try:
            self.selenium.find_element(by.By.XPATH, "//dl[@class='dl-horizontal']/dd[contains(text(), %s)]" % username)
        except:
            return False
        else:
            return True

    @property
    def profile_button(self):
        '''Finds package profile button'''
        return self.selenium.find_element(by.By.LINK_TEXT, 'Profile')

    @override_settings(CELERY_ALWAYS_EAGER=True)
    # This tests needs celery so overriding the settings
    def test_build_packages(self):
        '''This test perform a package addtion and check whether a build
        started for the same.
        1. Create a session cookie for given user. We are using a existing
               user 'brandon' which is already added as fixture.
        2. Try to create a package.
        3. Poll the task for package creation. Polling should start the build
        4. Verify that Building started and it is visible via GUI'''
        self.create_login_session('brandon')
        # test whether sources page opens after user logs in
        self.selenium.get('%s%s' % (self.live_server_url, '/buildsvc/sources/'))
        self.selenium.set_window_size(1024, 768)
        self.sources_button.click()
        git_url = "https://github.com/aaSemble/python-aasemble.django.git"
        self.create_new_package_source(git_url=git_url, branch='master', series='brandon/aasemble')
        from .models import PackageSource
        # Only one package is added with this url
        P = PackageSource.objects.filter(git_url=git_url)[0]
        try:
            poll_one(P.id)
        except:
            # Marking Pass even if we got some exception during package build.
            # Our verification is limited to UI inteface. Form UI, It should
            # be visible (even if it has just started)
            pass
        finally:
            self.selenium.get('%s%s' % (self.live_server_url, '/buildsvc/sources/'))
            self.build_button.click()
            self.assertEqual(self.verify_build_displayed(packageName='python-aasemble.django.git'), True, 'Build not started')

    def test_overview_button(self):
        '''This test performs the test for overview button
        1. Create a session cookie for given user. We are using a existing
               user 'brandon' which is already added as fixture.
        2. Press 'Overview' button.
        3. Verify whether 'Dashboard' came.'''
        self.create_login_session('brandon')
        # test whether sources page opens after user logs in
        self.selenium.get('%s%s' % (self.live_server_url, '/buildsvc/sources/'))
        self.selenium.set_window_size(1024, 768)
        self.overview_button.click()
        pageHeader = self.get_page_header_value()
        self.assertEqual(pageHeader.text, "Dashboard", "Dashboard didn't showed up")

    def get_page_header_value(self):
        '''Find page header's value'''
        return self.selenium.find_element(by.By.CLASS_NAME, "page-header")

    @property
    def overview_button(self):
        '''Finds overview button'''
        return self.selenium.find_element(by.By.XPATH, "//a[@href='/' and contains(text(), 'Overview')]")

    def test_logout_button(self):
        '''This test perform a logout from given seesion
        1. Create a session cookie for given user. We are using a existing
               user 'brandon' which is already added as fixture.
        2. Press logout.
        3. Verify that we came to login page.'''
        self.create_login_session('brandon')
        # test whether sources page opens after user logs in
        self.selenium.get('%s%s' % (self.live_server_url, '/buildsvc/sources/'))
        self.selenium.set_window_size(1024, 768)
        self.logout_button.click()
        self.assertEqual(self.verify_login_page(), True, "Logout didn't work")

    @property
    def logout_button(self):
        '''Finds package source button'''
        return self.selenium.find_element(by.By.LINK_TEXT, 'Log out')

    def verify_login_page(self):
        try:
            self.selenium.find_element(by.By.XPATH, "//*[@id='login_button']")
        except:
            return False
        else:
            return True

    def test_mirror_set(self):
        '''This test verifies the working of mirror set'''
        self.create_login_session('brandon')
        # test whether sources page opens after user logs in
        self.selenium.get(self.live_server_url)
        self.selenium.set_window_size(1024, 768)
        self.mirror_set_button.click()
        self.new_submit_button.click()
        self.selenium.find_element(by.By.ID, 'id_name').send_keys('mySet')
        # Selecting all options
        options = self.selenium.find_element(by.By.ID, 'id_mirrors')
        for option in options.find_elements(by.By.TAG_NAME, 'option'):
            option.click()
        self.new_submit_button.click()

    @property
    def mirror_set_button(self):
        '''Finds the mirror set button'''
        return self.selenium.find_element(by.By.LINK_TEXT, 'Mirror-Sets')

    def create_new_package_source(self, git_url, branch, series):
        '''This is the helper method to create
        a package. This consists of following steps:
        1. Click on new button.
        2. Enter values like git_url, branch and series.
        3. Click submit.
        INPUT: git_url, branch and series (All string type)'''
        self.new_submit_button.click()
        self.git_url.send_keys(git_url)
        self.branch.send_keys(branch)
        self.select_from_dropdown_menu(series)
        self.new_submit_button.submit()

    def select_from_dropdown_menu(self, series):
        '''This is the helper method to select a given
        series from drop-down box
        INPUT: series (string type)'''
        mySelect = Select(self.selenium.find_element_by_id("id_series"))
        mySelect.select_by_visible_text(series)

    def delete_package_source(self):
        '''This is the helper method to delete a package.
        This consists of followwinng steps:
        1. Click on source button.
        2. Click on edit button for package.
        3. click on delete button.'''
        self.sources_button.click()
        self.package_edit_button.click()
        self.delete_button.click()

    def verify_package_source(self, git_url):
        '''This is the helper method to verify whether
        a package exist or not on basis on url.
        INPUT: git_url (string type)
        RETURN: TRUE if package found and FALSE on otherwise case'''
        self.sources_button.click()
        # It will report an exception if element not found
        try:
            self.selenium.find_element(by.By.LINK_TEXT, git_url)
        except:
            return False
        else:
            return True

    @property
    def new_submit_button(self):
        '''Finds NEW and Submit button. Both buttons have same class name
        and live in diffrent views thus giving us opportunity of code reuse'''
        return self.selenium.find_element(by.By.CSS_SELECTOR, '.btn.btn-primary')

    @property
    def git_url(self):
        '''Finds box for entering git url'''
        return self.selenium.find_element(by.By.ID, 'id_git_url')

    @property
    def branch(self):
        '''Finds box for entering branch name'''
        return self.selenium.find_element(by.By.ID, 'id_branch')

    @property
    def package_edit_button(self):
        '''Finds package edit button.
        NOTE: Only one package is expected at once'''
        return self.selenium.find_element(by.By.CSS_SELECTOR, '.glyphicon.glyphicon-pencil')

    @property
    def delete_button(self):
        '''Finds package delete button'''
        return self.selenium.find_element(by.By.CSS_SELECTOR, '.btn.btn-danger')

    @property
    def sources_button(self):
        '''Finds package source button'''
        return self.selenium.find_element(by.By.LINK_TEXT, 'Sources')

    @property
    def build_button(self):
        '''Finds package source button'''
        return self.selenium.find_element(by.By.LINK_TEXT, 'Builds')

    def verify_build_displayed(self, packageName):
        '''Verify whether the Build has started by package name'''
        try:
            self.selenium.find_element(by.By.CSS_SELECTOR, "a[href*='%s']" % packageName)
        except:
            return False
        else:
            return True
