from appkit import app


class Other(app.Command):
    __extension_name__ = 'other'

    help = 'Optional command'

    def run(self, arguments):
        print("Other is running")

__sampleapp_extensions__ = [
    Other
]
