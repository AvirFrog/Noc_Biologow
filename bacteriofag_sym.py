import sys
import os
import numpy as np
import random

os.environ["PYGAME_HIDE_SUPPORT_PROMPT"] = "1"    # Do not print pygame welcome message into console (has to be set before importing pygame)
import pygame

# Color definitions in RGB
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
GRAY = (128, 128, 128)

BACKGROUND = BLACK


class Dot(pygame.sprite.Sprite):
    def __init__(self, x, y, parent_surface, width, height, containers, rng = None):
        super().__init__()

        if not rng:
            self.rng = np.random.default_rng()
        else:
            self.rng = rng

        self.image = pygame.Surface((width, height))
        self.image = self.image.convert_alpha()

        self.pos = np.array([x, y], dtype=np.float64)
        self.rect = self.image.get_rect(center=self.pos)
        self.vel = np.asarray([0, 0], dtype=np.float64)

        self.parent_surface = parent_surface

        containers = list(containers)
        self.containers = containers
        self.add(*containers)

    def move_containers(self, containers, replace=True):
        containers = list(containers)

        if replace:
            self.containers = containers
        else:
            self.containers.extend(containers)

        self.kill()    # This merely removes sprite from all groups so it can then be re-added, don't worry
        self.add(*self.containers)

    def update(self):
        self.pos += self.vel
        x, y = self.pos

        # Periodic boundary conditions
        if x < 0:
            self.pos[0] = self.WIDTH
            x = self.WIDTH
        if x > self.WIDTH:
            self.pos[0] = 0
            x = 0
        if y < 0:
            self.pos[1] = self.HEIGHT
            y = self.HEIGHT
        if y > self.HEIGHT:
            self.pos[1] = 0
            y = 0

        self.rect.x = x
        self.rect.y = y

        # Brownian
        #old_vel = self.vel.copy()

        change = self.rng.uniform(-1, 1, 2)
        change = (change[0]/np.sqrt(change[0]**2 + change[1]**2), change[1]/np.sqrt(change[0]**2 + change[1]**2))
        self.vel = change

        #vel_norm = np.linalg.norm(self.vel)
        #if vel_norm > 5:
        #    self.vel = old_vel

class Bacteria(Dot):
    def __init__(self, x, y, surface, containers, rng=None):
        super().__init__(x, y, surface, 20, 20, containers, rng)

        self.__draw()

        self.deathclock = None

    def __draw(self, color=GREEN):
        self.image.fill((0,0,0,0))
        pygame.draw.circle(self.image, color, (10, 10), 10, 10)

    def infect(self, deathclock=30):
        self.deathclock = deathclock
        self.__draw(color=YELLOW)

    def update(self):
        self.pos += self.vel
        x, y = self.pos
        s_x, s_y = self.parent_surface.get_size()

        # Periodic boundary conditions
        if x < 0:
            x += s_x
        if x > s_x:
            x -= s_x
        if y < 0:
            y += s_y
        if y > s_y:
            y -= s_y

        self.pos = np.asarray([x, y], dtype=np.float64)
        self.rect = self.image.get_rect(center=(x, y))

        # Brownian
        old_vel = self.vel.copy()

        change = self.rng.uniform(-1, 1, 2)
        change = (change[0]/np.sqrt(change[0]**2 + change[1]**2), change[1]/np.sqrt(change[0]**2 + change[1]**2))
        self.vel += change

        vel_norm = np.linalg.norm(self.vel)
        if vel_norm > 3:
            self.vel = old_vel

        if self.deathclock != None:

            if self.deathclock == 0:
                self.kill()
                return 1

            self.deathclock -= 1

class Virion(Dot):
    def __init__(self, x, y, surface, containers, rng=None):
        super().__init__(x, y, surface, 10, 10, containers, rng)

        self.__draw()

        self.deathclock = self.rng.integers(50, 100, endpoint=True)

    def __draw(self, color=RED):
        self.image.fill((0,0,0,0))
        pygame.draw.circle(self.image, color, (5, 5), 5, 5)

    def update(self):
        self.pos += self.vel
        x, y = self.pos
        s_x, s_y = self.parent_surface.get_size()

        # Periodic boundary conditions
        if x < 0:
            x += s_x
        if x > s_x:
            x -= s_x
        if y < 0:
            y += s_y
        if y > s_y:
            y -= s_y

        self.pos = np.asarray([x, y], dtype=np.float64)
        self.rect = self.image.get_rect(center=(x, y))

        # Brownian
        old_vel = self.vel.copy()

        change = self.rng.uniform(-1, 1, 2)
        change = (change[0]/np.sqrt(change[0]**2 + change[1]**2), change[1]/np.sqrt(change[0]**2 + change[1]**2))
        self.vel += change

        vel_norm = np.linalg.norm(self.vel)
        if vel_norm > 6:
            self.vel = old_vel

        if self.deathclock != None:
            if self.deathclock == 0:
                self.kill()
                return 0

            self.deathclock -= 1


class Simulation:
    def __init__(self, width=1600, height=900):

        self.rng = np.random.default_rng()

        self.WIDTH = width	# window width
        self.HEIGHT = height	# window height

        #self.virus_lifecycles_range = (50, 100)
        #self.virions_count = (2, 6)

        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption('Symulacja infekcji wirusowej w kolonii bakteryjnej')

        self.susceptible_container = pygame.sprite.Group()
        self.virus_container = pygame.sprite.Group()
        self.bacteria_infected_container = pygame.sprite.Group()
        self.all_container = pygame.sprite.Group()

        self.n_susceptible = 20
        self.n_infected = 1
        #self.n_quarantined = 0
        #self.cycle_to_fate = 20
        #self.mortality_rate = 1

    def start(self):

        self.N = self.n_susceptible + self.n_infected #+ self.n_quarantined

        pygame.init()
        screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption('Symulacja rozwoju wirusa w koloniii bakteryjnej')

        for _ in range(self.n_susceptible):    # Spawn bacteria
            x = self.rng.integers(0, self.WIDTH, endpoint=True)
            y = self.rng.integers(0, self.HEIGHT, endpoint=True)

            Bacteria(x, y, screen, containers=[self.susceptible_container,
                                               self.all_container], rng=self.rng)

        '''
        for i in range(self.n_quarantined):
            x = np.random.randint(0, self.WIDTH + 1)
            y = np.random.randint(0, self.HEIGHT + 1)
            vel = [0, 0]
            guy = Dot(x, y, self.WIDTH, self.HEIGHT, color=GREEN, velocity=vel)
            self.susceptible_container.add(guy)
            self.all_container.add(guy)
        '''

        for _ in range(self.n_infected):    # Spawn virions
            x = self.rng.integers(0, self.WIDTH, endpoint=True)
            y = self.rng.integers(0, self.HEIGHT, endpoint=True)
            Virion(x, y, screen, containers=[self.virus_container,
                                             self.all_container], rng=self.rng)

        clock = pygame.time.Clock()

        # Main loop
        while True:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:    # If "X" button was clicked, end the program
                    sys.exit()


            for sprite in self.all_container:    # Call .update() method on all sprites
                action = sprite.update()
                if action and sprite.__class__ == Bacteria:
                    for _ in range(self.rng.integers(2,6)):  # Spawn virions
                        Virion(self.rng.integers(sprite.rect.left,
                                                 sprite.rect.right,
                                                 endpoint=True),
                               self.rng.integers(sprite.rect.top,
                                                 sprite.rect.bottom,
                                                 endpoint=True),
                               screen,
                               [self.virus_container, self.all_container])

            screen.fill(BACKGROUND)        # Fill screen with background color (erases all objects)


            ## New infections

            # Find all viruses & non-immune bacteria which collided
            collision_group = pygame.sprite.groupcollide(
                self.virus_container,
                self.susceptible_container,
                False,
                True)    # removes bacteria that collided from suspectible_container

            for virus in collision_group:    # Loop over viruses that collided with anything
                bacteria = collision_group[virus][0]    # Select first bacteria that collided and infect it

                bacteria.infect()
                bacteria.move_containers([self.bacteria_infected_container,
                                          self.all_container])

                virus.kill()

            self.all_container.draw(screen)

            pygame.display.flip()
            clock.tick(30)
        pygame.quit()


if __name__ == '__main__':
    bacteriophage = Simulation()
    bacteriophage.n_susceptible = 200
    #bacteriophage.n_quarantined = 0
    bacteriophage.n_infected = 3
    #bacteriophage.cycle_to_fate = 150
    #bacteriophage.mortality_rate = 0.8
    #bacteriophage.virions_count = (1, 6)
    #bacteriophage.virus_lifecycles_range = (200, 250)
    bacteriophage.start()
