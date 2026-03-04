'''

Main entry point for the Flappy Bird clone application.
Creates the Game instance and starts the main loop.

'''
import sys

from game import Game


def main() -> None:
    """
    Create the Game instance and start the main loop.
    """
    try:
        game = Game()
        game.run()
    except SystemExit:
        # Allow clean exit on window close.
        pass
    except Exception as exc:
        # In a real app, consider logging this to a file.
        print(f"Unexpected error: {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    main()