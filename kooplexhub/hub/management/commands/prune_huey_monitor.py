"""Django management command: hub/management/commands/prune_huey_monitor.py.

Prune finished Huey Monitor tasks, leaf-first, in bounded transactions.
Dry run is the default; --apply enables deletion.
"""
import logging
from datetime import timedelta

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Exists, OuterRef
from django.utils import timezone
from huey_monitor.models import SignalInfoModel, TaskModel

logger = logging.getLogger('kooplex.huey.diagnostics')


class Command(BaseCommand):
    help = 'Prune old, finished Huey Monitor tasks and their signals in small batches.'

    def add_arguments(self, parser):
        parser.add_argument('--days', type=int, default=30,
                            help='Retain task records updated within this many days (default: 30).')
        parser.add_argument('--batch-size', type=int, default=200,
                            help='Maximum number of tasks in each transaction (default: 200).')
        parser.add_argument('--max-batches', type=int, default=10,
                            help='Maximum batches processed per invocation (default: 10).')
        parser.add_argument('--apply', action='store_true',
                            help='Actually delete records (default is dry run).')

    def handle(self, *args, **options):
        days = options['days']
        batch_size = options['batch_size']
        max_batches = options['max_batches']
        apply = options['apply']
        if days < 1 or batch_size < 1 or max_batches < 1:
            raise CommandError('--days, --batch-size and --max-batches must be positive')

        cutoff = timezone.now() - timedelta(days=days)
        children = TaskModel.objects.filter(parent_task_id=OuterRef('pk'))
        candidates = (
            TaskModel.objects.filter(finished=True, update_dt__lt=cutoff)
            .annotate(has_children=Exists(children))
            .filter(has_children=False)
        )
        total_tasks = 0
        total_signals = 0

        for batch_number in range(1, max_batches + 1):
            # Reevaluate the queryset every iteration, since deleting leaf tasks
            # can make previously ineligible parents eligible.
            ids = list(candidates.order_by('update_dt', 'pk')
                       .values_list('pk', flat=True)[:batch_size])
            if not ids:
                break

            if not apply:
                count_signals = SignalInfoModel.objects.filter(task_id__in=ids).count()
                self.stdout.write(
                    f'DRY RUN: eligible leaf tasks in first batch={len(ids)}, '
                    f'associated signals={count_signals}; cutoff={cutoff.isoformat()}')
                self.stdout.write('No records deleted. Rerun with --apply.')
                return

            with transaction.atomic():
                # Check eligibility again under lock. Lock only the specific tasks;
                # on MySQL with default REPEATABLE READ, this is not a substitute
                # for coordinating with concurrently running task updates.
                locked = list(
                    TaskModel.objects.select_for_update()
                    .filter(pk__in=ids, finished=True, update_dt__lt=cutoff)
                    .annotate(has_children=Exists(children))
                    .filter(has_children=False)
                    .values_list('pk', flat=True)
                )
                if not locked:
                    continue

                # Break the FK cycle BEFORE deleting signals.  Do not touch other
                # tasks; only selected old finished leaf tasks are affected.
                TaskModel.objects.filter(pk__in=locked).update(state=None)
                signal_count, _ = SignalInfoModel.objects.filter(task_id__in=locked).delete()
                task_count, _ = TaskModel.objects.filter(pk__in=locked).delete()

            total_tasks += task_count
            total_signals += signal_count
            message = (f'Huey monitor pruning batch={batch_number}: '
                       f'tasks={task_count} signals={signal_count}')
            logger.info(message)
            self.stdout.write(message)

        summary = (f'Huey monitor pruning completed: tasks={total_tasks}, '
                   f'signals={total_signals}, cutoff={cutoff.isoformat()}')
        logger.info(summary)
        self.stdout.write(self.style.SUCCESS(summary))

