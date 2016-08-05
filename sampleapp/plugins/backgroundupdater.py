import appkit
from appkit import cliapp


class BackgroundUpdater(appkit.CommandExtension):
    __extension_name__ = 'background-updater'

    help = 'Change desktop background'
    arguments = (
        cliapp.argument(
            '-d', '--directory',
            help='Choose random background from directory',
            required=True
        ),
    )

    def run(self, arguments):
        print("Got directory: {}".format(arguments.directory))
        return 0

__sampleapp_extensions__ = [
    BackgroundUpdater
]
