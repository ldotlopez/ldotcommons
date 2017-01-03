from appkit import (
    application,
    utils
)


import abc


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

    @abc.abstractmethod
    def load_checkpoint(self, task):
        raise NotImplementedError()

    @abc.abstractmethod
    def save_checkpoint(self, task, checkpoint):
        raise NotImplementedError()

    def get_tasks(self):
        yield from self.app.get_extensions_for(
            self.__class__.TASK_EXTENSION_POINT)

    def execute_task(self, task, app):
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
            try:
                ret = self.execute_task(task, self.app)
            except CronTaskError as e:
                self.logger.error(e)
                raise

            checkpoint.update({
                'last-execution': utils.now_timestamp()
            })
            self.save_checkpoint(task, checkpoint)
            return ret

    def execute_by_name(self, name, force=False):
        assert isinstance(name, str) and name
        assert isinstance(force, bool)

        tasks = {name: task for (name, task) in self.get_tasks()}
        if name not in tasks:
            raise CronTaskNotFoundError(name)

        return self.execute(tasks[name], force=force)

    def execute_all(self, force=False):
        for task in self.get_tasks():
            self.execute(task, force=force)


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

    def execute(self, app, arguments):
        list_ = arguments.list
        all_ = arguments.all
        tasks = arguments.tasks
        force = arguments.force

        test = sum([1 for x in [list_, all_, tasks] if x])

        if test == 0:
            msg = ("One of '--list', '--all' or '--task' options must be "
                   "specified")
            raise application.CommandArgumentError(msg)

        if test > 1:
            msg = ("Only one of '--list', '--all' and '--task' options can be "
                   "specified. They are mutually exclusive.")
            raise application.CommandArgumentError(msg)

        manager = app.get_service(self.__class__.SERVICE_NAME)

        if list_:
            tasks = manager.get_tasks()
            for name, task in sorted(tasks, key=lambda x: x[0]):
                msg = "{name} – interval: {interval} ({secs} seconds)"
                msg = msg.format(
                    name=name,
                    interval=task.interval,
                    secs=utils.parse_interval(task.interval))

                print(msg)

        elif all_:
            manager.execute_all(force=force)

        elif tasks:
            for name in tasks:
                manager.execute_by_name(name, force)

        else:
            # This code should never be reached but keeping it here we will
            # prevent future mistakes
            msg = "Incorrect usage"
            raise application.cliexc.PluginArgumentError(msg)


class CronTaskError(Exception):
    pass


class CronTaskNotFoundError(Exception):
    pass
