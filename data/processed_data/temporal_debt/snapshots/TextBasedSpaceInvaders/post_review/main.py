'''
Main entry point for the Simple Space Invaders game using Pygame.
Initializes the Game controller and starts the main loop.
'''
import pygame
from game import Game


def main():
    pygame.init()
    try:
        game = Game()
        game.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()