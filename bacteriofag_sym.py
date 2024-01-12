import pygame
import sys
import numpy as np
import random

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)

GRAY = (128, 128, 128)

BACKGROUND = BLACK


class Dot(pygame.sprite.Sprite):
    def __init__(self, x, y, width, height, color=GREEN, radius=10, velocity=[0, 0], randomize=False):
        super().__init__()
        self.image = pygame.Surface([radius * 2, radius * 2])
        self.image.fill((0, 0, 0, 0))
        pygame.draw.circle(self.image, color, (radius, radius), radius)
        self.image.set_colorkey((0, 0, 0, 0))
        self.rect = self.image.get_rect()
        self.pos = np.array([x, y], dtype=np.float64)
        self.vel = np.asarray(velocity, dtype=np.float64)

        self.killswitch_on = False
        self.recovered = False
        self.randomize = randomize

        self.WIDTH = width
        self.HEIGHT = height

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

        vel_norm = np.linalg.norm(self.vel)
        if vel_norm > 3:
            self.vel /= vel_norm

        if self.randomize:
            self.vel += np.random.rand(2) * 2 - 1

        if self.killswitch_on:
            self.cycles_to_fate -= 1

    def respawn(self, color, radius=10, offset=5):
        return Dot(
            self.rect.x,
            self.rect.y,
            self.WIDTH,
            self.HEIGHT,
            color=color,
            radius=radius,
            velocity=self.vel,
        )

    def killswitch(self, cycles_to_fate=20, mortality_rate=0.2):
        self.killswitch_on = True
        self.cycles_to_fate = cycles_to_fate
        self.mortality_rate = mortality_rate

class Simulation:
    def __init__(self, width=1600, height=900):
        self.WIDTH = width
        self.HEIGHT = height
        self.virus_lifecycles_range = (50, 100)
        self.virions_count = (2, 6)

        self.screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption('Gra')

        self.susceptible_container = pygame.sprite.Group()
        self.virus_container = pygame.sprite.Group()
        self.bacteria_infected_container = pygame.sprite.Group()
        self.all_container = pygame.sprite.Group()

        self.n_susceptible = 20
        self.n_infected = 1
        self.n_quarantined = 0
        self.T = 1000
        self.cycle_to_fate = 20
        self.mortality_rate = 1

    def start(self, randomize=False):

        self.N = self.n_susceptible + self.n_infected + self.n_quarantined

        pygame.init()
        screen = pygame.display.set_mode((self.WIDTH, self.HEIGHT))
        pygame.display.set_caption('Gra')

        for i in range(self.n_susceptible):
            x = np.random.randint(0, self.WIDTH + 1)
            y = np.random.randint(0, self.HEIGHT + 1)
            vel = np.random.rand(2) * 2 - 1
            guy = Dot(x, y, self.WIDTH, self.HEIGHT, color=GREEN, velocity=vel, randomize=randomize)
            self.susceptible_container.add(guy)
            self.all_container.add(guy)

        for i in range(self.n_quarantined):
            x = np.random.randint(0, self.WIDTH + 1)
            y = np.random.randint(0, self.HEIGHT + 1)
            vel = [0, 0]
            guy = Dot(x, y, self.WIDTH, self.HEIGHT, color=GREEN, velocity=vel, randomize=False)
            self.susceptible_container.add(guy)
            self.all_container.add(guy)

        for i in range(self.n_infected):
            x = np.random.randint(0, self.WIDTH + 1)
            y = np.random.randint(0, self.HEIGHT + 1)
            vel = np.random.rand(2) * 2 - 1
            guy = Dot(x, y, self.WIDTH, self.HEIGHT, color=RED, velocity=vel, radius=4, randomize=randomize)
            guy.killswitch(random.randint(self.virus_lifecycles_range[0], self.virus_lifecycles_range[1]),
                           self.mortality_rate)
            # dodalem linie nzej
            #guy.killswitch(self.cycle_to_fate, self.mortality_rate)
            self.virus_container.add(guy)
            self.all_container.add(guy)

        clock = pygame.time.Clock()

        while True:
        #for i in range(self.T):
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()

            self.all_container.update()
            screen.fill(BACKGROUND)

            # New infections
            collision_group = pygame.sprite.groupcollide(
                self.virus_container,
                self.susceptible_container,
                False,
                True)

            for virus in collision_group:
                for bacteria in collision_group[virus]:
                    new_bacteria = bacteria.respawn(YELLOW)
                    new_bacteria.vel *= -1
                    new_bacteria.killswitch(self.cycle_to_fate, self.mortality_rate)
                    self.bacteria_infected_container.add(new_bacteria)
                    self.all_container.add(new_bacteria)
                virus.kill()
                self.virus_container.remove(virus)
                self.all_container.remove(virus)

            for guy in self.bacteria_infected_container:
                if guy.killswitch_on and guy.cycles_to_fate == 0:
                    for _ in range(
                            int(np.random.uniform(self.virions_count[0],
                                                  self.virions_count[1]))):  # Spawn red dots  # Spawn red dots
                        new_guy = guy.respawn(RED, radius=4)
                        new_guy.killswitch_on = False
                        new_guy.pos = np.array([np.random.uniform(guy.rect.x - 20, guy.rect.x + 20),
                                                np.random.uniform(guy.rect.y - 20, guy.rect.y + 20)], dtype=np.float64)
                        new_guy.vel = np.array([np.random.uniform(-1, 0.1), np.random.uniform(-1, 0.1)],
                                               dtype=np.float64)
                        new_guy.randomize = True
                        print(random.randint(self.virus_lifecycles_range[0], self.virus_lifecycles_range[1]))
                        new_guy.killswitch(
                            random.randint(self.virus_lifecycles_range[0], self.virus_lifecycles_range[1]),
                            self.mortality_rate)
                        self.virus_container.add(new_guy)
                        self.all_container.add(new_guy)
                    self.bacteria_infected_container.remove(guy)
                    self.all_container.remove(guy)
            # self.all_container.update()

            for guy in self.virus_container:
                if guy.killswitch_on and guy.cycles_to_fate == 0:
                    guy.kill()
                    self.virus_container.remove(guy)

            self.all_container.draw(screen)

            pygame.display.flip()
            clock.tick(30)
        pygame.quit()


if __name__ == '__main__':
    covid = Simulation()
    covid.n_susceptible = 200
    covid.n_quarantined = 0
    covid.n_infected = 3
    covid.T = 1500
    covid.cycle_to_fate = 150
    covid.mortality_rate = 0.8
    covid.virions_count = (1, 6)
    covid.virus_lifecycles_range = (200, 250)
    covid.start(randomize=True)