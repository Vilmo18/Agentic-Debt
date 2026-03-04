'''
Entry point for the two-player Pong game application.
Initializes and runs the game loop via the Game class.
'''
import pygame
from game import Game


def main():
    """
    Create a Game instance and run it. Ensures pygame quits properly.
    """
    game = Game()
    game.run()
    pygame.quit()


if __name__ == "__main__":
    main()