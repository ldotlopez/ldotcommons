import appkit


class App(appkit.CLIApp):
    def __init__(self):
        super().__init__('sampleapp')
        self.load_plugin('backgroundupdater')
        self.load_plugin('other')
