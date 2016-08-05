from appkit import app


class BackgroundUpdater(app.Command):
    __extension_name__ = 'background-updater'

    help = 'Change desktop background'
    arguments = (
        app.argument(
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
