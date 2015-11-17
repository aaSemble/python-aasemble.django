import os
import re

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test.utils import skipIf
from selenium.webdriver.common.by import By
from selenium.webdriver.common import by
from selenium.webdriver.firefox.webdriver import WebDriver
from selenium.webdriver.support.ui import Select
from aasemble.django.tests import *


@skipIf(os.environ.get('SKIP_SELENIUM_TESTS', '') == '1',
        'Skipping Selenium based test, because SKIP_SELENIUM_TESTS=1')
class RepositoryFunctionalTests(StaticLiveServerTestCase):
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
		
    def test_source_package (self):
        session_cookie = create_session_cookie(username='myuser', password='123456')
        group = create_default_group(name='mygrp')
        self.assertEqual(group.name, 'mygrp')
        repo = create_default_repo(name='myrepo', username='myuser')
        self.assertEqual(repo.name, 'myrepo')
        series = create_series(name='myseries', reponame='myrepo')
        self.assertEqual(series.name, 'myseries')
        self.selenium.get(self.live_server_url)
        self.selenium.add_cookie(session_cookie)
        self.selenium.get('%s%s' % (self.live_server_url, '/buildsvc/sources/'))
        self.sources_button.click()
        git_url = "https://github.com/aaSemble/python-aasemble.django.git"
        self.create_new_package_source(git_url=git_url, branch='master', series='myrepo/myseries')
        self.verify_package_source(git_url=git_url)
        self.delete_package_source()
        #We will follow opposite order as that of creation
        delete_series(name='myseries')
        delete_repo(name='myrepo')
        delete_group(name='mygrp')
        delete_user(username='myuser')


    def create_new_package_source(self, git_url, branch, series):
        self.new_submit_button.click()
        self.git_url.send_keys(git_url)
        self.branch.send_keys(branch)
        self.select_from_dropdown_menu(series)
        self.new_submit_button.submit()

    def select_from_dropdown_menu(self, series):
        mySelect = Select(self.selenium.find_element_by_id("id_series"))
        mySelect.select_by_visible_text(series)

    def delete_package_source(self):
        self.sources_button.click()
        self.package_edit_button.click()
        self.delete_button.click()

    def verify_package_source(self, git_url):
        self.sources_button.click()
        #It will report an exception if element not found
        self.selenium.find_element(by.By.LINK_TEXT, git_url)

    @property
    def sources_button(self):
        return self.selenium.find_element(by.By.LINK_TEXT, 'Sources')

    @property
    def new_submit_button(self):
        return self.selenium.find_element(by.By.CSS_SELECTOR, '.btn.btn-primary')

    @property
    def git_url(self):
        return self.selenium.find_element(by.By.ID, 'id_git_url')

    @property
    def branch(self):
        return self.selenium.find_element(by.By.ID, 'id_branch')
    
    @property
    def package_edit_button(self):
        #It will find first element
        return self.selenium.find_element(by.By.CSS_SELECTOR, '.glyphicon.glyphicon-pencil')

    @property
    def delete_button(self):
        return self.selenium.find_element(by.By.CSS_SELECTOR, '.btn.btn-danger')

