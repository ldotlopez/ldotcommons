from appkit import (
    application,
    logging,
    utils
)


import abc
import sys


class CronTask(application.Extension):
    interval = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        try:
            self.interval = utils.parse_interval(self.interval)
        except ValueError as e:
            msg = "Invalid interval value '{interval}', check docs"
            msg = msg.format(interval=self.interval)
            raise TypeError(msg) from e

    @abc.abstractmethod
    def execute(self, app):
        raise NotImplementedError()


class CronManager:
    TASK_EXTENSION_POINT = CronTask

    def __init__(self, app):
        self.app = app
        self.app.register_extension_point(
            self.__class__.TASK_EXTENSION_POINT)
        self.logger = logging.get_logger('cronmanager')

    @abc.abstractmethod
    def load_checkpoint(self, task):
        raise NotImplementedError()

    @abc.abstractmethod
    def save_checkpoint(self, task, checkpoint):
        raise NotImplementedError()

    def get_tasks(self):
        for name in self.app.get_extension_names_for(
                        self.__class__.TASK_EXTENSION_POINT):

            try:
                yield name, self.app.get_extension(
                    self.__class__.TASK_EXTENSION_POINT, name)
            except application.ExtensionError as e:
                msg = "Task «{name}» failed: '{msg}'"
                msg = msg.format(name=name, msg=e)
                self.logger.error(msg)

            except StopIteration:
                break

    def execute_task_extension(self, task, app):
        return task.execute(app)

    def execute(self, task, force=False):
        assert isinstance(task, self.__class__.TASK_EXTENSION_POINT)
        assert isinstance(force, bool)

        checkpoint = {
            'last-execution': 0
        }

        tmp = self.load_checkpoint(task)
        assert isinstance(tmp, dict)
        checkpoint.update({k: v for (k, v)
                           in tmp.items()
                           if v is not None})

        timedelta = utils.now_timestamp() - checkpoint.get('last-execution', 0)
        if force or timedelta >= task.interval:
            ret = self.execute_task_extension(task, self.app)

            checkpoint.update({
                'last-execution': utils.now_timestamp()
            })
            self.save_checkpoint(task, checkpoint)
            return ret

    def execute_all(self, force=False):
        ret = []

        for name, task in self.get_tasks():
            try:
                ret.append((task, self.execute(task, force=force)))
            except application.ExtensionError as e:
                ret.append((task, e))

        return ret


class CronService(CronManager, application.Service):
    __extension_name__ = 'cron'


class CronCommand(application.Command):
    __extension_name__ = 'cron'
    SERVICE_NAME = 'cron'

    help = 'Run cron tasks'

    arguments = (
        application.cliargument(
            '-a', '--all',
            dest='all',
            action='store_true',
            default=[],
            help=('Run all tasks')
        ),
        application.cliargument(
            '-t', '--task',
            dest='tasks',
            action='append',
            default=[],
            help=('Run specifics task')
        ),
        application.cliargument(
            '-f', '--force',
            dest='force',
            action='store_true',
            help=('Force tasks to run omiting intervals')
        ),
        application.cliargument(
            '-l', '--list',
            dest='list',
            action='store_true',
            help=('Show registered tasks')
        ),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.logger = logging.get_logger('cron')

    def execute(self, app, arguments):
        list_ = arguments.list
        all_ = arguments.all
        tasks = arguments.tasks
        force = arguments.force

        test = sum([1 for x in [list_, all_, tasks] if x])

        if test == 0:
            msg = ("One of '--list', '--all' or '--task' options must be "
                   "specified")
            raise application.ArgumentsError(msg)

        if test > 1:
            msg = ("Only one of '--list', '--all' and '--task' options can be "
                   "specified. They are mutually exclusive.")
            raise application.ArgumentsError(msg)

        manager = app.get_service(self.__class__.SERVICE_NAME)

        if list_:
            tasks = list(manager.get_tasks())
            if not tasks:
                msg = "No available tasks"
                print(msg, file=sys.stderr)

            for name, task in sorted(tasks, key=lambda x: x[0]):
                msg = "{name} – interval: {interval} ({secs} seconds)"
                msg = msg.format(
                    name=name,
                    interval=task.interval,
                    secs=utils.parse_interval(task.interval))

                print(msg)

        elif all_:
            results = manager.execute_all(force=force)
            if not results:
                msg = "No available tasks"
                print(msg, file=sys.stderr)

            for (task, result) in results:
                self._handle_task_result(task, result)

        elif tasks:
            for name, task in manager.get_tasks():
                try:
                    manager.execute(task, force)
                except application.ExtensionError as e:
                    self._handle_task_result(task, e)

        else:
            # This code should never be reached but keeping it here we will
            # prevent future mistakes
            msg = "Incorrect usage"
            raise application.ExcetionError(msg)

    def _handle_task_result(self, task, result=None):
        if result is None:
            msg = "Task «{name}» OK"
            msg = msg.format(name=task.__extension_name__)
            self.logger.info(msg)

        elif isinstance(result, application.ExtensionError):
            msg = "Task «{name}» failed: '{msg}'"
            msg = msg.format(name=task.__extension_name__,
                             msg=result)
            self.logger.error(msg)

        else:
            raise TypeError(result)


class CronTaskError(Exception):
    pass


class CronTaskNotFoundError(Exception):
    pass
