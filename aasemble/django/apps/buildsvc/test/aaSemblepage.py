import selenium.common.exceptions as Exceptions

from selenium.webdriver.common import by
from selenium.webdriver.support.ui import Select


class BasePage(object):
    '''This is the base class to provide all the common
    functionality of overcast aasemble page. for example
    We might need page-header for any view of this site.
    so it can be written in base class'''

    def __init__(self, driver):
        """Constructor."""
        self.driver = driver

    def get_page_header_value(self):
        '''Find page header's value'''
        return self.driver.find_element(by.By.CLASS_NAME, "page-header")

    @property
    def new_submit_button(self):
        '''Finds NEW and Submit button. Both buttons have same class name
        and live in diffrent views thus giving us opportunity of code reuse'''
        return self.driver.find_element(by.By.CSS_SELECTOR, '.btn.btn-primary')

    @property
    def delete_button(self):
        '''Finds package delete button'''
        return self.driver.find_element(by.By.CSS_SELECTOR, '.btn.btn-danger')

    def _is_element_visible(self, locator):
        try:
            return self.driver.find_element(*locator).is_displayed()
        except (Exceptions.NoSuchElementException,
                Exceptions.ElementNotVisibleException):
            return False

    def _is_value_displayed(self, locator, value):
        webelement = self.driver.find_element(*locator)
        element_attribute_value = webelement.get_attribute('value')
        return element_attribute_value == value

    '''This method extracts web table row based on input text
       data to compare and verify as per test case'''
    def fetch_table_row_details(self, findtext, table_locator):
        # get all of the rows in the table
        table_webelement = self.driver.find_element(*table_locator)
        rows = table_webelement.find_elements(by.By.TAG_NAME, "tr")
        for row in rows:
            # Get the columns
            col = row.find_elements(by.By.TAG_NAME, "td")
            for s in col:
                if s.text == findtext:
                    return row


class SourcePage(BasePage):
    '''This class is to perform all operations on sourcePackage
    view of site'''

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
        mySelect = Select(self.driver.find_element_by_id("id_series"))
        mySelect.select_by_visible_text(series)

    def verify_package_source(self, git_url):
        '''This is the helper method to verify whether
        a package exist or not on basis on url.
        INPUT: git_url (string type)
        RETURN: TRUE if package found and FALSE on otherwise case'''
        self.sources_button.click()
        # It will report an exception if element not found
        try:
            self.driver.find_element(by.By.LINK_TEXT, git_url)
        except:
            return False
        else:
            return True

    def delete_package_source(self):
        '''This is the helper method to delete a package.
        This consists of followwinng steps:
        1. Click on source button.
        2. Click on edit button for package.
        3. click on delete button.'''
        self.sources_button.click()
        self.package_edit_button.click()
        self.delete_button.click()

    @property
    def package_edit_button(self):
        '''Finds package edit button.
        NOTE: Only one package is expected at once'''
        return self.driver.find_element(by.By.CSS_SELECTOR, '.glyphicon.glyphicon-pencil')

    @property
    def sources_button(self):
        '''Finds package source button'''
        return self.driver.find_element(by.By.LINK_TEXT, 'Sources')

    @property
    def git_url(self):
        '''Finds box for entering git url'''
        return self.driver.find_element(by.By.ID, 'id_git_url')

    @property
    def branch(self):
        '''Finds box for entering branch name'''
        return self.driver.find_element(by.By.ID, 'id_branch')


class ProfilePage(BasePage):
    '''This class is to perform all operations on Profile
    view of site'''

    @property
    def profile_button(self):
        '''Finds package profile button'''
        return self.driver.find_element(by.By.LINK_TEXT, 'Profile')

    def verify_profile_page(self, username):
        try:
            self.driver.find_element(by.By.XPATH, "//dl[@class='dl-horizontal']/dd[contains(text(), %s)]" % username)
        except:
            return False
        else:
            return True


class LogoutPage(BasePage):
    '''This class is to perform all operations on Profile
    view of site'''

    @property
    def logout_button(self):
        '''Finds package source button'''
        return self.driver.find_element(by.By.LINK_TEXT, 'Log out')

    def verify_login_page(self):
        try:
            self.driver.find_element(by.By.XPATH, "//*[@id='login_button']")
        except:
            return False
        else:
            return True


class OverviewPage(BasePage):
    '''This class is to perform all operations on Profile
    view of site'''

    @property
    def overview_button(self):
        '''Finds overview button'''
        return self.driver.find_element(by.By.XPATH, "//a[@href='/' and contains(text(), 'Overview')]")


class BuildPage(BasePage):

    @property
    def build_button(self):
        '''Finds package source button'''
        return self.driver.find_element(by.By.LINK_TEXT, 'Builds')

    def verify_build_displayed(self, packageName):
        '''Verify whether the Build has started by package name'''
        try:
            self.driver.find_element(by.By.CSS_SELECTOR, "a[href*='%s']" % packageName)
        except:
            return False
        else:
            return True


class MirrorsPage(BasePage):
    _table_id_locator = (by.By.CSS_SELECTOR, '.table.table-striped')

    @property
    def mirror_button(self):
        '''Finds package source button'''
        return self.driver.find_element(by.By.LINK_TEXT, 'Mirrors')

    @property
    def new_mirror_button(self):
        '''Finds new mirrors button'''
        return self.driver.find_element(by.By.LINK_TEXT, 'New')

    @property
    def url_field(self):
        '''Finds url field'''
        return self.driver.find_element(by.By.ID, 'id_url')

    @property
    def series_field(self):
        '''Finds series filed'''
        return self.driver.find_element(by.By.ID, 'id_series')

    @property
    def component_field(self):
        '''Finds component field'''
        return self.driver.find_element(by.By.ID, 'id_components')

    @property
    def submit_button(self):
        '''Finds submit button'''
        return self.driver.find_element(by.By.XPATH, './/button[@type="submit" and contains(.,"Submit")]')

    def verify_mirror_visible_by_url(self, value):
        locator = (by.By.LINK_TEXT, value)
        return self._is_element_visible(locator)

    def verify_mirror_value_visible(self, value):
        locator = (by.By.NAME, "url")
        return self._is_value_displayed(locator, value)

    def verify_mirror_private(self):
        locator = (by.By.XPATH, ".//table/tbody/tr[1]/td[5][contains(text(), False)]")
        return self._is_element_visible(locator)

    def click_on_mirror_uuid(self, url_id):
        row = self.fetch_table_row_details(url_id, self._table_id_locator)
        columns = row.find_elements(by.By.TAG_NAME, "td")
        # first columns corresponds to uuid
        (columns[0]).click()


class MirrorSetPage(BasePage):

    @property
    def mirror_set_button(self):
        '''Finds the mirror set button'''
        return self.driver.find_element(by.By.LINK_TEXT, 'Mirror-Sets')

    def create_mirror_set(self, name):
        '''Create new mirror set with given name'''
        self.driver.find_element(by.By.ID, 'id_name').send_keys(name)
        # Selecting all options
        options = self.driver.find_element(by.By.ID, 'id_mirrors')
        for option in options.find_elements(by.By.TAG_NAME, 'option'):
            option.click()
        self.new_submit_button.click()

    def view_snapshot(self, mirrorSetName):
        '''View snapshot in first row'''
        elements = self.driver.find_elements(by.By.XPATH, '//table[@class="table table-striped"]//tr')
        for ele in elements:
            if ele.find_element(by.By.XPATH, '//td[2]').text == mirrorSetName:
                return ele.find_element(by.By.XPATH, "//a[contains(text(), 'View snapshots')]")

    def countSnapshots(self):
        existingSnaps = self.driver.find_elements(by.By.XPATH, "//table[@class='table table-striped']//tr")
        noOfExistingSnaps = len(existingSnaps)
        return noOfExistingSnaps

    def getMirrorSetID_button(self, mirrorSetName):
        elements = self.driver.find_elements(by.By.XPATH, '//table[@class="table table-striped"]//tr')
        for ele in elements:
            if ele.find_element(by.By.XPATH, '//td[2]').text == mirrorSetName:
                return ele.find_element(by.By.XPATH, '//td[1]')

    def deleteMirrorSet(self, mirrorSetName):
        '''This method deletes the mirror-set'''
        mirrorLink = self.getMirrorSetID_button(mirrorSetName)
        mirrorLink.click()
        options = self.driver.find_element(by.By.ID, 'id_mirrors')
        for option in options.find_elements(by.By.TAG_NAME, 'option'):
            option.click()
        self.delete_button.click()

    def getLastestSnapShot_uuid(self, mirrorSetName):
        '''Returns the snap in the list for given Mirror-Sets'''
        viewButton = self.view_snapshot(mirrorSetName)
        viewButton.click()
        existingSnaps = self.driver.find_elements(by.By.XPATH, '//tr')
        lastSnap = existingSnaps[-1]
        return lastSnap.find_element(by.By.XPATH, '//td[1]')


class SnapshotPage(BasePage):

    @property
    def snapshot_button(self):
        '''Finds the snapshot button'''
        return self.driver.find_element(by.By.LINK_TEXT, 'Snapshots')

    def snapshotDetailsByMirrorSet(self, mirrorSetName):
        '''Gives the snapshot list for given mirror-set'''
        snapshotList = []
        elements = self.driver.find_elements(by.By.XPATH, '//table[@class="table table-striped"]//tr')
        for ele in elements:
            if ele.find_element(by.By.XPATH, '//td[2]').text == mirrorSetName:
                uuid = ele.find_element(by.By.XPATH, '//td[3]').text
                snapshotList.append(uuid)
        return snapshotList

    def getAllTagsBySnapshot(self, snapshotuuid):
        elements = self.driver.find_elements(by.By.XPATH, '//table[@class="table table-striped"]//tr')
        for ele in elements:
            if ele.find_element(by.By.XPATH, '//td[3]').text == snapshotuuid:
                snaps = ele.find_elements(by.By.XPATH, '//td[5]')
        return snaps

    def create_new_snapshot_tag(self, snapshotuuid, tag):
        elements = self.driver.find_elements(by.By.XPATH, '//table[@class="table table-striped"]//tr')
        for ele in elements[1:]:
            if ele.find_element(by.By.XPATH, '//td[3]').text == snapshotuuid:
                ele.find_element(by.By.XPATH, '//td[6]').click()
                self.driver.find_element(by.By.ID, 'id_tag').send_keys(tag)
                self.new_submit_button.submit()

    def verify_tag_present(self, snapshotuuid, tag):
        snaptags = self.getAllTagsBySnapshot(snapshotuuid)
        for snaptag in snaptags:
            if tag == snaptag.text:
                return True
        return False

    def edit_snapshot_tag(self, snapshotuuid, tag, oldtag):
        snaptags = self.getAllTagsBySnapshot(snapshotuuid)
        for snaptag in snaptags:
            if oldtag == snaptag.text:
                self.driver.find_element(by.By.LINK_TEXT, oldtag).click()
                self.driver.find_element(by.By.ID, 'id_tag').clear()
                self.driver.find_element(by.By.ID, 'id_tag').send_keys(tag)
                self.new_submit_button.click()

    def deleted_snapshot_tag(self, snapshotuuid, tag):
        snaptags = self.getAllTagsBySnapshot(snapshotuuid)
        for snaptag in snaptags:
            if tag == snaptag.text:
                self.driver.find_element(by.By.LINK_TEXT, tag).click()
                self.delete_button.click()


class ExternalDependenciesPage(BasePage):

    @property
    def externalDependencies_button(self):
        '''Finds the external dependencies button'''
        return self.driver.find_element(by.By.LINK_TEXT, 'External Dependencies')

    @property
    def url_field(self):
        '''Url button'''
        return self.driver.find_element(by.By.ID, 'id_url')

    @property
    def series_field(self):
        '''Series field button'''
        return self.driver.find_element(by.By.ID, 'id_series')

    @property
    def components_field(self):
        '''Components field button'''
        return self.driver.find_element(by.By.ID, 'id_components')

    @property
    def key_field(self):
        '''Key field'''
        return self.driver.find_element(by.By.ID, 'id_key')

    @property
    def externalDependencie_edit_button(self):
        '''Finds package edit button.
        NOTE: Only one package is expected at once'''
        return self.driver.find_element(by.By.CSS_SELECTOR, '.glyphicon.glyphicon-pencil')

    def selectOwnSeries_field_dropdown(self, series):
        '''Own series field'''
        mySelect = Select(self.driver.find_element(by.By.ID, 'id_own_series'))
        mySelect.select_by_visible_text(series)

    def createExternalDependency(self, url, series, component, ownSeries, key):
        self.new_submit_button.click()
        self.url_field.send_keys(url)
        self.series_field.send_keys(series)
        self.components_field.send_keys(component)
        self.selectOwnSeries_field_dropdown(ownSeries)
        self.key_field.send_keys(key)
        self.new_submit_button.submit()

    def delete_external_dependency(self):
        self.externalDependencie_edit_button.click()
        self.delete_button.click()

    def verify_external_dependencies(self, git_url, series, component):
        '''This is the helper method to verify whether
        a package exist or not on basis on url.
        INPUT: git_url, series, component
        RETURN: TRUE if package found and FALSE on otherwise case'''
        self.externalDependencies_button.click()
        vertficationString = "deb %s %s %s" % (git_url, series, component)
        try:
            coloum = self.driver.find_element(by.By.XPATH, "//table[@class='table table-striped']/tbody/tr/td[3]").text
            if coloum == vertficationString:
                return True
            else:
                return False
        except:
            return False
