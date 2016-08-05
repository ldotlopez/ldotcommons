from appkit import app


class App(app.App):
    def __init__(self):
        super().__init__('sampleapp')
        self.load_plugin('backgroundupdater')
