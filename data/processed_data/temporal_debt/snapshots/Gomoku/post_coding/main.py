'''
Main entry point for the Gomoku application. It initializes the controller and view,
and starts the tkinter main loop.
'''

import sys
from gomoku.controller import GameController
from gomoku.view import GomokuApp


def main():
    controller = GameController()
    app = GomokuApp(controller)
    controller.attach_view(app)
    app.mainloop()


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        sys.exit(0)
