from uvicorn.server import Server as BaseServer


class Server(BaseServer):

    def install_signal_handlers(self) -> None:
        pass

    def set_should_exit(self) -> None:
        self.should_exit = True
