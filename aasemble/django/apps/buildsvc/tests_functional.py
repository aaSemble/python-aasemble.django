import os
import re

from django.test.utils import override_settings, skipIf

from aasemble.django.apps.buildsvc.tasks import poll_one

from aasemble.django.apps.buildsvc.test.aaSemblepage import BuildPage, ExternalDependenciesPage, LogoutPage, MirrorSetPage, MirrorsPage, OverviewPage, ProfilePage, SnapshotPage, SourcePage
from aasemble.django.apps.buildsvc.test.basewebobject import WebObject

from aasemble.django.tests import create_session_cookie

# import selenium.common.exceptions as Exceptions


@skipIf(os.environ.get('SKIP_SELENIUM_TESTS', '') == '1',
        'Skipping Selenium based test, because SKIP_SELENIUM_TESTS=1')
class RepositoryFunctionalTests(WebObject):
    fixtures = ['complete.json']

    def test_user_signs_up_for_signup(self):
        self.driver.get('%s%s' % (self.live_server_url, '/accounts/signup/'))
        username_input = self.driver.find_element_by_id('id_email')
        username_input.send_keys('newuser@linux2go.dk')
        password1_input = self.driver.find_element_by_id('id_password1')
        password1_input.send_keys('secret')
        password2_input = self.driver.find_element_by_id('id_password2')
        password2_input.send_keys('secret')
        signup_form = self.driver.find_element_by_id('signup_form')
        signup_form.submit()
        page_header = self.driver.find_element_by_class_name('page-header')
        text_found = re.search(r'Dashboard', page_header.text)
        self.assertNotEqual(text_found, None)

    def test_secured_pages_open_after_login(self):
        session_cookie = create_session_cookie(username='test@email.com', password='top_secret')
        self.driver.get(self.live_server_url)
        self.driver.add_cookie(session_cookie)

        # test whether sources page opens after user logs in
        self.driver.get('%s%s' % (self.live_server_url, '/buildsvc/sources/'))
        page_header = self.driver.find_element_by_class_name('page-header')
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
        sourcePage = SourcePage(self.driver)
        self.create_login_session('brandon')
        # test whether sources page opens after user logs in
        sourcePage.driver.get(self.live_server_url)
        sourcePage.sources_button.click()
        git_url = "https://github.com/aaSemble/python-aasemble.django.git"
        sourcePage.create_new_package_source(git_url=git_url, branch='master', series='brandon/aasemble')
        self.assertEqual(sourcePage.verify_package_source(git_url=git_url), True, 'Package not created')
        sourcePage.delete_package_source()
        self.assertEqual(sourcePage.verify_package_source(git_url=git_url), False, 'Package not deleted')

    def test_profile_button(self):
        '''This test verifies the "Profile" button.
            1. Create a session cookie for given user. We are using a existing
               # user 'brandon' which is already added as fixture.
            2. Press 'Profile' button.
            3. Verify page by username'''
        self.create_login_session('brandon')
        profilePage = ProfilePage(self.driver)
        # test whether sources page opens after user logs in
        profilePage.driver.get(self.live_server_url)
        profilePage.profile_button.click()
        self.assertEqual(profilePage.verify_profile_page('brandon'), True, "Profile Name not verified")

    def test_create_delete_mirror(self):
        ''' This tests validates if non public mirror is created'''
        url = self.live_server_url + '/apt/brandon/brandon'
        self.create_login_session('brandon')
        mirrorsPage = MirrorsPage(self.driver)
        mirrorsPage.driver.get(self.live_server_url)
        mirrorsPage.mirror_button.click()
        mirrorsPage.new_mirror_button.click()
        mirrorsPage.url_field.send_keys(url)
        mirrorsPage.series_field.send_keys('brandon/aasemble')
        mirrorsPage.component_field.send_keys('aasemble')
        mirrorsPage.submit_button.click()
        self.assertTrue(mirrorsPage.verify_mirror_visible_by_url(url))
        self.assertTrue(mirrorsPage.verify_mirror_private())
        mirrorsPage.click_on_mirror_uuid(url)
        # Verfies if URL value  is visible after clicking on uuid
        self.assertTrue(mirrorsPage.verify_mirror_value_visible(url))
        mirrorsPage.delete_button.click()
        self.assertFalse(mirrorsPage.verify_mirror_visible_by_url(url))

    @override_settings(CELERY_ALWAYS_EAGER=True)
    # This tests needs celery so overriding the settings
    def test_build_packages(self):
        '''This test perform a package addtion and check whether a build
         started for the same.
         1. Create a session cookie for given user. We are using a existing
               # user 'brandon' which is already added as fixture.
         2. Try to create a package.
         3. Poll the task for package creation. Polling should start the build
         4. Verify that Building started and it is visible via GUI'''
        sourcePage = SourcePage(self.driver)
        self.create_login_session('brandon')
        # test whether sources page opens after user logs in
        sourcePage.driver.get(self.live_server_url)
        sourcePage.sources_button.click()
        git_url = "https://github.com/aaSemble/python-aasemble.django.git"
        sourcePage.create_new_package_source(git_url=git_url, branch='master', series='brandon/aasemble')
        self.assertEqual(sourcePage.verify_package_source(git_url=git_url), True, 'Package not created')
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
            buildPage = BuildPage(self.driver)
            buildPage.driver.get(self.live_server_url)
            buildPage.build_button.click()
            self.assertEqual(buildPage.verify_build_displayed(packageName='python-aasemble.django.git'), True, 'Build not started')

    def test_overview_button(self):
        '''This test performs the test for overview button
          1. Create a session cookie for given user. We are using a existing
               # user 'brandon' which is already added as fixture.
          2. Press 'Overview' button.
          3. Verify whether 'Dashboard' came.'''
        self.create_login_session('brandon')
        overviewPage = OverviewPage(self.driver)
        # test whether sources page opens after user logs in
        overviewPage.driver.get(self.live_server_url)
        overviewPage.overview_button.click()
        pageHeader = overviewPage.get_page_header_value()
        self.assertEqual(pageHeader.text, "Dashboard", "Dashboard didn't showed up")

    def test_logout_button(self):
        '''This test perform a logout from given seesion
        # 1. Create a session cookie for given user. We are using a existing
               # user 'brandon' which is already added as fixture.
        # 2. Press logout.
        # 3. Verify that we came to login page.'''
        self.create_login_session('brandon')
        logoutPage = LogoutPage(self.driver)
        # test whether sources page opens after user logs in
        logoutPage.driver.get(self.live_server_url)
        logoutPage.logout_button.click()
        self.assertEqual(logoutPage.verify_login_page(), True, "Logout didn't work")

    def test_mirror_set(self):
        '''This test verifies the working of mirror set'''
        self.create_login_session('brandon')
        mirrorsSet = MirrorSetPage(self.driver)
        mirrorsSet.driver.get(self.live_server_url)
        mirrorsSet.mirror_set_button.click()
        mirrorsSet.new_submit_button.click()
        mirrorsSet.create_mirror_set(name='mySet')

    def test_snapshot_operations(self):
        '''This test verifies the operations snapshot.
         Steps:
         1. Create new mirror and mirrorset for user 'brandon'.
         2. "View snapshot" for its first (only in this case) mirrorset.
         3. Save the number of lines in tables.
         4. Create a snaphot
         5. Repeat step 3.
         6. Difference should be exaclty one.'''
        self.test_mirror_set()
        self.create_login_session('brandon')
        mirrorsSet = MirrorSetPage(self.driver)
        mirrorsSet.driver.get(self.live_server_url)
        mirrorsSet.mirror_set_button.click()
        viewButton = mirrorsSet.view_snapshot('mySet')
        viewButton.click()
        noOfExistingSnapsPrevious = mirrorsSet.countSnapshots()
        mirrorsSet.new_submit_button.click()
        noOfExistingSnapsAfter = mirrorsSet.countSnapshots()
        self.assertEqual(noOfExistingSnapsAfter - noOfExistingSnapsPrevious, 1, "SnapShot didn't created")

    def test_snapshot_view(self):
        '''This test verifies the operations snapshot.
         ' Steps:
         1. Create new mirror and mirrorset for user 'brandon'.
         2. "View snapshot" for its first (only in this case) mirrorset.
         3. Create a snaphot
         4. Save the snpashot uuid
         5. open Snapshot page
         6. Verify that snapshot is visible with same uuid.'''
        self.test_snapshot_operations()
        self.create_login_session('brandon')
        mirrorsSet = MirrorSetPage(self.driver)
        mirrorsSet.driver.get(self.live_server_url)
        mirrorsSet.mirror_set_button.click()
        uuid = mirrorsSet.getLastestSnapShot_uuid('mySet')
        uuid = uuid.text
        snapshotPage = SnapshotPage(self.driver)
        snapshotPage.driver.get(self.live_server_url)
        snapshotPage.snapshot_button.click()
        uuids = snapshotPage.snapshotDetailsByMirrorSet('mySet')
        self.assertTrue(uuid in uuids, "Snapshot didn't showed up")

    def test_mirror_set_delete(self):
        ''' This test verifies the mirror-set
        creation and deletion
        Steps:
        1. Create mirror and mirror-set.
        2. Go to mirror-set page.
        3. Delete mirror set.'''
        self.test_mirror_set()
        self.create_login_session('brandon')
        mirrorsSet = MirrorSetPage(self.driver)
        mirrorsSet.driver.get(self.live_server_url)
        mirrorsSet.mirror_set_button.click()
        mirrorsSet.deleteMirrorSet('mySet')

    def test_snapshot_tags(self):
        '''This tests verifies the tag addtion/deletion and
        modification on snapshot.
        Steps:
         1. Create Mirror, Mirror-set and a snapshot
         2. Save the snapshot uuid.
         3. Create a new tag on snapshot.
         4. Edit the snapshot tag.
         5. Delete a snapshot tag.
         6. Create a new snapshot-tag '''
        self.test_mirror_set()
        self.create_login_session('brandon')
        mirrorsSet = MirrorSetPage(self.driver)
        mirrorsSet.driver.get(self.live_server_url)
        mirrorsSet.mirror_set_button.click()
        viewButton = mirrorsSet.view_snapshot('mySet')
        viewButton.click()
        mirrorsSet.new_submit_button.click()
        mirrorsSet.mirror_set_button.click()
        uuid = mirrorsSet.getLastestSnapShot_uuid("mySet").text
        snapshot = SnapshotPage(self.driver)
        snapshot.snapshot_button.click()
        # create new tag
        snapshot.create_new_snapshot_tag(snapshotuuid=uuid, tag='testtag')
        self.assertTrue(snapshot.verify_tag_present(snapshotuuid=uuid, tag='testtag'), "Tag not added")
        # edit snapshot tag
        snapshot.edit_snapshot_tag(snapshotuuid=uuid, tag='testtagedited', oldtag='testtag')
        self.assertTrue(snapshot.verify_tag_present(snapshotuuid=uuid, tag='testtagedited'), "Tag not edited")
        # deleted snapshot tag
        snapshot.deleted_snapshot_tag(snapshotuuid=uuid, tag='testtagedited')
        self.assertFalse(snapshot.verify_tag_present(snapshotuuid=uuid, tag='testtagedited'), "Tag not deleted")
        # add one more tag on same snapshot
        snapshot.create_new_snapshot_tag(snapshotuuid=uuid, tag='testsecondtag')
        self.assertTrue(snapshot.verify_tag_present(snapshotuuid=uuid, tag='testsecondtag'), "Tag not added")

    def test_external_dependencies(self):
        '''This test verifies the working of external dependency feature.
          Steps:
          1.  Create a login session
          2. Add a external dependency
          3. delete a external dependency'''
        self.create_login_session('brandon')
        externalDependency = ExternalDependenciesPage(self.driver)
        externalDependency.driver.get(self.live_server_url)
        externalDependency.externalDependencies_button.click()
        url = 'https://github.com/aaSemble/python-aasemble.django'
        series = 'user/aasemble'
        component = 'main'
        ownSeries = 'brandon/aasemble'
        key = 'justForTesting'
        externalDependency.createExternalDependency(url, series, component, ownSeries, key)
        self.assertTrue(externalDependency.verify_external_dependencies(url, series, component), 'External Dependency not added')
        externalDependency.delete_external_dependency()
        self.assertFalse(externalDependency.verify_external_dependencies(url, series, component), 'External Dependency not deleted')
