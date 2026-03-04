'''
Main entry point for the Checkers (Draughts) game application.
Initializes Pygame and starts the GameApp.
'''
import pygame
from app import GameApp


def main():
    pygame.init()
    try:
        app = GameApp()
        app.run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()