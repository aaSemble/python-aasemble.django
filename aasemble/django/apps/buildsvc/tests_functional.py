import os
import re

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test.utils import skipIf

from selenium.webdriver.common import by
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.ui import Select

from aasemble.django.tests import create_session_for_given_user, create_session_cookie


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
           5. Verify if the package has been deleted
           6. Peform cleanup like delete user. repo etc that we have created.'''
        session_cookie = create_session_for_given_user(username='dennis')
        self.selenium.get(self.live_server_url)
        self.selenium.add_cookie(session_cookie)
        # test whether sources page opens after user logs in
        self.selenium.get('%s%s' % (self.live_server_url, '/buildsvc/sources/'))
        self.selenium.set_window_size(1024, 768)
        self.sources_button.click()
        git_url = "https://github.com/aaSemble/python-aasemble.django.git"
        self.create_new_package_source(git_url=git_url, branch='master', series='dennis/aasemble')
        self.assertEqual(self.verify_package_source(git_url=git_url), True, 'Package not created')
        self.delete_package_source(git_url=git_url)
        self.assertEqual(self.verify_package_source(git_url=git_url), False, 'Package not deleted')

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
