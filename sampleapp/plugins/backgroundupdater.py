import appkit


class BackgroundUpdater(appkit.CommandExtension):
    __extension_name__ = 'background-updater'

    help = 'Change desktop background'
    arguments = (
        appkit.cliargument(
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
