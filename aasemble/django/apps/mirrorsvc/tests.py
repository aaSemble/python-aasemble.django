from django.contrib.auth import models as auth_models
from django.test import TestCase

import mock

from .models import Mirror, MirrorSet, Snapshot, Tags


class SnapshotTestCase(TestCase):
    @mock.patch('aasemble.django.apps.mirrorsvc.tasks.perform_snapshot')
    def test_save_snapshot_triggers_snapshot(self, perform_snapshot):
        user = auth_models.User.objects.create(username='testuser')
        m = Mirror.objects.create(owner=user, url='http://example.com', series='trusty', components='main')
        ms = MirrorSet.objects.create(name='ms1', owner=user)
        ms.mirrors.add(m)
        s = Snapshot.objects.create(mirrorset=ms)
        Tags.objects.create(snapshot=s, tag='test')
        perform_snapshot.apply_async.assert_called_with((s.id,), countdown=5)

    @mock.patch('aasemble.django.apps.mirrorsvc.models.Snapshot.sync_dists')
    @mock.patch('aasemble.django.apps.mirrorsvc.models.Snapshot.symlink_pool')
    def test_perform_snapshot_task_calls_sync_and_symlink(self, sync_dists, symlink_pool):
        from .tasks import perform_snapshot
        user = auth_models.User.objects.create(username='testuser')
        m = Mirror.objects.create(owner=user, url='http://example.com', series='trusty', components='main')
        ms = MirrorSet.objects.create(name='ms1', owner=user)
        ms.mirrors.add(m)
        s = Snapshot.objects.create(mirrorset=ms)
        Tags.objects.create(snapshot=s, tag='test')
        perform_snapshot(s.id)
        sync_dists.assert_called_with()
        symlink_pool.assert_called_with()


class TaskTestCase(TestCase):
    @mock.patch('aasemble.django.apps.mirrorsvc.models.Mirror')
    def test_refresh_mirror(self, MirrorMock):
        from . import tasks
        tasks.refresh_mirror(1234)

        MirrorMock.objects.get.assert_called_with(id=1234)
        MirrorMock.objects.get.return_value.update_mirror.assert_called_with()

    @mock.patch('aasemble.django.apps.mirrorsvc.models.Snapshot')
    def test_perform_snapshot(self, SnapshotMock):
        from . import tasks
        tasks.perform_snapshot(1234)

        SnapshotMock.objects.get.assert_called_with(id=1234)
        SnapshotMock.objects.get.return_value.perform_snapshot.assert_called_with()
