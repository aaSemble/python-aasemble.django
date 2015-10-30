from celery import shared_task

@shared_task(ignore_result=True)
def refresh_mirror(mirror_id):
    from .models import Mirror
    ps = Mirror.objects.get(id=mirror_id)
    ps.update_mirror()


@shared_task(ignore_result=True)
def perform_snapshot(snapshot_id):
    from .models import Snapshot
    s = Snapshot.objects.get(id=snapshot_id)
    s.perform_snapshot()
