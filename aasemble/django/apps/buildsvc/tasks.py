from celery import shared_task


@shared_task(ignore_result=True)
def reprepro(repository_id, *args):
    from .models import Repository
    r = Repository.objects.get(id=repository_id)
    r._reprepro(*args)


@shared_task(ignore_result=True)
def build(package_source_id):
    from .models import PackageSource
    ps = PackageSource.objects.get(id=package_source_id)
    ps.build_real()


@shared_task(ignore_result=True)
def poll_one(package_source_id):
    from .models import PackageSource
    ps = PackageSource.objects.get(id=package_source_id)
    if ps.poll():
        ps.build()


@shared_task(ignore_result=True)
def poll_all():
    from .models import PackageSource
    for ps in PackageSource.objects.all():
        poll_one.delay(ps.id)
