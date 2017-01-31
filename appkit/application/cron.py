# -*- coding: utf-8 -*-

# Copyright (C) 2015 Luis López <luis@cuarentaydos.com>
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; either version 2
# of the License, or (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA  02110-1301,
# USA.


from appkit import (
    application,
    logging,
    utils
)
from appkit.application import (
    commands,
    services
)

import abc
import sys


class Task(application.Extension):
    INTERVAL = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.human_interval = str(self.INTERVAL)

        try:
            self.INTERVAL = utils.parse_interval(self.INTERVAL)
        except ValueError as e:
            msg = "Invalid interval value '{interval}', check docs"
            msg = msg.format(interval=self.interval)
            raise TypeError(msg) from e

    @abc.abstractmethod
    def execute(self, app):
        msg = "Extension {name} doesn't implements execute method"
        msg = msg.format(name=self.__class__)
        raise NotImplementedError(msg)


class CronManager:
    TASK_EXTENSION_POINT = Task

    def __init__(self, app):
        self.app = app
        self.app.register_extension_point(
            self.__class__.TASK_EXTENSION_POINT)
        self.logger = logging.getLogger('cronmanager')

    @abc.abstractmethod
    def load_checkpoint(self, task):
        """
        CronManagers must implement this method in order to load task's
        checkpoints
        """
        msg = "Extension {name} doesn't implements load_checkpoint method"
        msg = msg.format(name=self.__class__)
        raise NotImplementedError(msg)

    @abc.abstractmethod
    def save_checkpoint(self, task, checkpoint):
        """
        CronManagers must implement this method in order to save task's
        checkpoints
        """
        msg = "Extension {name} doesn't implements save_checkpoint method"
        msg = msg.format(name=self.__class__)
        raise NotImplementedError(msg)

    def call_execute_method(self, task, app):
        """
        Overridable method to customize task execution
        """
        return task.execute(app)

    def get_task(self, name):
        return self.app.get_extension(self.__class__.TASK_EXTENSION_POINT,
                                      name)

    def get_tasks(self):
        for name in self.app.get_extension_names_for(
                        self.__class__.TASK_EXTENSION_POINT):

            try:
                yield name, self.get_task(name)
            except application.ExtensionError as e:
                msg = "Task «{name}» failed: '{msg}'"
                msg = msg.format(name=name, msg=e)
                self.logger.error(msg)

            except StopIteration:
                break

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
        if force or timedelta >= task.INTERVAL:
            ret = self.call_execute_method(task, self.app)

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


class CronService(CronManager, services.Service):
    __extension_name__ = 'cron'


class CronCommand(commands.Command):
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
        self.logger = logging.getLogger('cron')

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
            tasks = [(n, e) for (n, e) in manager.get_tasks() if n in tasks]
            for name, task in tasks:
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


class TaskError(Exception):
    pass


class TaskNotFoundError(Exception):
    pass
