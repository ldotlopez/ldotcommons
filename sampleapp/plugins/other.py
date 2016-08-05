import appkit


class Other(appkit.CommandExtension):
    __extension_name__ = 'other'

    help = 'Optional command'

    def run(self, arguments):
        print("Other is running")

__sampleapp_extensions__ = [
    Other
]
